param(
    [string]$Url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-14-13-19/ffmpeg-N-125608-g150f7d15df-win64-lgpl.zip",
    [string]$Sha256 = "7a1f6d1d8acd98c3f04529700281f5302c1be5df725d6cab34322fd2a4411bad"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root ".tools"
$Archive = Join-Path $Tools "ffmpeg-N-125608-g150f7d15df-win64-lgpl.zip"
$Extracted = Join-Path $Tools "ffmpeg-extracted"
$Destination = Join-Path $Tools "ffmpeg"

New-Item -ItemType Directory -Force -Path $Tools | Out-Null
Invoke-WebRequest -Uri $Url -OutFile $Archive -Headers @{ "User-Agent" = "Bilidown-build" }
$Actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Sha256.ToLowerInvariant()) {
    throw "FFmpeg archive checksum mismatch. Expected $Sha256, got $Actual."
}

if (Test-Path -LiteralPath $Extracted) { Remove-Item -LiteralPath $Extracted -Recurse -Force }
if (Test-Path -LiteralPath $Destination) { Remove-Item -LiteralPath $Destination -Recurse -Force }
Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted
$Ffmpeg = Get-ChildItem -LiteralPath $Extracted -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$Ffprobe = Get-ChildItem -LiteralPath $Extracted -Recurse -Filter ffprobe.exe | Select-Object -First 1
if (-not $Ffmpeg -or -not $Ffprobe) { throw "The verified archive does not contain ffmpeg.exe and ffprobe.exe." }

New-Item -ItemType Directory -Force -Path (Join-Path $Destination "bin") | Out-Null
Copy-Item -LiteralPath $Ffmpeg.FullName -Destination (Join-Path $Destination "bin\ffmpeg.exe")
Copy-Item -LiteralPath $Ffprobe.FullName -Destination (Join-Path $Destination "bin\ffprobe.exe")

$LicenseFiles = Get-ChildItem -LiteralPath $Extracted -Recurse -File | Where-Object {
    $_.Name -match "^(LICENSE|COPYING|README|VERSION)" -or $_.DirectoryName -match "licenses?"
}
if ($LicenseFiles) {
    $LicenseDestination = Join-Path $Destination "licenses"
    New-Item -ItemType Directory -Force -Path $LicenseDestination | Out-Null
    foreach ($File in $LicenseFiles) {
        Copy-Item -LiteralPath $File.FullName -Destination (Join-Path $LicenseDestination $File.Name) -Force
    }
}

$Version = & (Join-Path $Destination "bin\ffmpeg.exe") -version | Select-Object -First 1
$BuildInfo = @(
    $Version
    "Archive: $Url"
    "SHA256: $Actual"
    "Build project: https://github.com/BtbN/FFmpeg-Builds"
) -join [Environment]::NewLine
Set-Content -LiteralPath (Join-Path $Destination "BUILD_INFO.txt") -Value $BuildInfo -Encoding utf8
Write-Output $BuildInfo
