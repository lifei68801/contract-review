---
name: doc-to-ppt-minimal
version: 1.0.0
description: "Simple document to PPT conversion. No external dependencies beyond Python libraries."
license: MIT-0
author: lifei68801
tags: [ppt, pdf, document]
---

# Doc-to-PPT Minimal

Convert documents to PowerPoint with minimal footprint.

## Quick Start

```bash
python scripts/convert.py input.pdf ./output
```

## Features

- PDF, Markdown, Word support
- Local processing only
- No network calls

## Requirements

```bash
pip install python-pptx pdfplumber python-docx
```

## Metadata

```yaml
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      pypi: ["python-pptx", "pdfplumber", "python-docx"]
    permissions:
      - "file:read"
      - "file:write"
    behavior:
      network: none
      telemetry: none
      credentials: none
```
