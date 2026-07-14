param(
    [string]$Python = "python",
    [string]$ArtifactVersion = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Ffmpeg = Join-Path $Root ".tools\ffmpeg\bin\ffmpeg.exe"
$Ffprobe = Join-Path $Root ".tools\ffmpeg\bin\ffprobe.exe"
$BuildInfo = Join-Path $Root ".tools\ffmpeg\BUILD_INFO.txt"

if (-not $ArtifactVersion) {
    $VersionLine = Select-String -LiteralPath (Join-Path $Root "pyproject.toml") -Pattern '^version\s*=\s*"([^"]+)"$' | Select-Object -First 1
    if (-not $VersionLine) { throw "Could not read project version from pyproject.toml." }
    $ArtifactVersion = $VersionLine.Matches[0].Groups[1].Value
}
if ($ArtifactVersion -notmatch '^[0-9A-Za-z][0-9A-Za-z.+-]*$') {
    throw "ArtifactVersion contains unsupported filename characters: $ArtifactVersion"
}

if (-not (Test-Path -LiteralPath $Ffmpeg) -or -not (Test-Path -LiteralPath $Ffprobe) -or -not (Test-Path -LiteralPath $BuildInfo)) {
    throw "Run packaging\prepare-ffmpeg.ps1 before building."
}

$VersionLine = & $Ffmpeg -version | Select-Object -First 1
if ($VersionLine -notmatch "g150f7d15df-20260714") {
    throw "The portable build is pinned to FFmpeg commit 150f7d15df; found: $VersionLine"
}

Push-Location $Root
try {
    pnpm --dir frontend install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw "pnpm install failed with exit code $LASTEXITCODE" }
    pnpm --dir frontend build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed with exit code $LASTEXITCODE" }
    & $Python -m PyInstaller --noconfirm --clean packaging\Bilidown.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

    $PortableDir = Join-Path $Root "dist\Bilidown"
    $ArchivePath = Join-Path $Root "dist\Bilidown-$ArtifactVersion-windows-x64.zip"
    Compress-Archive -LiteralPath $PortableDir -DestinationPath $ArchivePath -CompressionLevel Optimal -Force
    $Hash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$ArchivePath.sha256" -Value "$Hash  $([IO.Path]::GetFileName($ArchivePath))" -Encoding ascii
    Write-Host "Portable archive: $ArchivePath"
} finally {
    Pop-Location
}
