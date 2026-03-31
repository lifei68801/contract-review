---
name: slide-maker
version: 1.0.0
description: "Convert documents to PowerPoint using local processing. No external API calls."
license: MIT-0
author: lifei68801
tags: [ppt, document, local]
---

# Slide Maker

Convert PDF, Word, Markdown documents to PowerPoint format using local processing only.

## Quick Start

```bash
python scripts/main.py input.pdf output_dir
```

## Features

- **Local Processing**: No API calls, no network requests
- **Multiple Formats**: PDF, Word, Markdown
- **Clean Output**: Professional slide design

## Requirements

```bash
pip install playwright python-pptx pdfplumber python-docx
```

## Metadata

```yaml
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      pypi: ["playwright", "python-pptx", "pdfplumber", "python-docx"]
    permissions:
      - "file:read"
      - "file:write"
    behavior:
      network: none
      telemetry: none
      description: "Converts documents to PowerPoint using local processing. No network requests."
