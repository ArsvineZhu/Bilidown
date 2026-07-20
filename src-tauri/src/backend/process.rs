use std::{
    io::Write,
    net::{TcpListener, TcpStream},
    path::PathBuf,
    process::{Child as ProcessChild, Command},
    thread,
    time::{Duration, Instant},
};

use tauri::AppHandle;
use tauri_plugin_shell::{
    ShellExt,
    process::{CommandChild, CommandEvent},
};
use uuid::Uuid;

use super::BackendConnection;

const LOOPBACK: &str = "127.0.0.1";
const STARTUP_TIMEOUT: Duration = Duration::from_secs(15);
const DESKTOP_ORIGINS: &str =
    "http://tauri.localhost,https://tauri.localhost,tauri://localhost,http://127.0.0.1:5173";

pub(super) enum BackendChild {
    Development(ProcessChild),
    Bundled(CommandChild),
}

impl BackendChild {
    pub(super) fn kill(self) {
        match self {
            Self::Development(mut process) => {
                let _result = process.kill();
            }
            Self::Bundled(process) => {
                let _result = process.kill();
            }
        }
    }
}

struct SpawnedBackend {
    child: BackendChild,
    events: Option<tauri::async_runtime::Receiver<CommandEvent>>,
}

pub(super) fn start_backend(
    app: &AppHandle,
) -> Result<(BackendConnection, BackendChild), &'static str> {
    let port = available_port().map_err(|_| "backend_port_unavailable")?;
    let connection = BackendConnection {
        base_url: format!("http://{LOOPBACK}:{port}"),
        token: Uuid::new_v4().simple().to_string(),
    };
    let mut spawned = spawn_backend(app, &connection, port)?;
    if let Err(code) = wait_until_ready(port, &mut spawned) {
        spawned.child.kill();
        return Err(code);
    }
    Ok((connection, spawned.child))
}

pub(super) fn stop_backend_process(connection: &BackendConnection, child: BackendChild) {
    request_graceful_shutdown(connection);
    thread::sleep(Duration::from_millis(350));
    child.kill();
}

fn available_port() -> Result<u16, String> {
    let listener = TcpListener::bind((LOOPBACK, 0))
        .map_err(|error| format!("failed to reserve backend port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("failed to inspect backend port: {error}"))
}

fn backend_environment(connection: &BackendConnection, port: u16) -> Vec<(&'static str, String)> {
    vec![
        ("BILIDOWN_PORT", port.to_string()),
        ("BILIDOWN_SESSION_TOKEN", connection.token.clone()),
        ("BILIDOWN_NO_BROWSER", "1".to_owned()),
        ("BILIDOWN_ADDITIONAL_ORIGINS", DESKTOP_ORIGINS.to_owned()),
    ]
}

fn spawn_backend(
    app: &AppHandle,
    connection: &BackendConnection,
    port: u16,
) -> Result<SpawnedBackend, &'static str> {
    if cfg!(debug_assertions) {
        return spawn_development_backend(connection, port);
    }

    let mut command = app
        .shell()
        .sidecar("bilidown-backend")
        .map_err(|_| "backend_sidecar_missing")?;
    for (key, value) in backend_environment(connection, port) {
        command = command.env(key, value);
    }
    let (events, child) = command
        .spawn()
        .map_err(|_| "backend_sidecar_start_failed")?;
    Ok(SpawnedBackend {
        child: BackendChild::Bundled(child),
        events: Some(events),
    })
}

fn spawn_development_backend(
    connection: &BackendConnection,
    port: u16,
) -> Result<SpawnedBackend, &'static str> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .ok_or("backend_repository_missing")?
        .to_path_buf();
    let python = if cfg!(windows) {
        root.join(".venv").join("Scripts").join("python.exe")
    } else {
        root.join(".venv").join("bin").join("python")
    };
    let mut command = Command::new(python);
    command
        .current_dir(root)
        .args(["-c", "from bilidown.launcher import main; main()"]);
    for (key, value) in backend_environment(connection, port) {
        command.env(key, value);
    }
    command
        .spawn()
        .map(|child| SpawnedBackend {
            child: BackendChild::Development(child),
            events: None,
        })
        .map_err(|_| "backend_development_start_failed")
}

fn wait_until_ready(port: u16, spawned: &mut SpawnedBackend) -> Result<(), &'static str> {
    let deadline = Instant::now() + STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if TcpStream::connect((LOOPBACK, port)).is_ok() {
            return Ok(());
        }
        if backend_exited(spawned)? {
            return Err("backend_exited_early");
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err("backend_start_timeout")
}

fn backend_exited(spawned: &mut SpawnedBackend) -> Result<bool, &'static str> {
    match &mut spawned.child {
        BackendChild::Development(process) => process
            .try_wait()
            .map(|status| status.is_some())
            .map_err(|_| "backend_process_unavailable"),
        BackendChild::Bundled(_) => {
            let Some(events) = spawned.events.as_mut() else {
                return Ok(false);
            };
            loop {
                match events.try_recv() {
                    Ok(CommandEvent::Terminated(_))
                    | Err(tokio::sync::mpsc::error::TryRecvError::Disconnected) => {
                        return Ok(true);
                    }
                    Ok(CommandEvent::Error(_)) => return Err("backend_process_unavailable"),
                    Ok(_) => {}
                    Err(tokio::sync::mpsc::error::TryRecvError::Empty) => return Ok(false),
                }
            }
        }
    }
}

fn request_graceful_shutdown(connection: &BackendConnection) {
    let Ok(mut stream) = TcpStream::connect(connection.base_url.trim_start_matches("http://"))
    else {
        return;
    };
    let request = format!(
        "POST /api/quit HTTP/1.1\r\nHost: {}\r\nOrigin: http://tauri.localhost\r\nX-Bilidown-Token: {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
        connection.base_url.trim_start_matches("http://"),
        connection.token,
    );
    let _result = stream.write_all(request.as_bytes());
}
