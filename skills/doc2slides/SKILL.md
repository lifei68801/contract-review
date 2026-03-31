---
name: doc2slides
version: 3.6.0
description: "Convert PDF, Word, and Markdown documents into professional PowerPoint slides with 18+ layout types and smart layout matching. Use when: user wants to create slides from a document or convert content to PPT."
license: MIT-0
author: lifei68801
metadata:
  openclaw:
    requires:
      bins: ["python3", "pip3"]
      env:
        optional:
          - OPENAI_API_KEY
          - ZHIPU_API_KEY
          - DEEPSEEK_API_KEY
    permissions:
      - "file:read"
      - "file:write"
    behavior:
      modifiesLocalFiles: true
      network: optional
      telemetry: none
      credentials: none
---

# Doc2Slides

Got a PDF or document? Need a presentation? One command, done.


> Input: any PDF / DOCX / Markdown
> Output: 6-page professional PPT in minutes
>
> Cover | Dashboard | Timeline | Comparison | Pyramid | Summary


## Quick Start

```bash
# Install the skill first
clawhub install doc2slides

# Then install Python dependencies
pip3 install python-pptx playwright requests && playwright install chromium

# Generate slides
cd ~/.openclaw/workspace/skills/doc2slides/scripts
python3 workflow.py --input document.pdf --output slides.pptx
```

That's it. PDF → PPT in minutes.

## What You Get

| Feature | Details |
|---------|---------|
| **Layouts** | 18+ types: Dashboard, Timeline, Flow Chart, Pyramid, Comparison, Matrix... |
| **Smart Matching** | Auto-picks the best layout per section |
| **Charts** | Built-in SVG charts — pie, bar, line, progress rings |
| **Resolution** | 3x high-def rendering |
| **LLM Mode** | Optional AI analysis for smarter layout choices |
| **Input** | PDF, DOCX, Markdown |
| **Offline** | Works without internet (template mode) |

## Usage Examples

```bash
# Basic — 5 slides from PDF
python3 workflow.py --input report.pdf --output report.pptx

# With page limit
python3 workflow.py --input report.pdf --output report.pptx --pages 3

# With custom instruction (style, focus, etc.)
python3 workflow.py --input report.pdf --output report.pptx --instruction "Focus on data and charts"

# Markdown input
python3 workflow.py --input notes.md --output notes.pptx
```

## When to Use This Skill

Activate when the user says anything like:
- "把这个文档做成PPT"
- "Convert this PDF to slides"
- "Generate a presentation from..."
- "帮我做个演示文稿"

**Before generating**, ask: *"有什么特殊要求吗？风格、页数、重点内容、配色？也可以说'按默认来'。"*

## How It Works

```
Document → Analyze → Match Layouts → Build HTML → Render (3x) → PPTX
```

No external CDN. No cloud service. Everything runs locally. HTML + inline CSS + SVG charts — fully self-contained.

## LLM Enhancement (Optional)

Set one of these env vars to enable AI-powered layout decisions:

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI / compatible |
| `ZHIPU_API_KEY` | Zhipu AI |
| `DEEPSEEK_API_KEY` | DeepSeek |

No API key? No problem — falls back to template mode with zero network calls.

## Architecture

| Script | Role |
|--------|------|
| `workflow.py` | Main orchestrator |
| `llm_generate_html.py` | AI slide generation |
| `llm_adapter.py` | Multi-provider adapter |
| `smart_layout_matcher.py` | Auto layout selection |
| `svg_charts.py` | Chart rendering |
| `html2png_batch.py` | Screenshot pipeline |
| `png2pptx.py` | Image → PPTX assembly |

All source code included. MIT-0 license.
