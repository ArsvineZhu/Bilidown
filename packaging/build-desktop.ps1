param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Ffmpeg = Join-Path $Root ".tools\ffmpeg\bin\ffmpeg.exe"
$Ffprobe = Join-Path $Root ".tools\ffmpeg\bin\ffprobe.exe"
$CargoBin = Join-Path $HOME ".cargo\bin"

if ((Test-Path -LiteralPath (Join-Path $CargoBin "cargo.exe") -PathType Leaf) -and ($env:Path -notlike "*$CargoBin*")) {
    $env:Path = "$CargoBin;$env:Path"
}

if (-not (Test-Path -LiteralPath $Ffmpeg) -or -not (Test-Path -LiteralPath $Ffprobe)) {
    throw "Run packaging\prepare-ffmpeg.ps1 before building."
}

Push-Location $Root
try {
    & $Python -m PyInstaller --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is unavailable. Install the .[dev] dependencies."
    }
    pnpm --dir frontend install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) {
        throw "pnpm install failed with exit code $LASTEXITCODE"
    }
    pnpm --dir frontend desktop:build
    if ($LASTEXITCODE -ne 0) {
        throw "Tauri build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Desktop bundles: src-tauri\target\release\bundle"
} finally {
    Pop-Location
}
