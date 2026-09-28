#!/usr/bin/env bash
# One-click stage 1 runner: download -> 16kHz WAV -> whisper -> full-sentence SRT + transcript MD.
# Usage: run_pipeline.sh <bilibili_url_or_bvid> <output_dir> [episode_title]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <bilibili_url_or_bvid> <output_dir> [episode_title]"
  echo "Example: $0 https://www.bilibili.com/video/BV1AJe36fE9Q/ ./episodes/BV1AJe36fE9Q_Economist \"The Economist · Youth Unemployment\""
  exit 1
fi

URL="$1"; OUT="$2"; TITLE="${3:-Untitled Episode}"

echo "==> Stage 1/3: download + transcribe + merge sentences"
python3 "${SCRIPT_DIR}/bili_processor.py" "$URL" --outdir "$OUT" --title "$TITLE"

echo "==> Stage 2/3: SRT -> transcript_data.json"
python3 "${SCRIPT_DIR}/srt_to_transcript.py" "$OUT"

echo "==> Stage 3/3: author exam_data.json (agent step), then build assets:"
echo "    python3 ${SCRIPT_DIR}/build_exam_assets.py \"$OUT\""
echo "Done. Open ${OUT}/ielts_listening_interactive.html to start practicing."
