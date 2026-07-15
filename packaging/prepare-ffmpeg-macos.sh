#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
SOURCES="$TOOLS/sources"
BUILD="$TOOLS/ffmpeg-build"
DEPS="$TOOLS/ffmpeg-deps"
DEST="$TOOLS/ffmpeg"
FFMPEG_VERSION="8.1.2"
LAME_VERSION="3.100"
FFMPEG_ARCHIVE="ffmpeg-$FFMPEG_VERSION.tar.xz"
LAME_ARCHIVE="lame-$LAME_VERSION.tar.gz"
FFMPEG_URL="https://ffmpeg.org/releases/$FFMPEG_ARCHIVE"
LAME_URL="https://downloads.sourceforge.net/project/lame/lame/$LAME_VERSION/$LAME_ARCHIVE"
FFMPEG_SHA256="464beb5e7bf0c311e68b45ae2f04e9cc2af88851abb4082231742a74d97b524c"
LAME_SHA256="ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e"
DEPLOYMENT_TARGET="13.0"
ARCH="$(uname -m)"

if [[ "$ARCH" != "arm64" ]]; then
  echo "Official macOS builds require Apple Silicon (arm64); found: $ARCH" >&2
  exit 1
fi

mkdir -p "$SOURCES"

download_and_verify() {
  local url="$1"
  local destination="$2"
  local expected="$3"
  if [[ ! -f "$destination" ]]; then
    curl --fail --location --retry 3 --output "$destination" "$url"
  fi
  local actual
  actual="$(shasum -a 256 "$destination" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "Checksum mismatch for $(basename "$destination"): expected $expected, got $actual" >&2
    exit 1
  fi
}

download_and_verify "$FFMPEG_URL" "$SOURCES/$FFMPEG_ARCHIVE" "$FFMPEG_SHA256"
download_and_verify "$LAME_URL" "$SOURCES/$LAME_ARCHIVE" "$LAME_SHA256"

rm -rf "$BUILD" "$DEPS" "$DEST"
mkdir -p "$BUILD" "$DEPS" "$DEST/bin" "$DEST/licenses"
tar -xf "$SOURCES/$LAME_ARCHIVE" -C "$BUILD"
tar -xf "$SOURCES/$FFMPEG_ARCHIVE" -C "$BUILD"

export MACOSX_DEPLOYMENT_TARGET="$DEPLOYMENT_TARGET"
export CFLAGS="-O2 -mmacosx-version-min=$DEPLOYMENT_TARGET"
export LDFLAGS="-mmacosx-version-min=$DEPLOYMENT_TARGET"

pushd "$BUILD/lame-$LAME_VERSION" >/dev/null
./configure \
  --prefix="$DEPS" \
  --disable-shared \
  --enable-static \
  --disable-frontend
make -j"$(sysctl -n hw.logicalcpu)"
make install
popd >/dev/null

FFMPEG_CONFIGURE=(
  --prefix="$DEST"
  --cc=clang
  --disable-autodetect
  --disable-doc
  --disable-debug
  --disable-ffplay
  --disable-shared
  --enable-static
  --enable-libmp3lame
  --pkg-config-flags=--static
  --extra-cflags="-I$DEPS/include -mmacosx-version-min=$DEPLOYMENT_TARGET"
  --extra-ldflags="-L$DEPS/lib -mmacosx-version-min=$DEPLOYMENT_TARGET"
)

pushd "$BUILD/ffmpeg-$FFMPEG_VERSION" >/dev/null
PKG_CONFIG_PATH="$DEPS/lib/pkgconfig" ./configure "${FFMPEG_CONFIGURE[@]}"
make -j"$(sysctl -n hw.logicalcpu)"
make install
cp COPYING.LGPLv2.1 COPYING.LGPLv3 "$DEST/licenses/"
popd >/dev/null
cp "$BUILD/lame-$LAME_VERSION/COPYING" "$DEST/licenses/LAME-COPYING"

for binary in ffmpeg ffprobe; do
  test -x "$DEST/bin/$binary"
  while read -r dependency _; do
    [[ -z "$dependency" ]] && continue
    case "$dependency" in
      /usr/lib/*|/System/Library/*) ;;
      *) echo "$binary has a non-system dynamic dependency: $dependency" >&2; exit 1 ;;
    esac
  done < <(otool -L "$DEST/bin/$binary" | tail -n +2)
done

{
  "$DEST/bin/ffmpeg" -version | head -n 1
  echo "Architecture: $ARCH"
  echo "Minimum macOS: $DEPLOYMENT_TARGET"
  echo "FFmpeg source: $FFMPEG_URL"
  echo "FFmpeg SHA256: $FFMPEG_SHA256"
  echo "LAME source: $LAME_URL"
  echo "LAME SHA256: $LAME_SHA256"
  printf 'Configure:'
  printf ' %q' "${FFMPEG_CONFIGURE[@]}"
  printf '\n'
} > "$DEST/BUILD_INFO.txt"

echo "Prepared native $ARCH FFmpeg in $DEST"
