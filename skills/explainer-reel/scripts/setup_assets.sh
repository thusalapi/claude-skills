#!/usr/bin/env bash
# One-time setup for reel.py: Python packages, offline voice model, fonts and a
# synthesised sound-effect kit. Re-running skips anything already downloaded.
# Usage: bash setup_assets.sh [ASSET_DIR]   (default ~/.explainer-reel-assets)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
A="${1:-${REEL_ASSETS:-$HOME/.explainer-reel-assets}}"
mkdir -p "$A/kokoro" "$A/fonts" "$A/sounds"

command -v ffmpeg >/dev/null || { echo "ffmpeg is required (apt install ffmpeg / brew install ffmpeg)"; exit 1; }

PKGS="kokoro-onnx soundfile scipy pillow numpy"
pip install -q $PKGS --break-system-packages 2>/dev/null || pip install -q $PKGS

# Kokoro TTS (Apache-2.0), runs offline on CPU
cd "$A/kokoro"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "$f" ] || curl -fsSL -o "$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done

# Fonts (SIL Open Font Licence): DM Serif Display for headlines, Inter for labels
cd "$A/fonts"
for f in DMSerifDisplay-Regular.ttf DMSerifDisplay-Italic.ttf; do
  [ -s "$f" ] || curl -fsSL -o "$f" "https://raw.githubusercontent.com/google/fonts/main/ofl/dmserifdisplay/$f"
done
if [ ! -s Inter-SemiBold.ttf ]; then
  curl -fsSL -o inter.zip https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
  python3 - <<'PY'
import zipfile
z = zipfile.ZipFile("inter.zip")
for w in ("Medium", "SemiBold"):
    open(f"Inter-{w}.ttf", "wb").write(z.read(f"extras/ttf/Inter-{w}.ttf"))
PY
  rm inter.zip
fi

# Sound effects: generated, so there is nothing to license
[ -s "$A/sounds/whoosh.wav" ] || python3 "$HERE/make_sfx.py" "$A/sounds"

echo "assets ready in $A"
