use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{
    App, AppHandle, Manager,
    menu::{CheckMenuItem, Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
};

use crate::{backend, idle};

pub struct ExitState(pub AtomicBool);
pub struct TrayState(pub AtomicBool);

pub fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _result = window.show();
        let _result = window.unminimize();
        let _result = window.set_focus();
    }
}

pub fn request_exit(app: &AppHandle) {
    app.state::<ExitState>().0.store(true, Ordering::SeqCst);
    backend::stop_backend(app);
    app.exit(0);
}

#[tauri::command]
pub fn quit_app(app: AppHandle) {
    request_exit(&app);
}

#[allow(clippy::too_many_lines)]
pub fn setup_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let open = MenuItem::with_id(app, "open", "打开 Bilidown / Open", true, None::<&str>)?;
    let downloads = MenuItem::with_id(
        app,
        "downloads",
        "打开下载目录 / Downloads",
        true,
        None::<&str>,
    )?;
    let separator = PredefinedMenuItem::separator(app)?;
    let timeout_15 = CheckMenuItem::with_id(
        app,
        "idle-15",
        "闲置 15 分钟退出 / 15 min",
        true,
        false,
        None::<&str>,
    )?;
    let timeout_30 = CheckMenuItem::with_id(
        app,
        "idle-30",
        "闲置 30 分钟退出 / 30 min",
        true,
        true,
        None::<&str>,
    )?;
    let timeout_60 = CheckMenuItem::with_id(
        app,
        "idle-60",
        "闲置 60 分钟退出 / 60 min",
        true,
        false,
        None::<&str>,
    )?;
    let timeout_off = CheckMenuItem::with_id(
        app,
        "idle-off",
        "关闭自动退出 / Off",
        true,
        false,
        None::<&str>,
    )?;
    let second_separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "彻底退出 / Quit", true, None::<&str>)?;
    let menu = Menu::with_items(
        app,
        &[
            &open,
            &downloads,
            &separator,
            &timeout_15,
            &timeout_30,
            &timeout_60,
            &timeout_off,
            &second_separator,
            &quit,
        ],
    )?;

    let initial = app.state::<idle::IdleState>();
    let settings = idle::idle_settings(initial)?;
    timeout_15.set_checked(settings.timeout_minutes == Some(15))?;
    timeout_30.set_checked(settings.timeout_minutes == Some(30))?;
    timeout_60.set_checked(settings.timeout_minutes == Some(60))?;
    timeout_off.set_checked(settings.timeout_minutes.is_none())?;

    let app_handle = app.handle().clone();
    TrayIconBuilder::new()
        .icon(
            app.default_window_icon()
                .ok_or("default window icon is missing")?
                .clone(),
        )
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(move |_tray, event| {
            let id = event.id().as_ref();
            match id {
                "open" => show_main_window(&app_handle),
                "downloads" => open_downloads(&app_handle),
                "quit" => request_exit(&app_handle),
                "idle-15" | "idle-30" | "idle-60" | "idle-off" => {
                    let timeout = match id {
                        "idle-15" => Some(15),
                        "idle-30" => Some(30),
                        "idle-60" => Some(60),
                        _ => None,
                    };
                    let state = app_handle.state::<idle::IdleState>();
                    let _result = idle::set_idle_timeout(app_handle.clone(), state, timeout);
                    let _result = timeout_15.set_checked(timeout == Some(15));
                    let _result = timeout_30.set_checked(timeout == Some(30));
                    let _result = timeout_60.set_checked(timeout == Some(60));
                    let _result = timeout_off.set_checked(timeout.is_none());
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                show_main_window(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
}

fn open_downloads(app: &AppHandle) {
    let Ok(path) = app.path().download_dir().map(|path| path.join("Bilidown")) else {
        return;
    };
    let _result = std::fs::create_dir_all(&path);
    #[cfg(target_os = "windows")]
    let _result = std::process::Command::new("explorer").arg(&path).spawn();
    #[cfg(target_os = "macos")]
    let _result = std::process::Command::new("open").arg(&path).spawn();
    #[cfg(target_os = "linux")]
    let _result = std::process::Command::new("xdg-open").arg(&path).spawn();
}
