param(
    [string]$Python = "python",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Ffmpeg = Join-Path $Root ".tools\ffmpeg\bin\ffmpeg.exe"
$Ffprobe = Join-Path $Root ".tools\ffmpeg\bin\ffprobe.exe"
$StageRoot = Join-Path $Root "dist\portable-stage"
$CargoBin = Join-Path $HOME ".cargo\bin"

if ((Test-Path -LiteralPath (Join-Path $CargoBin "cargo.exe") -PathType Leaf) -and ($env:Path -notlike "*$CargoBin*")) {
    $env:Path = "$CargoBin;$env:Path"
}

function Get-ProjectVersion {
    $version = & $Python -c "import tomllib; from pathlib import Path; print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
    if ($LASTEXITCODE -ne 0 -or -not $version) {
        throw "Unable to read the project version with $Python."
    }
    return $version.Trim()
}

function Get-RustTarget {
    $cargoRustc = Join-Path $HOME ".cargo\bin\rustc.exe"
    $rustc = if (Test-Path -LiteralPath $cargoRustc -PathType Leaf) { $cargoRustc } else { "rustc" }
    $targetLine = (& $rustc -vV | Where-Object { $_ -like "host: *" } | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or -not $targetLine) {
        throw "Unable to determine the Rust host target."
    }
    return $targetLine.Substring("host: ".Length).Trim()
}

Push-Location $Root
try {
    if (-not (Test-Path -LiteralPath $Ffmpeg) -or -not (Test-Path -LiteralPath $Ffprobe)) {
        throw "Run packaging\prepare-ffmpeg.ps1 before building."
    }

    $version = Get-ProjectVersion
    $target = Get-RustTarget
    if ($target -ne "x86_64-pc-windows-msvc") {
        throw "Windows portable packaging currently supports x86_64-pc-windows-msvc; found $target."
    }

    if (-not $SkipBuild) {
        & $Python -m PyInstaller --version | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller is unavailable. Install the .[dev] dependencies."
        }
        pnpm --dir frontend install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) {
            throw "pnpm install failed with exit code $LASTEXITCODE"
        }
        pnpm --dir frontend desktop:build:portable
        if ($LASTEXITCODE -ne 0) {
            throw "Tauri portable build failed with exit code $LASTEXITCODE"
        }
    }

    $desktopExecutable = Join-Path $Root "src-tauri\target\release\bilidown-desktop.exe"
    $sidecarExecutable = Join-Path $Root "src-tauri\target\release\bilidown-backend.exe"
    foreach ($required in @($desktopExecutable, $sidecarExecutable, (Join-Path $PSScriptRoot "PORTABLE_README_zh-CN.txt"), (Join-Path $PSScriptRoot "THIRD_PARTY_NOTICES.txt"), (Join-Path $PSScriptRoot "FFMPEG_SOURCE.txt"))) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Portable build input is missing: $required"
        }
    }

    $portableName = "Bilidown-$version-windows-x64"
    $stage = Join-Path $StageRoot $portableName
    $archive = Join-Path $Root "dist\$portableName-portable.zip"
    $checksum = "$archive.sha256"
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
    Remove-Item -LiteralPath $archive, $checksum -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $stage -Force | Out-Null

    Copy-Item -LiteralPath $desktopExecutable -Destination (Join-Path $stage "Bilidown.exe")
    Copy-Item -LiteralPath $sidecarExecutable -Destination (Join-Path $stage "bilidown-backend.exe")
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "PORTABLE_README_zh-CN.txt") -Destination (Join-Path $stage "README.txt")
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "THIRD_PARTY_NOTICES.txt") -Destination $stage
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "FFMPEG_SOURCE.txt") -Destination $stage
    $manifest = Join-Path $stage "SHA256SUMS.txt"
    Get-ChildItem -LiteralPath $stage -File |
        Sort-Object Name |
        ForEach-Object {
            $fileHash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
            "{0}  {1}" -f $fileHash.Hash.ToLowerInvariant(), $_.Name
        } |
        Set-Content -LiteralPath $manifest -Encoding ascii

    Compress-Archive -LiteralPath $stage -DestinationPath $archive -CompressionLevel Optimal
    $hash = Get-FileHash -LiteralPath $archive -Algorithm SHA256
    "{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $archive) | Set-Content -LiteralPath $checksum -Encoding ascii

    $entries = [System.IO.Compression.ZipFile]::OpenRead($archive).Entries.FullName
    $expectedEntries = @(
        "$portableName\Bilidown.exe",
        "$portableName\bilidown-backend.exe",
        "$portableName\README.txt",
        "$portableName\THIRD_PARTY_NOTICES.txt",
        "$portableName\FFMPEG_SOURCE.txt",
        "$portableName\SHA256SUMS.txt"
    )
    $missingEntries = $expectedEntries | Where-Object { $_ -notin $entries }
    if ($missingEntries) {
        throw "Portable archive is missing: $($missingEntries -join ', ')"
    }

    Write-Host "Portable archive: $archive"
    Write-Host "Checksum: $checksum"
    Remove-Item -LiteralPath $stage -Recurse -Force
} finally {
    Pop-Location
}
