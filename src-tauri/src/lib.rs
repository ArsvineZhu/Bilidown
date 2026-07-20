// Tauri injects command arguments as owned framework values.
#![allow(clippy::needless_pass_by_value)]

mod backend;
mod desktop;
mod idle;

use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{Manager, RunEvent, WindowEvent};

pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            desktop::show_main_window(app);
        }))
        .plugin(tauri_plugin_shell::init())
        .manage(desktop::ExitState(AtomicBool::new(false)))
        .manage(desktop::TrayState(AtomicBool::new(false)))
        .manage(backend::BackendState::new())
        .setup(|app| {
            app.manage(idle::IdleState::load(app));
            match desktop::setup_tray(app) {
                Ok(()) => app
                    .state::<desktop::TrayState>()
                    .0
                    .store(true, Ordering::SeqCst),
                Err(error) => eprintln!("Bilidown tray setup failed: {error}"),
            }
            idle::spawn_monitor(app.handle().clone());
            desktop::show_main_window(app.handle());
            backend::spawn_start(app.handle().clone());
            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() == "main"
                && let WindowEvent::CloseRequested { api, .. } = event
                && window
                    .app_handle()
                    .state::<desktop::TrayState>()
                    .0
                    .load(Ordering::SeqCst)
                && !window
                    .app_handle()
                    .state::<desktop::ExitState>()
                    .0
                    .load(Ordering::SeqCst)
            {
                api.prevent_close();
                let _result = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            backend::backend_connection,
            backend::backend_status,
            backend::retry_backend,
            desktop::quit_app,
            idle::idle_settings,
            idle::mark_activity,
            idle::set_active_jobs,
            idle::set_idle_timeout,
        ])
        .build(tauri::generate_context!());
    let app = match builder {
        Ok(app) => app,
        Err(error) => {
            eprintln!("Bilidown desktop runtime failed: {error}");
            return;
        }
    };

    app.run(|app_handle, event| {
        if matches!(&event, RunEvent::Exit) {
            backend::stop_backend(app_handle);
        }
        #[cfg(target_os = "macos")]
        {
            if let RunEvent::Reopen { .. } = event {
                desktop::show_main_window(app_handle);
            }
        }
    });
}
