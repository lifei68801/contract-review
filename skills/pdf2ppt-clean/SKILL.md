---
name: pdf2ppt-clean
version: 1.0.0
description: "Convert PDF to PowerPoint using local processing. No external API calls."
license: MIT-0
author: lifei68801
tags: [pdf, ppt, local]
---

# PDF to PowerPoint Converter

Convert PDF documents to PowerPoint format using local processing only.

## Quick Start

```bash
python scripts/main.py input.pdf output_dir
```

## Features

- **Local Processing**: No API calls, no network requests
- **Smart Formatting**: Auto-detect headers and sections
- **Clean Output**: Properly formatted slides

## Requirements

```bash
pip install pdfplumber
```

## Usage

```bash
# Basic usage
python scripts/main.py document.pdf

# Specify output directory
python scripts/main.py document.pdf ./slides
```

## How It Works

1. Extracts text from PDF using pdfplumber
2. Cleans up formatting issues
3. Detects headers and sections
4. Outputs clean slides

## Metadata

```yaml
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      pypi: ["pdfplumber"]
    permissions:
      - "file:read"
      - "file:write"
    behavior:
      network: none
      telemetry: none
      description: "Converts PDF to PowerPoint using local pdfplumber. No network requests."
```
