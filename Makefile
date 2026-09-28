# English Listening Workspace — command entry points (make help)
SKILL := .agents/skills/bilibili-ielts-listening/scripts

.PHONY: all help portal serve build open process

all: help

help:
	@echo "=========================================================="
	@echo " IELTS on Computer · Listening Practice Workspace"
	@echo "=========================================================="
	@echo "  make portal              打开真题集主页 (index.html)"
	@echo "  make serve               启动本地服务预览 (http://127.0.0.1:8765)"
	@echo "  make build [EP=<dir>]    重新编译套卷 (若省略 EP 则自动重建全部)"
	@echo "  make open [EP=<dir>]     在浏览器打开指定套卷 (若省略 EP 则打开主页)"
	@echo "  make process URL=<url> [NAME=<dir>] [TITLE=\"...\"]"
	@echo "                           阶段1+2：下载/转写/字幕对齐"
	@echo "=========================================================="

portal:
	open index.html

serve:
	@echo "Serving IELTS Listening Hub at http://127.0.0.1:8765/ (Ctrl-C to stop)"
	python3 -m http.server 8765

build:
	@if [ -n "$(EP)" ]; then \
		echo "==> Building episode: $(EP)"; \
		python3 "$(SKILL)/build_exam_assets.py" "$(EP)"; \
	else \
		echo "==> Building all episodes in workspace..."; \
		count=0; \
		for d in BV*/; do \
			if [ -f "$$d/exam_data.json" ]; then \
				echo "==> Building $$d"; \
				python3 "$(SKILL)/build_exam_assets.py" "$$d"; \
				count=$$((count + 1)); \
			fi; \
		done; \
		echo "[SUCCESS] Rebuilt $$count episode(s)"; \
	fi

open:
	@if [ -n "$(EP)" ]; then \
		open "$(EP)/ielts_listening_interactive.html"; \
	else \
		open index.html; \
	fi

process:
	@test -n "$(URL)" || { echo "usage: make process URL=<bilibili_url_or_bvid> [NAME=<dir>] [TITLE=...]"; exit 1; }
	@dir="$(NAME)"; \
	if [ -z "$$dir" ]; then \
		dir=$$(echo "$(URL)" | grep -o 'BV[a-zA-Z0-9]\+'); \
	fi; \
	echo "==> Target directory: $$dir"; \
	python3 "$(SKILL)/bili_processor.py" "$(URL)" --outdir "$$dir" --title "$(TITLE)" && \
	python3 "$(SKILL)/srt_to_transcript.py" "$$dir" && \
	echo "" && \
	echo "Next: author $$dir/exam_data.json, then run: make build EP=$$dir"
