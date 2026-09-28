#!/usr/bin/env python3
"""Build passage cloze reproduction data (passage_data.json) for an episode.
This provides Stage 1: Full-Text Verbatim Cloze & Passage Dictation training.
"""

import json
import re
import sys
from pathlib import Path

# High-value cloze dictionaries for known episodes
CLOZE_TARGETS_MAP = {
    "BV129KV6NEeG": [
        'native speed', 'listening comprehension', '100,000 subscriber special', 'mix it up',
        'eight minutes', '100,000 subscribers', '1,000 away', '100k', 'four months',
        'exact beach', 'first vlog', 'voice was shaking', 'retaking the video',
        'relaxed', 'advanced English learner', 'future of this channel',
        'basically fluent', 'change my language', 'completely different',
        'words that I choose', 'heavy slang', 'colloquialisms', 'sarcasm',
        'shut up', 'banter', 'very sarcastic', 'very dry', 'take the piss out of each other',
        'moved abroad', 'one on one', 'big social event', 'comprehension drops',
        'lack of cultural understanding', 'intonation', 'reality TV', 'dating shows',
        'small-talky, getting-to-know-each-other context', 'no subtitles', 'comedies',
        'cultural understanding', 'educational', 'supermarket', 'part of your life',
        'replacing all of your habits', 'habits in English', 'through the roof',
        'immersed', 'immersion', 'lifestyle content', 'vocabulary builds',
        'accessible', 'one video a week', 'pull them off', 'quick growth in four months',
        'better than the last'
    ],
    "BV1AJe36fE9Q": [
        'tough time', 'way of life', 'guaranteed ticket', 'roadmap', 'vanished',
        'car-parts maker', 'hiring spree', '140 fresh graduates', 'ultimatum',
        "half a month's salary", 'severance', 'screwdriver', 'manual labor', 'factory floor',
        'more than 100', 'tiny payout', 'outpouring of outrage', "trampling on society's trust",
        'unwritten social contract', 'Volkswagen', 'head of human resources', 'top executives',
        '12.7 million', 'double', 'plummeted', 'property market', 'flagging consumption',
        'tightening their belts', 'white-collar ecosystem', 'architects', 'civil engineers',
        'urban planners', 'mortgages', 'domino effect', 'hiring freeze',
        'artificial intelligence', 'digital avatars', 'grunt work', 'quietly laying off',
        'stock prices', 'gig economy', 'overstuffed', 'auction that punishes the worker',
        'full-time children', 'monthly allowance', 'housekeeper',
        'Pretend-to-Work Company', 'water cooler', 'societal illusion',
        'Capital Library', 'polishing their CVs', 'computer games', 'voluntary break',
        'sanity', 'agency', 'office chair', 'symbol', 'redefine', 'completely new one'
    ]
}


def make_hint(text: str) -> str:
    """Turn 'native speed' into 'n____ s____'."""
    words = text.split()
    hints = []
    for w in words:
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', w)
        if len(cleaned) <= 1:
            hints.append(w)
        else:
            hints.append(cleaned[0] + "_" * (len(cleaned) - 1))
    return " ".join(hints)


def mark_targets_in_text(text: str, targets: list) -> str:
    """Mark non-overlapping target occurrences with <<<...>>>."""
    marked = text
    for tgt in targets:
        pattern = re.compile(r'\b(' + re.escape(tgt) + r')\b', re.IGNORECASE)
        # Split by existing <<<...>>> to only match in unmarked segments
        parts = re.split(r'(<<<.+?>>>)', marked)
        for i in range(0, len(parts), 2):
            parts[i] = pattern.sub(r'<<<\1>>>', parts[i])
        marked = ''.join(parts)
    return marked


def build_passage_data(episode_dir: Path):
    t_path = episode_dir / "transcript_data.json"
    if not t_path.exists():
        sys.exit(f"[-] Missing transcript: {t_path}")
    transcript = json.loads(t_path.read_text(encoding="utf-8"))

    e_path = episode_dir / "exam_data.json"
    exam = json.loads(e_path.read_text(encoding="utf-8")) if e_path.exists() else {}

    # Match target words
    ep_name = episode_dir.name
    curated = []
    for k, v in CLOZE_TARGETS_MAP.items():
        if k in ep_name:
            curated = v
            break

    # If no curated list, extract from exam_data.json
    if not curated and exam:
        for p in exam.get("parts", []):
            for q in p.get("questions", []):
                curated.extend([a.strip() for a in q.get("answers", []) if len(a.strip()) > 3])
            for sq in p.get("sentence_questions", []):
                curated.extend([a.strip() for a in sq.get("answers", []) if len(a.strip()) > 3])

    # Sort targets by length descending so longer phrases match first
    curated = sorted(list(set(curated)), key=lambda x: -len(x))

    # Divide transcript into 4 parts based on exam or evenly
    n_sents = len(transcript)
    if "BV129KV6NEeG" in ep_name:
        splits = [0, 17, 28, 41, n_sents]
    elif "BV1AJe36fE9Q" in ep_name:
        splits = [0, 67, 107, 157, n_sents]
    else:
        q = n_sents // 4
        splits = [0, q, q * 2, q * 3, n_sents]

    part_titles = [
        exam.get("parts", [{}])[i].get("title", f"Part {i+1}")
        if i < len(exam.get("parts", [])) else f"Part {i+1}"
        for i in range(4)
    ]

    parts_data = []
    blank_counter = 1

    for p_idx in range(4):
        s_start, s_end = splits[p_idx], splits[p_idx + 1]
        p_sents = transcript[s_start:s_end]
        if not p_sents:
            continue

        part_item = {
            "part": p_idx + 1,
            "title": part_titles[p_idx],
            "audio_start": p_sents[0]["start"],
            "audio_end": p_sents[-1]["end"],
            "sentences": []
        }

        for s in p_sents:
            raw_text = s["text"]
            marked_text = mark_targets_in_text(raw_text, curated)

            s_blanks = []
            def repl(match):
                nonlocal blank_counter
                ans = match.group(1)
                bid = blank_counter
                blank_counter += 1
                s_blanks.append({
                    "id": bid,
                    "answer": ans,
                    "hint": make_hint(ans)
                })
                return f"[[{ans}]]"

            cloze_text = re.sub(r'<<<(.+?)>>>', repl, marked_text)

            part_item["sentences"].append({
                "id": s["id"],
                "start": s["start"],
                "end": s["end"],
                "speaker": s["speaker"],
                "text": raw_text,
                "cloze_text": cloze_text,
                "blanks": s_blanks
            })

        parts_data.append(part_item)

    out_file = episode_dir / "passage_data.json"
    out_file.write_text(json.dumps(parts_data, ensure_ascii=False, indent=2), encoding="utf-8")
    total_blanks = blank_counter - 1
    print(f"[+] Wrote {len(parts_data)} parts with {total_blanks} cloze blanks -> {out_file}")
    return parts_data


def generate_passage_markdown(passage_data: list, exam_info: dict) -> str:
    """Generate printable markdown worksheet for Stage 1 passage cloze reproduction."""
    lines = []
    title = exam_info.get("title", "IELTS Academic Listening")
    subtitle = exam_info.get("subtitle", "")
    lines.append("# IELTS 听力训练 · 环节一：整段原文精听复现与听写卷")
    lines.append(f"## 主题：{title}")
    if subtitle:
        lines.append(f"### 音频来源：*{subtitle}*")
    lines.append("")
    lines.append("> 本卷专为突破高语速与连读弱读设计。在进行雅思40题模考前，请先通听各段完成整段填空，并针对难句进行影子跟读（Shadowing）。")
    lines.append("")
    lines.append("---")
    lines.append("")

    for p in passage_data:
        pno = p["part"]
        start_min, start_sec = int(p["audio_start"] // 60), int(p["audio_start"] % 60)
        end_min, end_sec = int(p["audio_end"] // 60), int(p["audio_end"] % 60)
        time_str = f"{start_min:02d}:{start_sec:02d} – {end_min:02d}:{end_sec:02d}"

        part_blanks = []
        for s in p["sentences"]:
            part_blanks.extend(s["blanks"])

        b_min = part_blanks[0]["id"] if part_blanks else 0
        b_max = part_blanks[-1]["id"] if part_blanks else 0

        lines.append(f"## PART {pno}: {p['title']} (Audio: {time_str})")
        lines.append(f"*填空题号：第 {b_min} – {b_max} 题 · 边听边补全下方段落中的划线缺失词汇/短语*")
        lines.append("")
        lines.append("### 【段落填空练习】")
        lines.append("")

        # Group sentences by speaker paragraphs
        current_speaker = None
        para_sentences = []

        def flush_para():
            if not para_sentences:
                return
            spk_label = f"**[{current_speaker}]** " if current_speaker else ""
            para_text = " ".join(para_sentences)
            lines.append(f"{spk_label}{para_text}")
            lines.append("")

        for s in p["sentences"]:
            if s["speaker"] != current_speaker:
                flush_para()
                current_speaker = s["speaker"]
                para_sentences = []

            # Format cloze text with numbered blanks
            # Replace [[ans]] with (N) ________ [hint]
            s_text = s["cloze_text"]
            for b in s["blanks"]:
                s_text = s_text.replace(f"[[{b['answer']}]]", f"**({b['id']})** ________ *[{b['hint']}]*", 1)
            para_sentences.append(s_text)

        flush_para()

        # Part Answer Key Table
        lines.append("### 【答案与句意对照】")
        lines.append("| 题号 | 标准答案 | 出现时间 | 原文例句 |")
        lines.append("|:---|:---|:---|:---|")
        for s in p["sentences"]:
            for b in s["blanks"]:
                s_time = f"`{int(s['start']//60):02d}:{int(s['start']%60):02d}–{int(s['end']//60):02d}:{int(s['end']%60):02d}`"
                quote = s["text"].replace("|", "\\|")
                lines.append(f"| **{b['id']}** | **{b['answer']}** | {s_time} | \"{quote}\" |")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 build_passage_data.py <episode_dir>")
    build_passage_data(Path(sys.argv[1]))
