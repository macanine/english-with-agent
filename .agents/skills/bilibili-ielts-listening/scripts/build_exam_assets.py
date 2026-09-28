#!/usr/bin/env python3
"""Build all exam deliverables for an episode from its single-source data files.

Inputs  (inside the episode directory):
    exam_data.json         – the authored exam (40 questions across 4 parts)
    transcript_data.json   – transcript lines (from srt_to_transcript.py)
Outputs:
    ielts_listening_interactive.html       – zero-dependency CDI simulator
    ielts_listening_practice.md            – printable exam paper
    ielts_listening_answers_and_analysis.md – answer key + distractor analysis

Usage:
    python3 build_exam_assets.py <episode_dir> [--audio audio.m4a]

Agents must NOT hand-edit the generated files — edit exam_data.json and rebuild.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_passage_data import build_passage_data, generate_passage_markdown

DEFAULT_TEMPLATE = SCRIPT_DIR.parent / "assets" / "exam_simulator.html.template"

LETTER_TYPES = ("mcq", "matching", "summary")


# ---------------------------------------------------------------- data loading
def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[-] Missing input file: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"[-] Invalid JSON in {path}: {e}")


def collect_meta(exam: dict) -> dict:
    """Flatten every question into QMETA: id -> {part, type, time, answers, quote, analysis, labels}."""
    meta = {}

    def put(qid, part, qtype, answers, quote="", analysis="", time=None, labels=None):
        if qid in meta:
            sys.exit(f"[-] Duplicate question id {qid}")
        meta[qid] = {
            "id": qid, "part": part, "type": qtype, "answers": answers,
            "quote": quote, "analysis": analysis, "time": time, "labels": labels or {},
        }

    for part in exam["parts"]:
        pno = part["part"]
        # note items carry the authoritative audio time for their question
        note_time = {}
        for sec in part.get("sections", []):
            for n in sec.get("notes", []):
                if n.get("id"):
                    note_time[n["id"]] = n.get("time")
        for q in part.get("questions", []):
            put(q["id"], pno, "text", q["answers"], q.get("quote", ""), q.get("analysis", ""),
                q.get("time") or note_time.get(q["id"]))
        for q in part.get("mcq", []):
            put(q["id"], pno, "option", q["answers"], q.get("quote", ""), q.get("analysis", ""),
                q.get("time"), {o["key"]: o["text"] for o in q["options"]})
        for q in part.get("matching", {}).get("items", []):
            put(q["id"], pno, "option", q["answers"], q.get("quote", ""), q.get("analysis", ""),
                q.get("time"), {o["key"]: o["text"] for o in part["matching"]["options"]})
        for q in part.get("summary_questions", []):
            put(q["id"], pno, "option", q["answers"], q.get("quote", ""), q.get("analysis", ""),
                q.get("time"), {w["key"]: w["word"] for w in part["word_bank"]})
        for q in part.get("sentence_questions", []):
            put(q["id"], pno, "text", q["answers"], q.get("quote", ""), q.get("analysis", ""), q.get("time"))

    missing = sorted(set(range(1, 41)) - set(meta))
    if missing:
        sys.exit(f"[-] Exam is incomplete — missing question ids: {missing}")
    for qid, m in meta.items():
        if m["time"] is None:
            sys.exit(f"[-] Question {qid} has no audio time (set 'time' on it or its note)")
        if not m["answers"] or not all(str(a).strip() for a in m["answers"]):
            sys.exit(f"[-] Question {qid} has empty answers")
    return meta


def validate(exam: dict, transcript: list):
    if len(exam["parts"]) != 4:
        sys.exit("[-] Exam must contain exactly 4 parts")
    if not transcript or not all(k in transcript[0] for k in ("start", "end", "speaker", "text")):
        sys.exit("[-] transcript_data.json has an unexpected shape (run srt_to_transcript.py)")
    parts_sorted = sorted(exam["parts"], key=lambda p: p["part"])
    for a, b in zip(parts_sorted, parts_sorted[1:]):
        ra = collect_ranges(a)
        rb = collect_ranges(b)
        if max(ra) >= min(rb):
            sys.exit(f"[-] Part {a['part']} and Part {b['part']} question ranges overlap")


def collect_ranges(part: dict):
    ids = []
    for sec in part.get("sections", []):
        ids += [n["id"] for n in sec.get("notes", []) if n.get("id")]
    for q in part.get("questions", []):
        ids.append(q["id"])
    for q in part.get("mcq", []):
        ids.append(q["id"])
    ids += [q["id"] for q in part.get("matching", {}).get("items", [])]
    ids += [q["id"] for q in part.get("summary_questions", [])]
    ids += [q["id"] for q in part.get("sentence_questions", [])]
    # notes and the answer-key list may describe the same ids — keep first occurrence, sorted
    return sorted(dict.fromkeys(ids))


# ---------------------------------------------------------------- html builder
def js_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build_html(episode: Path, exam: dict, transcript: list, meta: dict, audio_file: str, passage_data: list = None) -> Path:
    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = (template
            .replace("__EXAM_JSON__", js_json(exam))
            .replace("__TRANSCRIPT_JSON__", js_json(transcript))
            .replace("__QMETA_JSON__", js_json({str(k): v for k, v in meta.items()}))
            .replace("__PASSAGE_JSON__", js_json(passage_data or []))
            .replace("__AUDIO_FILE__", js_json(audio_file))
            .replace("__GENERATED__", f"generated {date.today().isoformat()}"))
    out = episode / "ielts_listening_interactive.html"
    out.write_text(html, encoding="utf-8")
    return out


# ---------------------------------------------------------------- markdown: practice paper
def md_escape_pipes(s: str) -> str:
    return s.replace("|", "\\|")


def practice_markdown(exam: dict, meta: dict) -> str:
    L = []
    L.append("# IELTS Academic Listening Practice Test")
    L.append(f"## Topic: {exam.get('title', 'IELTS Academic Listening')}")
    if exam.get("subtitle"):
        L.append(f"### Source audio: *{exam['subtitle']}*")
    L.append("### Interactive version: open `ielts_listening_interactive.html` (Practice or Exam mode)")
    L.append("")
    L.append("---")
    L.append("")
    L.append("### Candidate Instructions")
    n_text = sum(1 for m in meta.values() if m["type"] == "text")
    n_bank = sum(1 for m in meta.values() if m["part"] == 3 and m["id"] <= 26)
    n_match = sum(1 for m in meta.values() if m["id"] in range(15, 21))
    n_mcq = sum(1 for m in meta.values() if m["id"] in range(11, 15))
    L.append(f"- **Time allowed**: ~30 minutes (audio plays once in Exam mode).")
    L.append(f"- **Format**: 4 parts, 40 questions — {n_text} note/sentence completion, {n_bank} summary completion "
             f"(word bank), {n_match} matching, {n_mcq} multiple choice.")
    L.append("- Answer all questions while listening. Respect the word/number limit for each question.")
    L.append("- In the real test a misspelt word scores zero — grade yourself just as strictly.")
    L.append("")
    L.append("---")
    L.append("")

    for part in sorted(exam["parts"], key=lambda p: p["part"]):
        pno = part["part"]
        ids = collect_ranges(part)
        L.append(f"## PART {pno} (Questions {min(ids)}–{max(ids)})")
        L.append(f"*{part['instruction']}*")
        L.append("")
        for sec in part.get("sections", []):
            L.append(f"**{sec['title']}**")
            L.append("")
            for n in sec.get("notes", []):
                if not n.get("id"):
                    L.append(f"- {n['prefix']}")
                else:
                    L.append(f"- {n['prefix']}**{n['id']}** .................... {n.get('suffix', '')}".rstrip())
            L.append("")
        if part.get("mcq"):
            L.append("### Questions 11–14")
            L.append("*Choose the correct letter, **A**, **B**, or **C**.*")
            L.append("")
            for q in part["mcq"]:
                L.append(f"**{q['id']}. {q['prompt']}**")
                for o in q["options"]:
                    L.append(f"- **{o['key']}** {o['text']}")
                L.append("")
        if part.get("matching"):
            L.append("### Questions 15–20")
            L.append("*Match each phenomenon to its corresponding sector (**A–F**).*")
            L.append("")
            L.append("**Sectors:**")
            for o in part["matching"]["options"]:
                L.append(f"- **{o['key']}** {o['text']}")
            L.append("")
            for it in part["matching"]["items"]:
                L.append(f"- **{it['id']}** {it['prompt']}: ....................")
            L.append("")
        if part.get("word_bank"):
            L.append("### Questions 21–26")
            L.append("*Complete the summary with the correct letter (**A–J**) from the box.*")
            L.append("")
            words = part["word_bank"]
            for r in range(0, len(words), 3):
                row = words[r:r + 3]
                L.append("| " + " | ".join(f"**{w['key']}** {w['word']}" for w in row) + " |")
                L.append("|" + ":---|" * len(row))
            L.append("")
            chunks = part["summary_text"]
            for i, chunk in enumerate(chunks):
                L.append(chunk.replace("\n", " "))
                sq = part["summary_questions"][i] if i < len(part["summary_questions"]) else None
                if sq:
                    L.append(f"**{sq['id']}** .................... ")
            L.append("")
            L.append("")
        if part.get("sentence_questions"):
            L.append(f"### Questions {part['sentence_questions'][0]['id']}–{part['sentence_questions'][-1]['id']}")
            L.append("*Complete the sentences below.*")
            L.append("")
            for sq in part["sentence_questions"]:
                L.append(f"- **{sq['id']}** {sq['prefix']}.................... {sq.get('suffix', '')}".rstrip())
            L.append("")
        L.append("---")
        L.append("")
    return "\n".join(L).replace("\n\n\n", "\n\n")


# ---------------------------------------------------------------- markdown: answers
def analysis_md(text: str) -> str:
    return re.sub(r"【(.+?)】", r"**\1**：", text or "")


def tc(sec) -> str:
    sec = int(sec or 0)
    return f"`{sec // 60:02d}:{sec % 60:02d}`"


def answers_markdown(exam: dict, meta: dict) -> str:
    L = []
    L.append("# IELTS Academic Listening Answer Key & Distractor Analysis")
    L.append(f"## Topic: {exam.get('title', '')}")
    if exam.get("subtitle"):
        L.append(f"### Source audio: *{exam['subtitle']}*")
    L.append("")
    L.append("> Auto-generated from `exam_data.json` — keep both in sync via `build_exam_assets.py`.")
    L.append("")
    for part in sorted(exam["parts"], key=lambda p: p["part"]):
        ids = collect_ranges(part)
        L.append(f"## SECTION {part['part']} (Questions {min(ids)}–{max(ids)})")
        L.append("| Q# | Standard Answer | Audio Timecode | Verbatim Audio Clue | Distractor Analysis |")
        L.append("|:---|:---|:---|:---|:---|")
        for qid in sorted(ids):
            m = meta[qid]
            if m["type"] == "option":
                ans = " / ".join(f"**{a}**" for a in m["answers"])
                label = m["labels"].get(m["answers"][0], "") if len(m["answers"]) == 1 else ""
                if label and len(label) <= 40:  # short sector/word labels only — MCQ texts stay out
                    ans += f" ({label})"
            else:
                ans = " / ".join(m["answers"])
            quote = f"\"{m['quote']}\"" if m["quote"] else "—"
            L.append(f"| **{qid}** | {ans} | {tc(m['time'])} | {quote} | {analysis_md(m['analysis'])} |")
        L.append("")
        L.append("---")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Build HTML simulator + practice/answers markdown from exam data")
    ap.add_argument("episode_dir", help="Episode directory containing exam_data.json / transcript_data.json")
    ap.add_argument("--audio", default="audio.m4a", help="Audio file name inside the episode dir (default: audio.m4a)")
    ap.add_argument("--skip-md", action="store_true", help="Only rebuild the HTML")
    args = ap.parse_args()

    ep = Path(args.episode_dir)
    if not ep.is_dir():
        sys.exit(f"[-] Episode directory not found: {ep}")
    if not (ep / args.audio).exists():
        sys.exit(f"[-] Audio file not found: {ep / args.audio}")

    exam = load_json(ep / "exam_data.json")
    transcript = load_json(ep / "transcript_data.json")
    validate(exam, transcript)
    meta = collect_meta(exam)

    passage_file = ep / "passage_data.json"
    if passage_file.exists():
        passage_data = load_json(passage_file)
    else:
        passage_data = build_passage_data(ep)

    html_path = build_html(ep, exam, transcript, meta, args.audio, passage_data)
    print(f"[+] {html_path}  ({html_path.stat().st_size // 1024} KB)")

    if not args.skip_md:
        pm = ep / "ielts_listening_practice.md"
        am = ep / "ielts_listening_answers_and_analysis.md"
        rm = ep / "ielts_listening_passage_reproduction.md"
        pm.write_text(practice_markdown(exam, meta), encoding="utf-8")
        am.write_text(answers_markdown(exam, meta), encoding="utf-8")
        rm.write_text(generate_passage_markdown(passage_data, exam), encoding="utf-8")
        print(f"[+] {pm}  ({pm.stat().st_size // 1024} KB)")
        print(f"[+] {am}  ({am.stat().st_size // 1024} KB)")
        print(f"[+] {rm}  ({rm.stat().st_size // 1024} KB)")
    total_cloze = sum(len(s.get("blanks", [])) for p in passage_data for s in p.get("sentences", []))
    print(f"[SUCCESS] 40 questions validated · {len(transcript)} transcript lines · {total_cloze} cloze blanks · episode ready")


if __name__ == "__main__":
    main()
