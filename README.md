# 雅思听力全真模考研习中心 (IELTS on Computer Listening Hub)

> **基于 Bilibili 优质英语母语语料，本地自动化生成剑桥标准 40 题雅思机考模拟套卷、精听讲义与深度解析。**  
> 纯本地硬件加速（Apple Silicon Metal）· 零外部 CDN 依赖 · 即开即练 · 双阶递进导向。

---

## 快速开始 (Quickstart)

### 方式 1：双击或直接打开主页门户
双击打开项目根目录下的 [**`index.html`**](file:///Users/nic/Documents/英语/Agent-听说/index.html)，即可浏览所有可用真题套卷并一键进入机考模拟器：

```bash
make portal     # 自动调用系统默认浏览器打开主页门户
```

### 方式 2：本地 HTTP 服务预览
音频与交互最稳定的打开方式：

```bash
make serve      # 在 http://127.0.0.1:8765 启动本地工作区服务 (Ctrl-C 停止)
```

---

## 现已入库的精选真题 (Exam Library)

| 试卷编号 / 主题 | 语料来源 | 形式 / 时长 | 难度与题型 | 快捷入口 |
| :--- | :--- | :--- | :--- | :--- |
| **Test 01 · 青年失业与白领生态**<br>`BV1AJe36fE9Q` | 《经济学人》<br>*The Economist* | 双人深度研判<br>12:43 | **Band 7.5 – 8.5**<br>宏观经济、地产链条蒸发、零工算法反向竞价、假装上班族 | [机考模拟器](file:///Users/nic/Documents/英语/Agent-听说/BV1AJe36fE9Q_Economist_Youth_Unemployment/ielts_listening_interactive.html)<br>[真题试卷](file:///Users/nic/Documents/英语/Agent-听说/BV1AJe36fE9Q_Economist_Youth_Unemployment/ielts_listening_practice.md)<br>[原文复现](file:///Users/nic/Documents/英语/Agent-听说/BV1AJe36fE9Q_Economist_Youth_Unemployment/ielts_listening_passage_reproduction.md)<br>[答案解析](file:///Users/nic/Documents/英语/Agent-听说/BV1AJe36fE9Q_Economist_Youth_Unemployment/ielts_listening_answers_and_analysis.md)<br>[双语讲义](file:///Users/nic/Documents/英语/Agent-听说/BV1AJe36fE9Q_Economist_Youth_Unemployment/transcript_annotated.md) |
| **Test 02 · 母语语速与真人秀浸润**<br>`BV129KV6NEeG` | 英国博主 Evie<br>*English with Evie* | 原声狂飙独白<br>08:34 | **Band 7.0 – 8.0**<br>母语与非母语选词分水岭、英式冷幽默与 banter、群体听力骤降、习惯置换法 | [机考模拟器](file:///Users/nic/Documents/英语/Agent-听说/BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/ielts_listening_interactive.html)<br>[真题试卷](file:///Users/nic/Documents/英语/Agent-听说/BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/ielts_listening_practice.md)<br>[原文复现](file:///Users/nic/Documents/英语/Agent-听说/BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/ielts_listening_passage_reproduction.md)<br>[答案解析](file:///Users/nic/Documents/英语/Agent-听说/BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/ielts_listening_answers_and_analysis.md)<br>[整句讲义](file:///Users/nic/Documents/英语/Agent-听说/BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/transcript_annotated.md) |

---

## 工作区精简架构 (Directory Structure)

工作区已去除多余层级，所有套卷直平铺于根目录，架构清晰明了：

```text
Agent-听说/
├── index.html                                        # 雅思模考门户主页（双阶集成导航）
├── README.md                                         # 项目使用指南与架构说明（本文件）
├── AGENTS.md                                         # AI Agent 行为规范与 Golden Rules
├── Makefile                                          # 常用操作快捷入口 (make help)
│
├── BV1AJe36fE9Q_Economist_Youth_Unemployment/        # 试卷 1 目录
│   ├── audio.m4a                                     # 原声高码率音频 (gitignored)
│   ├── audio_16k.wav                                 # 16kHz mono WAV 识别音频 (gitignored)
│   ├── whisper_raw.json                              # Whisper 识别数据 (gitignored)
│   ├── transcript_full_sentence.srt                  # 毫秒对齐整句英文字幕
│   ├── transcript_annotated.md                       # 精编分章节精听讲义
│   ├── transcript_data.json                          # 字幕 JSON（由脚本生成）
│   ├── exam_data.json                                # 40 题核心事实源（Single Source of Truth）
│   ├── passage_data.json                             # 环节一原文复现听写数据源
│   ├── ielts_listening_interactive.html              # 雅思官方 CDI 标准交互模拟器
│   ├── ielts_listening_practice.md                   # 剑桥排版真题试卷
│   ├── ielts_listening_passage_reproduction.md       # 环节一原文精听复现与听写卷
│   └── ielts_listening_answers_and_analysis.md       # 官方答案键与深度干扰项剖析
│
├── BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40/  # 试卷 2 目录
│   └── ...                                           # 同上全套交付产物
│
└── .agents/skills/bilibili-ielts-listening/          # 驱动 Skill 引擎
    ├── SKILL.md                                      # 技能完整操作指南
    ├── assets/exam_simulator.html.template           # 零依赖原生模拟器模板
    └── scripts/
        ├── bili_processor.py                         # 音频下载、转换、Whisper 转写与整句重构
        ├── srt_to_transcript.py                      # 字幕转换为 transcript_data.json
        ├── build_passage_data.py                     # 原文精听复现数据生成
        └── build_exam_assets.py                      # 编译单源数据生成 HTML 与三份 Markdown
```

---

## 核心原则：单一数据源 (Single Source of Truth)

在每一个套卷目录中：

1. **`exam_data.json`** 是且仅是 40 题全真题目的唯一事实来源。
2. **`transcript_data.json`** 是整句字幕数据的唯一事实来源。
3. **`passage_data.json`** 是原文精听复现填空数据的唯一事实来源。
4. **`ielts_listening_interactive.html`、`ielts_listening_practice.md`、`ielts_listening_passage_reproduction.md`、`ielts_listening_answers_and_analysis.md`** 全部由构建器自动化编译生成。  
   切勿直接手工修改生成文件。若需微调题目，修改 JSON 后执行构建即可：

```bash
make build EP=BV129KV6NEeG_NativeFlow_English_With_Evie_Vol40
```

---

## 常用 Makefile 命令清单

| 命令 | 用途 |
| :--- | :--- |
| `make` / `make help` | 查看常用指令清单 |
| `make portal` | 用默认浏览器打开主页模考门户 (`index.html`) |
| `make serve` | 启动本地静态服务器 (`http://127.0.0.1:8765`) |
| `make build [EP=<dir>]` | 重新校验并编译套卷（**若省略 EP 则自动重建全部套卷**） |
| `make open [EP=<dir>]` | 在浏览器打开指定套卷模拟器（若省略 EP 则打开主页） |
| `make process URL=<url> [NAME=<dir>] [TITLE="<title>"]` | 阶段 1+2：下载 B 站音频、Whisper 转写、切分整句与生成字幕 JSON |

---

## 双阶训练体系与命题设计原则

针对中国考生听力实战痛点，系统提供双阶梯训练流程：

1. **环节一：整段原文精听复现 (Stage 1: Passage Reproduction & Shadowing)**：
   - 解决“语速过快、连读吞音听不清”的入门障碍。
   - 连续段落整段听写，抓取地道习语、动词短语与高频搭配。
   - 支持单句反复点击播放与影子跟读（Shadowing），打通语流听觉感知。
2. **环节二：雅思全真40题模考 (Stage 2: Official Cambridge IELTS Exam)**：
   - 约 75% 高密度填空听写（Part 1 笔记填空、Part 2 单选与配对、Part 3 总结填空与细节听写、Part 4 学术讲座笔记填空）。
   - 真实原声证据（Verbatim Evidence）：每题标有精确秒级时间戳与录音例句引用。
   - 深度干扰项剖析（Distractor Analysis）：以中文标签（如 `【限定修饰词】`、`【同义置换陷阱】`）深入剖析出题逻辑。
   - 官方 Band 9 诊断评分：练习模式与30分钟机考模式双轨运行。
