use std::{
    fs,
    path::PathBuf,
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use serde::Serialize;
use tauri::{AppHandle, Manager};

mod process;

use process::{BackendChild, start_backend, stop_backend_process};

const STARTUP_TIMEOUT: Duration = Duration::from_secs(15);

#[derive(Clone, Serialize)]
pub struct BackendConnection {
    pub base_url: String,
    pub token: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BackendPhase {
    Starting,
    Ready,
    Failed,
    Stopping,
}

#[derive(Clone, Serialize)]
pub struct BackendStatus {
    pub state: BackendPhase,
    pub error_code: Option<String>,
}

#[derive(Debug, PartialEq, Eq, Serialize)]
pub struct BackendCommandError {
    pub code: String,
}

struct BackendRuntime {
    phase: BackendPhase,
    error_code: Option<String>,
    connection: Option<BackendConnection>,
    child: Option<BackendChild>,
}

pub struct BackendState(Mutex<BackendRuntime>);

impl BackendState {
    pub const fn new() -> Self {
        Self(Mutex::new(BackendRuntime {
            phase: BackendPhase::Starting,
            error_code: None,
            connection: None,
            child: None,
        }))
    }

    fn status(&self) -> Result<BackendStatus, BackendCommandError> {
        self.0
            .lock()
            .map(|runtime| BackendStatus {
                state: runtime.phase,
                error_code: runtime.error_code.clone(),
            })
            .map_err(|_| command_error("backend_state_unavailable"))
    }

    fn connection(&self) -> Result<Option<BackendConnection>, BackendCommandError> {
        let runtime = self
            .0
            .lock()
            .map_err(|_| command_error("backend_state_unavailable"))?;
        match runtime.phase {
            BackendPhase::Ready => Ok(runtime.connection.clone()),
            BackendPhase::Failed => Err(command_error(
                runtime
                    .error_code
                    .as_deref()
                    .unwrap_or("backend_start_failed"),
            )),
            BackendPhase::Stopping => Err(command_error("backend_stopping")),
            BackendPhase::Starting => Ok(None),
        }
    }

    fn begin_retry(&self) -> Result<bool, BackendCommandError> {
        let mut runtime = self
            .0
            .lock()
            .map_err(|_| command_error("backend_state_unavailable"))?;
        if !matches!(runtime.phase, BackendPhase::Failed) {
            return Ok(false);
        }
        runtime.phase = BackendPhase::Starting;
        runtime.error_code = None;
        drop(runtime);
        Ok(true)
    }

    fn complete_start(&self, result: Result<(BackendConnection, BackendChild), &'static str>) {
        let Ok(mut runtime) = self.0.lock() else {
            if let Ok((_connection, child)) = result {
                child.kill();
            }
            return;
        };
        if !matches!(runtime.phase, BackendPhase::Starting) {
            if let Ok((_connection, child)) = result {
                child.kill();
            }
            return;
        }
        match result {
            Ok((connection, child)) => {
                runtime.phase = BackendPhase::Ready;
                runtime.connection = Some(connection);
                runtime.child = Some(child);
            }
            Err(code) => {
                runtime.phase = BackendPhase::Failed;
                runtime.error_code = Some(code.to_owned());
            }
        }
    }

    fn take_for_stop(&self) -> Option<(BackendConnection, BackendChild)> {
        let Ok(mut runtime) = self.0.lock() else {
            return None;
        };
        runtime.phase = BackendPhase::Stopping;
        runtime.connection.take().zip(runtime.child.take())
    }
}

fn command_error(code: &str) -> BackendCommandError {
    BackendCommandError {
        code: code.to_owned(),
    }
}

pub fn spawn_start(app: AppHandle) {
    thread::spawn(move || {
        let result = start_backend(&app);
        update_startup_diagnostic(result.as_ref().err().copied());
        app.state::<BackendState>().complete_start(result);
    });
}

fn update_startup_diagnostic(error_code: Option<&str>) {
    let Some(base) = diagnostic_directory() else {
        return;
    };
    let path = base.join("desktop-startup-error.log");
    if let Some(code) = error_code {
        if fs::create_dir_all(base).is_ok() {
            let _result = fs::write(
                path,
                format!("Bilidown desktop backend startup failed: {code}\n"),
            );
        }
    } else {
        let _result = fs::remove_file(path);
    }
}

fn diagnostic_directory() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .map(|path| path.join("Bilidown"))
    }
    #[cfg(target_os = "macos")]
    {
        std::env::var_os("HOME")
            .map(PathBuf::from)
            .map(|path| path.join("Library").join("Logs").join("Bilidown"))
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        std::env::var_os("HOME")
            .map(PathBuf::from)
            .map(|path| path.join(".local").join("state").join("Bilidown"))
    }
}

#[tauri::command]
pub fn backend_status(
    state: tauri::State<'_, BackendState>,
) -> Result<BackendStatus, BackendCommandError> {
    state.status()
}

#[tauri::command]
pub async fn backend_connection(
    state: tauri::State<'_, BackendState>,
) -> Result<BackendConnection, BackendCommandError> {
    let deadline = Instant::now() + STARTUP_TIMEOUT + Duration::from_secs(2);
    while Instant::now() < deadline {
        if let Some(connection) = state.connection()? {
            return Ok(connection);
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    Err(command_error("backend_start_timeout"))
}

#[tauri::command]
pub fn retry_backend(
    app: AppHandle,
    state: tauri::State<'_, BackendState>,
) -> Result<BackendStatus, BackendCommandError> {
    if state.begin_retry()? {
        spawn_start(app);
    }
    state.status()
}

pub fn stop_backend(app: &AppHandle) {
    let Some(state) = app.try_state::<BackendState>() else {
        return;
    };
    if let Some((connection, child)) = state.take_for_stop() {
        stop_backend_process(&connection, child);
    }
}

#[cfg(test)]
mod tests {
    use super::{BackendPhase, BackendState};

    #[test]
    fn failed_start_can_be_retried() {
        let state = BackendState::new();

        assert!(matches!(
            state.status(),
            Ok(status) if status.state == BackendPhase::Starting
        ));
        state.complete_start(Err("backend_start_timeout"));
        assert!(matches!(
            state.status(),
            Ok(status)
                if status.state == BackendPhase::Failed
                    && status.error_code.as_deref() == Some("backend_start_timeout")
        ));
        assert!(state.connection().is_err());

        assert_eq!(state.begin_retry(), Ok(true));
        assert!(matches!(
            state.status(),
            Ok(status)
                if status.state == BackendPhase::Starting && status.error_code.is_none()
        ));
        assert_eq!(state.begin_retry(), Ok(false));
    }
}
