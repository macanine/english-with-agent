#!/usr/bin/env python3
"""Convert a full-sentence SRT (with [Host N] speaker tags) into transcript_data.json
for the interactive IELTS simulator.

Usage:
    python3 srt_to_transcript.py <episode_dir>
Reads  <episode_dir>/transcript_full_sentence.srt
Writes <episode_dir>/transcript_data.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

TS_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")
SPK_RE = re.compile(r"^\[([^\]]+)\]\s*")


def ts_to_sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path: Path):
    raw = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n", raw.strip())
    items = []
    for block in blocks:
        lines = [ln for ln in block.strip().splitlines() if ln.strip() != ""]
        if len(lines) < 2:
            continue
        m = TS_RE.search(lines[1]) if not TS_RE.search(lines[0]) else TS_RE.search(lines[0])
        if not m:
            continue
        start = ts_to_sec(*m.group(1, 2, 3, 4))
        end = ts_to_sec(*m.group(5, 6, 7, 8))
        text_lines = lines[2:] if TS_RE.search(lines[1]) else lines[1:]
        text = " ".join(text_lines).strip()
        speaker = "Host 1"
        spk = SPK_RE.match(text)
        if spk:
            speaker = spk.group(1).strip()
            text = SPK_RE.sub("", text)
        start_ts = "00:%02d:%02d,%03d" % (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        end_ts = "00:%02d:%02d,%03d" % (int(m.group(6)), int(m.group(7)), int(m.group(8)))
        items.append({
            "id": len(items) + 1,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "start": round(start, 2),
            "end": round(end, 2),
            "speaker": speaker,
            "text": text,
        })
    return items


def main():
    ap = argparse.ArgumentParser(description="SRT -> transcript_data.json")
    ap.add_argument("episode_dir", help="Episode directory containing transcript_full_sentence.srt")
    ap.add_argument("--srt", default="transcript_full_sentence.srt", help="SRT file name inside the episode dir")
    args = ap.parse_args()

    ep = Path(args.episode_dir)
    srt = ep / args.srt
    if not srt.exists():
        sys.exit(f"[-] SRT not found: {srt}")

    items = parse_srt(srt)
    if not items:
        sys.exit("[-] No subtitle blocks parsed — check the SRT format.")
    if not all(i["speaker"] for i in items):
        sys.exit("[-] Some blocks are missing [Host N] speaker tags.")

    out = ep / "transcript_data.json"
    out.write_text(json.dumps(items, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[+] Wrote {len(items)} transcript lines -> {out}")


if __name__ == "__main__":
    main()
