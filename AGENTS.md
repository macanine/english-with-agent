# AGENTS.md — 英语听力训练工作区

这个工作区把 Bilibili 英语播客/视频变成完整雅思听力训练材料。核心工作流由
skill `.agents/skills/bilibili-ielts-listening/` 驱动，完整说明见其 `SKILL.md`。

## 工作区结构

```
Agent-听说/
├── index.html                 # 雅思听力训练门户（主页导航）
├── README.md                  # 项目使用与架构说明
├── AGENTS.md                  # 本文件（Agent 指南）
├── Makefile                   # 常用命令入口（make help）
├── BV1AJe36fE9Q_Economist_Youth_Unemployment/          # 经济学人 · 青年失业
├── BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/     # English with Evie · 母语语速挑战
└── .agents/skills/bilibili-ielts-listening/
    ├── SKILL.md               # 流水线完整文档
    ├── assets/exam_simulator.html.template   # 模拟器模板（零依赖）
    └── scripts/               # bili_processor / srt_to_transcript / build_exam_assets
```

## 黄金法则：单一数据源

每个 episode 目录中：

- **`exam_data.json`** 是试题的唯一事实来源（可手编辑）。
- **`transcript_data.json`** 由 SRT 脚本生成（不可手编辑）。
- **`ielts_listening_interactive.html`、`ielts_listening_practice.md`、
  `ielts_listening_answers_and_analysis.md`** 全部由构建器生成。
  **永远不要手改这三个文件** — 改 JSON 后重建：

```bash
make build EP=<NAME>
```

构建器会校验 40 题完整性（编号、时间、答案、分区不重叠），数据有问题会拒绝构建。

## 常用命令

```bash
make help                          # 查看全部命令
make portal                        # 直接在浏览器打开主页 (index.html)
make serve                         # 本地 HTTP 服务预览 (http://127.0.0.1:8765)
make process URL=<BV链接> [NAME=<目录>] [TITLE=<标题>]   # 阶段1+2：下载/转写/字幕JSON
make build [EP=<NAME>]             # 阶段3：从 JSON 重建 HTML + 两个 MD（省略 EP 则重建全部）
make open [EP=<NAME>]              # 打开模拟器（省略 EP 则打开主页）
```

## 新增一集（agent 标准动作序列）

1. `make process URL=… NAME=BVxxxx_slug TITLE="…"` — 下载音频、whisper 转写、生成全句 SRT 与字幕 JSON。
2. 通读 `transcript_annotated.md`，按 SKILL.md 的命题规范写 `exam_data.json`
   （40 题、4 部分、约 75% 听写填空；每题带 verbatim 证据、秒级时间点、中文陷阱解析）。
3. `make build EP=…` — 构建三件产物；校验不过就按报错修 JSON。
4. 视觉 QA（headless Chrome 截图，参数与清单见 SKILL.md "QA hooks"）：
   至少覆盖 开始页 / part=1..4 / transcript / review / grade=1 / 430px 移动端，
   并确认音频条显示真实时长。

## 修改已有一集

- 调题、换词库、改答案变体 → 只改 `exam_data.json` → `make build`。
- 字幕有错 → 改 `transcript_full_sentence.srt` → `make process`（会跳过已完成的下载/转写）
  或直接重跑 `srt_to_transcript.py` → `make build`。
- 改 UI/交互 → 改 skill 里的 `assets/exam_simulator.html.template` → `make build`
  （模板变更会应用到所有 episode）。

## 约定

- 模拟器 HTML 必须保持**零外部依赖**（无 CDN/字体/框架），`file://` 离线可用。
- 命题语言：题面英文、解析中文（`【标签】`开头）；答案要收集拼写/冠词/数字写法变体。
- 词数限制指令必须与最长可接受答案一致。
- 产物中的时间戳一律是"音频内秒数"，由构建器格式化。
- 大文件（音频、whisper 输出）不入库，见 `.gitignore`。
