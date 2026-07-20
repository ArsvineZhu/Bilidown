# Bilidown 1.0.0 Portable Build and Application Metadata

## Context

The native desktop build currently produces Windows MSI and NSIS installers, but
does not provide a portable distribution for users who cannot or do not want to
install the application. The earlier PyInstaller-only archive is not suitable as
a replacement because it predates the Tauri desktop shell and would omit the
tray, WebView login, and native lifecycle behavior.

The project also needs consistent release metadata. The approved 1.0.0 release
metadata is:

- Product name: `Bilidown`
- Version: `1.0.0`
- Author and publisher: `Arsvine Zhu`
- Copyright: `Copyright © 2026 Arsvine Zhu`

## Design

### Metadata

Set the approved version and author in the Python package, frontend package,
Rust package, Tauri configuration, and generated OpenAPI information. Add Tauri
bundle publisher and copyright metadata so the Windows installer exposes the
same identity. Keep the existing application identifier unchanged.

Extend the existing metadata tests so all runtime and packaging version values
must agree. Add focused assertions for the author and Tauri publisher fields.
This deliberately favors explicit fields plus verification over a new metadata
generation layer, avoiding format-specific rewriting of TOML, JSON, and Python
source during every build.

### Windows portable archive

Add `packaging/build-portable.ps1`. It will use the same frontend and PyInstaller
sidecar pipeline as the native build, then build the Tauri executable without
creating an installer. The script will assemble a fresh staging directory named
`Bilidown-1.0.0-windows-x64` and create:

`dist/Bilidown-1.0.0-windows-x64-portable.zip`.

The archive will contain the desktop executable, the target-specific backend
sidecar in the exact layout required by Tauri's shell plugin, bundled FFmpeg
runtime resources, and a concise portable-use README. It will also include
third-party and FFmpeg notices plus a SHA-256 checksum manifest. The portable
edition does not install services, write registry entries, or configure startup.

The script will remove only its known staging directory, create the archive,
validate the expected archive entries, and perform a non-interactive executable
smoke check where practical. It will retain the final archive in `dist/`.

Windows 10/11 users normally already have Microsoft Edge WebView2 Runtime. The
portable guide will state this prerequisite and direct users to install it if
the application cannot start.

### Release and documentation

Update the Windows build/release workflow to upload the portable ZIP alongside
MSI and NSIS artifacts. Update Chinese and English installation, build, release,
and troubleshooting documentation with the portable workflow, its limitations,
and verification instructions.

## Alternatives Considered

1. **Recommended: Tauri portable ZIP.** Preserves the current desktop feature
   set and gives users a conventional unzip-and-run artifact.
2. **Legacy PyInstaller-only ZIP.** Rejected because it would drop the Tauri
   shell, tray behavior, and in-app cookie-login facility.
3. **Self-extracting NSIS portable executable.** Rejected because it adds
   installer-specific behavior and is less transparent than a normal portable
   folder.

## Verification

- Python metadata and configuration tests verify version, author, publisher,
  and generated OpenAPI consistency.
- A focused portable-build test verifies archive naming and required runtime and
  documentation entries without requiring a full Windows release build.
- On Windows, run `packaging\\build-portable.ps1`, inspect the ZIP, extract it
  outside the repository, start the application, and confirm the tray and
  backend health behavior work.
- Run the existing Python suite, frontend typecheck/tests/build, Rust formatting
  and clippy checks, and the desktop packaging checks.

## Scope

This work adds Windows x64 portable distribution and 1.0.0 metadata only. It
does not add portable builds for macOS/Linux, change the application identifier,
or create a new installer/signing strategy.
