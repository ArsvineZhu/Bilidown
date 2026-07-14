#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
cd "$ROOT"
PROJECT_VERSION="$("$PYTHON" -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])' 2>/dev/null || true)"
ARTIFACT_VERSION="${ARTIFACT_VERSION:-$PROJECT_VERSION}"
ARCH="$(uname -m)"

if [[ ! "$ARTIFACT_VERSION" =~ ^[0-9A-Za-z][0-9A-Za-z.+-]*$ ]]; then
  echo "ARTIFACT_VERSION contains unsupported filename characters: $ARTIFACT_VERSION" >&2
  exit 1
fi
if [[ "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
  echo "Unsupported macOS architecture: $ARCH" >&2
  exit 1
fi
for binary in ffmpeg ffprobe; do
  test -x "$ROOT/.tools/ffmpeg/bin/$binary" || {
    echo "Run packaging/prepare-ffmpeg-macos.sh before building." >&2
    exit 1
  }
done

pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
export BILIDOWN_TARGET_ARCH="$ARCH"
"$PYTHON" -m PyInstaller --noconfirm --clean packaging/Bilidown.spec

APP="$ROOT/dist/Bilidown.app"
test -x "$APP/Contents/MacOS/Bilidown"
if [[ -n "${BILIDOWN_CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp --sign "$BILIDOWN_CODESIGN_IDENTITY" "$APP"
else
  codesign --force --deep --sign - "$APP"
fi
codesign --verify --deep --strict --verbose=2 "$APP"

ARCHIVE="$ROOT/dist/Bilidown-$ARTIFACT_VERSION-macos-$ARCH.app.zip"
rm -f "$ARCHIVE" "$ARCHIVE.sha256"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ARCHIVE"
HASH="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
printf '%s  %s\n' "$HASH" "$(basename "$ARCHIVE")" > "$ARCHIVE.sha256"
echo "Portable archive: $ARCHIVE"
