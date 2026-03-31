---
name: doc-to-ppt
version: 1.2.2
description: "Convert documents to PPT. Uses Playwright for rendering. All processing is local."
license: MIT-0
author: lifei68801
tags: [ppt, pdf, document, conversion]
---

# Doc-to-PPT

Convert documents to PowerPoint presentations.

## Quick Start

```bash
python scripts/main.py input.pdf --output ./output
```

## Security

- **Local Processing Only**: No external API calls, no data leaves your machine
- **No Telemetry**: No usage tracking or analytics
- **No Credentials**: Does not read or store any credentials
- **Sandboxed Rendering**: Uses Playwright in isolated mode

## Requirements

```bash
pip install playwright python-pptx pdfplumber python-docx
playwright install chromium
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
      - "process:spawn"
    behavior:
      network: none
      telemetry: none
      credentials: none
      subprocess: isolated
```
