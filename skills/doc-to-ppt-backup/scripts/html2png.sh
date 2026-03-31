#!/usr/bin/env bash
# html2png.sh - HTML to PNG conversion using Chrome headless
# Usage: html2png.sh <input.html> [output.png]
set -euo pipefail

INPUT="${1:?Usage: html2png.sh <input.html> [output.png]}"
OUTPUT="${2:-${INPUT%.html}.png}"

# Ensure absolute path
if [[ ! "$INPUT" = /* ]]; then
  INPUT="$(pwd)/$INPUT"
fi

# Try Chrome first, then Chromium
if command -v google-chrome &> /dev/null; then
  CMD="google-chrome"
elif command -v chromium &> /dev/null; then
  CMD="chromium"
elif command -v chromium-browser &> /dev/null; then
  CMD="chromium-browser"
else
  echo "Error: Chrome/Chromium not found. Please install Chrome or Chromium."
  exit 1
fi

"$CMD" --headless --disable-gpu --no-sandbox \
  --screenshot="$OUTPUT" \
  --window-size=1200,675 \
  "file://$INPUT" 2>/dev/null

echo "✓ Generated: $OUTPUT"
