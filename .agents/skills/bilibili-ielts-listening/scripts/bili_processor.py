#!/usr/bin/env python3
"""Bilibili Audio & Subtitle Processor (stage 1 of the IELTS listening pipeline).

1. Downloads audio from a Bilibili video (BV id or URL) via yt-dlp.
2. Converts audio to 16 kHz mono WAV via macOS native afconvert.
3. Transcribes with whisper.cpp (whisper-cli, Metal accelerated).
4. Merges chopped ASR segments into complete, full-sentence subtitles (.srt)
   and a clean speaker-attributed transcript (.md).

Each stage is skipped automatically when its output already exists
(override with --force). After this script, run srt_to_transcript.py and
build_exam_assets.py to produce the interactive simulator.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL_PATH = os.path.expanduser("~/.cache/whisper.cpp/ggml-base.en.bin")

# Lexical & acoustic rectification rules (generic homophones + this project's known episodes)
ACOUSTIC_CORRECTIONS = [
    (r"\bXinju\b", "Xingyu"),
    (r"\bJingyu\b", "Xingyu"),
    (r"\bThe People As Daily\b", "The People's Daily"),
    (r"\bgressed the weight\b", "grasped the weight"),
    (r"\bfind a fair\b", "find a fare"),
    (r"\bThe source is detailed\b", "The sources detailed"),
    (r"\bNot more, it was packed\b", "Not anymore, it was packed"),
    (r"\ba severance\b", "as severance"),
    (r"\bhalf a month salary\b", "half a month's salary"),
    (r"\bhalf a month as pay\b", "half a month's pay"),
    (r"\bwho is hired for like a corporate role\b", "who was hired for like a corporate role"),
    (r"\bthat, a huge change\b", "that's a huge change"),
    (r"\bthere are major car parts maker\b", "they are a major car-parts maker"),
    (r"\bI've loaded it for when I hit 100k\b", "Upload it for when I hit 100k"),
    (r"\bmy that dog scared me\b", "that dog scared me"),
    (r"\bsmall talkies getting to know each other context\b", "small-talky, getting-to-know-each-other context"),
    (r"\bturn them on them\b", "turn them on then"),
    (r"\bgrowth for months\b", "growth in four months"),
]


def die(msg: str, hint: str = ""):
    print(f"[-] {msg}", file=sys.stderr)
    if hint:
        print(f"    hint: {hint}", file=sys.stderr)
    sys.exit(1)


def resolve_bin(name: str, fallback_paths=()) -> str:
    """Find a binary via $PATH, then well-known locations."""
    found = shutil.which(name)
    if found:
        return found
    for p in fallback_paths:
        p = os.path.expanduser(p)
        if os.path.exists(p):
            return p
    return ""


def clean_text(text: str) -> str:
    for pattern, replacement in ACOUSTIC_CORRECTIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()


def download_bilibili_audio(url_or_bvid: str, output_dir: Path, force: bool) -> Path:
    yt_dlp = resolve_bin("yt-dlp", ["~/.local/bin/yt-dlp", "~/bin/yt-dlp"])
    if not yt_dlp:
        die("yt-dlp not found", "install with: brew install yt-dlp  (or pip install -U yt-dlp)")
    target = output_dir / "audio.m4a"
    if target.exists() and target.stat().st_size > 100_000 and not force:
        print(f"[+] Audio already exists, skipping download: {target} ({target.stat().st_size // 1024} KB)")
        return target

    print(f"[*] Downloading audio from {url_or_bvid} ...")
    res = subprocess.run(
        [yt_dlp, "-f", "ba/30280/30232/30216", "--no-playlist", url_or_bvid, "-o", str(target)],
        capture_output=True, text=True,
    )
    if res.returncode != 0 or not target.exists():
        die(f"yt-dlp failed: {res.stderr.strip()[:400]}",
            "check the URL/BV id and your network; bilibili may throttle repeated requests")
    print(f"[+] Downloaded: {target} ({target.stat().st_size // 1024} KB)")
    return target


def convert_to_wav(m4a_path: Path, wav_path: Path, force: bool) -> Path:
    if wav_path.exists() and wav_path.stat().st_size > 100_000 and not force:
        print(f"[+] 16kHz WAV already exists, skipping conversion: {wav_path}")
        return wav_path
    afconvert = resolve_bin("afconvert", ["/usr/bin/afconvert"])
    if not afconvert:
        die("afconvert not found — this pipeline requires macOS")
    print(f"[*] Converting to 16 kHz mono WAV ...")
    res = subprocess.run(
        [afconvert, "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(m4a_path), str(wav_path)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        die(f"afconvert failed: {res.stderr.strip()[:300]}")
    print(f"[+] WAV ready: {wav_path} ({wav_path.stat().st_size // 1024} KB)")
    return wav_path


def run_whisper(wav_path: Path, output_prefix: Path, model_path: str, force: bool) -> Path:
    json_path = Path(f"{output_prefix}.json")
    if json_path.exists() and json_path.stat().st_size > 1000 and not force:
        print(f"[+] Whisper output already exists, skipping transcription: {json_path}")
        return json_path
    whisper = resolve_bin("whisper-cli", ["/opt/homebrew/bin/whisper-cli", "/usr/local/bin/whisper-cli"])
    if not whisper:
        die("whisper-cli not found", "install with: brew install whisper-cpp")
    if not os.path.exists(model_path):
        die(f"whisper model not found: {model_path}",
            "download with: whisper-cpp download-ggml-model base.en  (or pass --model)")
    print(f"[*] Transcribing with whisper.cpp (Metal) — this can take a minute ...")
    res = subprocess.run(
        [whisper, "-m", model_path, "-f", str(wav_path), "-l", "en", "-fa", "-t", "8",
         "-ojf", "-of", str(output_prefix)],
        capture_output=True, text=True,
    )
    if res.returncode != 0 or not json_path.exists():
        die(f"whisper-cli failed: {res.stderr.strip()[:400]}")
    print(f"[+] Transcription complete: {json_path}")
    return json_path


def merge_sentences_and_export(whisper_json_path: Path, output_srt: Path, output_md: Path, title: str):
    data = json.loads(Path(whisper_json_path).read_text(encoding="utf-8"))
    raw_segments = data.get("transcription", [])
    merged = []

    # Check if token-level timestamps are present
    has_tokens = any(bool(seg.get("tokens")) for seg in raw_segments)
    if has_tokens:
        curr_tokens = []
        for seg in raw_segments:
            for tok in seg.get("tokens", []):
                t_text = tok.get("text", "")
                if t_text.startswith("[_") and t_text.endswith("]"):
                    continue
                curr_tokens.append(tok)
                if re.search(r"[\.\?!]$", t_text.strip()):
                    full_text = "".join(t["text"] for t in curr_tokens).strip()
                    if not re.search(r"\b(e\.g|i\.e|vs|Mr|Ms|Dr)\.$", full_text, re.I):
                        s_from = curr_tokens[0]["timestamps"]["from"]
                        s_to = curr_tokens[-1]["timestamps"]["to"]
                        full_clean = clean_text(full_text)
                        if full_clean:
                            merged.append({"from": s_from, "to": s_to, "text": full_clean})
                        curr_tokens = []
        if curr_tokens:
            full_text = "".join(t["text"] for t in curr_tokens).strip()
            full_clean = clean_text(full_text)
            if full_clean:
                merged.append({"from": curr_tokens[0]["timestamps"]["from"], "to": curr_tokens[-1]["timestamps"]["to"], "text": full_clean})
    else:
        curr_parts = []
        curr_start = curr_end = None

        def is_terminal(t: str) -> bool:
            return t.rstrip().endswith((".", "?", "!"))

        for seg in raw_segments:
            t_from, t_to = seg["timestamps"]["from"], seg["timestamps"]["to"]
            txt = clean_text(seg["text"])
            if not txt:
                continue
            if not curr_parts:
                curr_start = t_from
                if not txt.startswith("- ") and txt[0].islower():
                    txt = txt[0].upper() + txt[1:]
            if txt.startswith("- ") and curr_parts:  # speaker turn marker
                merged.append({"from": curr_start, "to": curr_end, "text": " ".join(curr_parts)})
                curr_parts, curr_start = [], t_from
            curr_parts.append(txt)
            curr_end = t_to
            if is_terminal(txt):
                full = " ".join(curr_parts)
                if not re.search(r"\b(e\.g|i\.e|vs|Mr|Ms|Dr)\.$", full):
                    merged.append({"from": curr_start, "to": curr_end, "text": full})
                    curr_parts, curr_start = [], None
        if curr_parts:
            merged.append({"from": curr_start, "to": curr_end, "text": " ".join(curr_parts)})

    annotated, current_spk = [], "Host 1"
    for item in merged:
        txt = item["text"]
        if txt.startswith("- "):
            txt = txt[2:].strip()
            current_spk = "Host 2" if current_spk == "Host 1" else "Host 1"
        annotated.append({**item, "speaker": current_spk, "text": txt})

    with open(output_srt, "w", encoding="utf-8") as f:
        for idx, it in enumerate(annotated, 1):
            f.write(f"{idx}\n{it['from']} --> {it['to']}\n[{it['speaker']}] {it['text']}\n\n")
    print(f"[+] Full-sentence subtitles: {output_srt} ({len(annotated)} lines)")

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(f"# Audio Transcript: {title}\n\n")
        f.write("> **Format**: full-sentence dialogue transcript with speaker attribution\n\n---\n\n")
        last_spk = None
        for it in annotated:
            label = "Host 1 (Lead Analyst)" if it["speaker"] == "Host 1" else "Host 2 (Inquisitive Co-host)"
            if it["speaker"] != last_spk:
                f.write(f"\n\n**[{label}]** `[{it['from']} - {it['to']}]`\n\n")
                last_spk = it["speaker"]
            f.write(f"{it['text']} ")
    print(f"[+] Structured transcript: {output_md}")


def main():
    ap = argparse.ArgumentParser(description="Stage 1: download → convert → transcribe → merge sentences")
    ap.add_argument("url", help="Bilibili video URL or BV id")
    ap.add_argument("--outdir", default="./output", help="Output episode directory")
    ap.add_argument("--model", default=DEFAULT_MODEL_PATH, help="whisper ggml model path")
    ap.add_argument("--title", default="Untitled Episode", help="Episode title used in the transcript header")
    ap.add_argument("--force", action="store_true", help="Re-run every stage even if outputs exist")
    args = ap.parse_args()

    if not re.match(r"(https?://|BV[\w]+)", args.url, re.IGNORECASE):
        die(f"not a Bilibili URL or BV id: {args.url}", "example: https://www.bilibili.com/video/BV1AJe36fE9Q/")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    m4a = download_bilibili_audio(args.url, out, args.force)
    wav = convert_to_wav(m4a, out / "audio_16k.wav", args.force)
    js = run_whisper(wav, out / "whisper_raw", args.model, args.force)
    merge_sentences_and_export(js, out / "transcript_full_sentence.srt", out / "transcript_annotated.md", args.title)
    print("\n[SUCCESS] Stage 1 complete. Next: srt_to_transcript.py + build_exam_assets.py")


if __name__ == "__main__":
    main()
