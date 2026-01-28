#!/bin/bash

set -euo pipefail

INPUT="ui/public/Janus_God_and_Bull_Video_Generation.mp4"
OUTPUT="ui/public/hero-video-processed.mp4"

# Option 1: Zoom and crop (12% zoom, centered toward top)
ffmpeg -i "$INPUT" \
  -vf "scale=1.12*iw:1.12*ih,crop=iw/1.12:ih/1.12:0.06*iw:0" \
  -c:v libx264 -preset slow -crf 18 \
  -an \
  "$OUTPUT"

echo "Processed video saved to $OUTPUT"
