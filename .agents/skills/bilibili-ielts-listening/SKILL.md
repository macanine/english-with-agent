---
name: bilibili-ielts-listening
description: >-
  Turns any English Bilibili video (BV id or URL) into a complete IELTS listening
  training kit: downloads the audio, transcribes locally with whisper.cpp (Apple
  Silicon Metal), reconstructs clean full-sentence speaker-attributed subtitles,
  authors a 40-question Cambridge-style exam as structured JSON, and builds a
  zero-dependency interactive "IELTS on Computer" simulator (practice + authentic
  exam mode, synced transcript, band scoring) plus printable exam/answer markdown.
  Use when the user gives a bilibili link/BV id for listening practice, asks for
  IELTS listening exercises from a video/podcast, or wants to rebuild/tweak an
  existing episode's exam or simulator.
---

# Bilibili IELTS Listening Pipeline

Convert one Bilibili English episode into a full IELTS listening training kit.
Three stages, one data contract:

```
Stage 1  bili_processor.py        Bilibili ──▶ audio.m4a / audio_16k.wav / whisper_raw.json
                                  ──▶ transcript_full_sentence.srt / transcript_annotated.md
Stage 2  srt_to_transcript.py     .srt ──▶ transcript_data.json          (deterministic)
         + agent authoring        ──▶ exam_data.json                      (the creative step)
Stage 3  build_exam_assets.py     JSON ──▶ ielts_listening_interactive.html
                                       + ielts_listening_practice.md
                                       + ielts_listening_answers_and_analysis.md
```

Every episode lives in `<NAME>/` with this **artifact contract**:

| File | Produced by | Hand-editable? |
|:---|:---|:---|
| `audio.m4a`, `audio_16k.wav`, `whisper_raw.json` | Stage 1 | no (regeneratable) |
| `transcript_full_sentence.srt`, `transcript_annotated.md` | Stage 1 | only for ASR fixes (then rerun Stage 2) |
| `transcript_data.json` | Stage 2 (script) | no |
| `exam_data.json` | Stage 2 (agent) | **yes — the single source of truth** |
| `ielts_listening_interactive.html`, `ielts_listening_practice.md`, `ielts_listening_answers_and_analysis.md` | Stage 3 (script) | **never — rebuild instead** |

Reference implementation: `BV1AJe36fE9Q_Economist_Youth_Unemployment/`.

## Stage 1 — Download, transcribe, merge sentences

```bash
python3 .agents/skills/bilibili-ielts-listening/scripts/run_pipeline.sh \
  "https://www.bilibili.com/video/BVxxxxxxxx/"  \
  "episodes/BVxxxxxxxx_<slug>" \
  "Episode Title"
```

Idempotent: existing outputs are skipped (`--force` to redo). Binaries are
resolved via `$PATH` with fallbacks; missing tools produce actionable errors.

## Stage 2 — Transcript JSON + exam authoring

**2a. Deterministic** — always run after any transcript change:

```bash
python3 .agents/skills/bilibili-ielts-listening/scripts/srt_to_transcript.py episodes/<NAME>
```

**2b. Agent authoring** — write `exam_data.json` (40 questions, 4 parts) after
listening/reading the transcript. Rules that make the exam Cambridge-grade:

- ~75% fill-in-the-blank dictation; parts 1/4 are note completion, part 2 is
  MCQ (Q11–14) + matching (Q15–20), part 3 is word-bank summary (Q21–26) +
  sentence completion (Q27–30).
- Every question needs: `answers` (accept all reasonable variants — spelling,
  articles, "more than 100"/"100+"), a verbatim `quote`, a `time` (seconds into
  the audio, used for clue replay), and a Chinese `analysis` starting with a
  `【标签】` (trap type, collocation, number trap …).
- `word limits` in `instruction` must match the longest accepted answer.
- Schema reference: copy the structure from the reference episode's
  `exam_data.json`; the builder validates (ids 1–40 complete, unique, timed,
  answerable, non-overlapping ranges) and refuses to build on errors.

## Stage 3 — Build the deliverables

```bash
python3 .agents/skills/bilibili-ielts-listening/scripts/build_exam_assets.py episodes/<NAME>
```

Regenerates the HTML simulator and both markdown files from the JSON in one
shot. Tweak exam → edit `exam_data.json` → rebuild. Never patch the HTML.

## The interactive simulator (built by Stage 3)

- **Zero dependencies** — no CDN, no Google Fonts, no Bootstrap; works fully
  offline from `file://`. Template:
  `assets/exam_simulator.html.template`; data injected at build time.
- **Practice Mode**: seek/±5s/speed/volume, synced karaoke transcript, per-part
  & per-question audio clue replay.
- **Exam Mode (完全模拟机考)**: official-style instructions screen, audio plays
  once (seek/rewind locked and enforced), transcript & clues hidden, 30:00
  countdown (amber <5min, red <1min) with auto-submit, review screen before
  submission, then band score + per-part breakdown + per-question feedback.
- Progress auto-saves to localStorage (versioned key `ielts_cdi_v7`); a saved
  attempt resumes from the start screen.

### QA hooks (used by agents for visual testing)

URL params — transient, never persisted to localStorage:

| Param | Effect |
|:---|:---|
| `skipstart=1` | skip the instructions overlay (practice mode) |
| `mode=exam` / `mode=practice` | start directly in that mode |
| `part=1..4`, `view=transcript`, `view=review` | jump to a view |
| `demo=1` | prefill answers (every 5th wrong) for visual QA |
| `grade=1` | grade immediately (implies demo) |

Visual check loop (headless Chrome, no extra tooling needed):

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1440,1400 \
  --virtual-time-budget=5000 --autoplay-policy=no-user-gesture-required \
  --screenshot=/tmp/sim.png "file://$PWD/episodes/<NAME>/ielts_listening_interactive.html?demo=1&grade=1"
```

Sweep at minimum: start screen, `part=1..4`, `view=transcript`, `view=review`,
`grade=1`, `grade=1&part=3`, plus a `430x932` mobile shot. Also sanity-check
that the audio bar shows the real duration (not `--:--`) — that proves the
audio src resolved.

## System requirements

- macOS (Apple Silicon recommended) · `afconvert` (built-in)
- `yt-dlp`, `whisper-cpp` (`brew install yt-dlp whisper-cpp`)
- Model `~/.cache/whisper.cpp/ggml-base.en.bin` (override with `--model`)
- Python 3.9+ (stdlib only — no pip dependencies anywhere in this skill)

## Troubleshooting

- **Audio won't play in the simulator** → the audio bar must show a real
  duration. If not, the audio file name differs: rerun Stage 3 with
  `--audio <file>`. Some browsers restrict `file://` media; use
  `make serve EP=episodes/<NAME>` and open the printed localhost URL.
- **yt-dlp throttled / 403** → retry later or update yt-dlp; bilibili rate-limits.
- **Transcript has wrong proper nouns** → fix the `.srt`, rerun Stage 2a + 3,
  or add a rule to `ACOUSTIC_CORRECTIONS` in `bili_processor.py`.
