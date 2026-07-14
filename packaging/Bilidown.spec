# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys
import tomllib

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
is_macos = sys.platform == "darwin"
executable_suffix = "" if is_macos else ".exe"
target_arch = os.getenv("BILIDOWN_TARGET_ARCH") if is_macos else None
codesign_identity = os.getenv("BILIDOWN_CODESIGN_IDENTITY") or None
yt_datas, yt_binaries, yt_hiddenimports = collect_all("yt_dlp")

datas = yt_datas + [
    (str(root / "frontend" / "dist"), "frontend/dist"),
    (str(root / "packaging" / "THIRD_PARTY_NOTICES.txt"), "."),
    (str(root / "packaging" / "FFMPEG_SOURCE.txt"), "."),
    (str(root / "README.md"), "."),
    (str(root / "SECURITY.md"), "."),
    (str(root / "docs"), "docs"),
    (str(root / ".tools" / "ffmpeg" / "BUILD_INFO.txt"), "ffmpeg"),
    (str(root / ".tools" / "ffmpeg" / "licenses"), "ffmpeg/licenses"),
    (str(root / "LICENSE"), "."),
]
binaries = yt_binaries + [
    (str(root / ".tools" / "ffmpeg" / "bin" / f"ffmpeg{executable_suffix}"), "ffmpeg/bin"),
    (str(root / ".tools" / "ffmpeg" / "bin" / f"ffprobe{executable_suffix}"), "ffmpeg/bin"),
]

a = Analysis(
    [str(root / "packaging" / "entrypoint.py")],
    pathex=[str(root / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=yt_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Bilidown",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=target_arch,
    codesign_identity=codesign_identity,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Bilidown",
)

if is_macos:
    app = BUNDLE(
        coll,
        name="Bilidown.app",
        icon=None,
        bundle_identifier="com.bilidown.local",
        version=version,
        target_arch=target_arch,
        codesign_identity=codesign_identity,
        info_plist={
            "CFBundleDisplayName": "Bilidown",
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
        },
    )
