#!/usr/bin/env python3
"""
Update a Notion page with Markdown content.
"""

import json
import time
import re
import sys

# Use urllib3 directly to avoid any issues
import urllib.request
import urllib.error

API_KEY = open("/root/.config/notion/api_key").read().strip()
PAGE_ID = "32df1f9c-b1ce-8157-939e-f1aedade410e"
NOTION_VERSION = "2025-09-03"
NEW_TITLE = "注意力不是你需要的：Grassmann 流，一种无注意力序列建模的几何替代方案"
MD_FILE = "/root/.openclaw/workspace/articles/grassmann-flows-v2.md"

BASE_URL = "https://api.notion.com/v1"


def notion_api(method, path, body=None, max_retries=5):
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    _method = method  # capture for error handling below

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 3
                try:
                    retry = e.headers.get("Retry-After")
                    if retry:
                        wait = int(retry) + 1
                except:
                    pass
                print(f"  429 rate limited, wait {wait}s (attempt {attempt+1})")
                time.sleep(wait)
                continue
            elif e.code == 400:
                # Silently ignore 400 for DELETE operations (likely already archived)
                if _method == "DELETE":
                    return {"archived": True}
                err_body = e.read().decode("utf-8", errors="replace")
                print(f"  400 error: {err_body[:200]}")
                return None
            else:
                err_body = e.read().decode("utf-8", errors="replace")
                print(f"  {e.code} error: {err_body[:200]}")
                return None
        except Exception as ex:
            print(f"  Request error: {ex} (attempt {attempt+1})")
            time.sleep(2)
            continue
    return None


def delete_all_blocks(page_id):
    print("Step 1: Deleting existing blocks...")
    total = 0
    empty_count = 0
    while True:
        result = notion_api("GET", f"/blocks/{page_id}/children?page_size=100")
        if not result or not result.get("results"):
            break
        blocks = result["results"]
        active = [b for b in blocks if not b.get("archived")]
        if not active:
            empty_count += 1
            if empty_count > 2:
                break
            # Try fetching again - sometimes archived blocks still appear
            time.sleep(0.5)
            continue
        empty_count = 0
        print(f"  Found {len(active)} active blocks, deleting...")
        for b in active:
            r = notion_api("DELETE", f"/blocks/{b['id']}")
            # Ignore 400 errors (already archived)
            if r or r is None:
                total += 1
        time.sleep(0.4)
    print(f"  Total deleted: {total}")


def update_title(page_id, title):
    print(f"Step 2: Updating title...")
    body = {
        "properties": {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        }
    }
    r = notion_api("PATCH", f"/pages/{page_id}", body)
    print(f"  Title updated: {r is not None}")


def rich_text(text):
    """Convert text with **bold** and *italic* to Notion rich_text."""
    parts = []
    i = 0
    buf = ""
    bold = False
    italic = False

    def flush():
        nonlocal buf
        if not buf:
            return
        ann = {}
        if bold:
            ann["bold"] = True
        if italic:
            ann["italic"] = True
        rt = {"type": "text", "text": {"content": buf}}
        if ann:
            rt["annotations"] = ann
        parts.append(rt)
        buf = ""

    while i < len(text):
        # Bold italic ***
        if text[i:i+3] == "***":
            flush()
            bold = not bold
            italic = not italic
            i += 3
            continue
        # Bold **
        if text[i:i+2] == "**":
            flush()
            bold = not bold
            i += 2
            continue
        # Italic * (only when at word boundary and not part of **)
        if text[i] == "*" and text[i:i+2] != "**" and text[i:i+3] != "***":
            # Check word boundary
            prev_ok = (i == 0 or text[i-1] in " \t\n(\"'")
            next_ok = (i+1 < len(text) and text[i+1] not in " \t\n*")
            if prev_ok or italic:  # closing italic doesn't need next boundary
                flush()
                italic = not italic
                i += 1
                continue
        buf += text[i]
        i += 1

    flush()

    if not parts:
        parts.append({"type": "text", "text": {"content": ""}})
    return parts


def parse_table(lines):
    """Parse markdown table lines into Notion table block."""
    if len(lines) < 2:
        return None
    header = [c.strip() for c in lines[0].split("|")[1:-1]]
    # Skip separator line (line[1])
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)

    ncols = len(header)
    if ncols == 0:
        return None

    children = []
    # Header row
    children.append({
        "object": "block",
        "type": "table_row",
        "table_row": {
            "cells": [[{"type": "text", "text": {"content": h}}] for h in header]
        }
    })
    # Data rows
    for row in rows:
        cells = []
        for j in range(ncols):
            txt = row[j] if j < len(row) else ""
            cells.append(rich_text(txt))
        children.append({
            "object": "block",
            "type": "table_row",
            "table_row": {"cells": cells}
        })

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": ncols,
            "has_column_header": True,
            "has_row_header": False,
            "children": children
        }
    }


def convert_md(md):
    """Convert markdown to list of Notion blocks."""
    blocks = []
    lines = md.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        s = line.strip()

        # Empty
        if not s:
            i += 1
            continue

        # Code block
        if s.startswith("```"):
            lang = s[3:].strip()
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1  # skip closing ```
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang if lang else "plain text"
                }
            })
            continue

        # Divider
        if s == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1
            continue

        # Headings
        if s.startswith("### ") and not s.startswith("#### "):
            blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text(s[4:])}})
            i += 1
            continue
        if s.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text(s[3:])}})
            i += 1
            continue
        if s.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text(s[2:])}})
            i += 1
            continue

        # Quote
        if s.startswith("> "):
            blocks.append({"object": "block", "type": "quote", "quote": {"rich_text": rich_text(s[2:])}})
            i += 1
            continue

        # Block math $$
        if s.startswith("$$"):
            math_lines = []
            first_line = s[2:]
            if first_line and not first_line.endswith("$$"):
                math_lines.append(first_line)
                i += 1
                while i < n:
                    ml = lines[i].strip()
                    if ml.endswith("$$"):
                        ml = ml[:-2]
                        if ml:
                            math_lines.append(ml)
                        i += 1
                        break
                    math_lines.append(ml)
                    i += 1
            elif first_line.endswith("$$"):
                ml = first_line[:-2]
                if ml:
                    math_lines.append(ml)
                i += 1
            else:
                i += 1

            for ml in math_lines:
                ml = ml.strip()
                if ml:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": ml}}]}
                    })
            continue

        # Table
        if s.startswith("|") and s.endswith("|"):
            tbl_lines = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                tbl_lines.append(lines[i].strip())
                i += 1
            tbl = parse_table(tbl_lines)
            if tbl:
                blocks.append(tbl)
            else:
                for tl in tbl_lines:
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(tl)}})
            continue

        # Numbered list
        nm = re.match(r"^(\d+)\.\s+(.*)", s)
        if nm:
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": rich_text(nm.group(2))}
            })
            i += 1
            continue

        # Bulleted list
        if s.startswith("- ") or s.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text(s[2:])}
            })
            i += 1
            continue

        # Regular paragraph (may span multiple lines)
        para = s
        i += 1
        while i < n:
            ns = lines[i].strip()
            if not ns:
                break
            if (ns.startswith("#") or ns.startswith("> ") or ns == "---" or
                ns.startswith("- ") or ns.startswith("* ") or ns.startswith("```") or
                ns.startswith("|") or ns.startswith("$$") or
                re.match(r"^\d+\.\s", ns)):
                break
            para += " " + ns
            i += 1
        blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text(para)}})

    return blocks


def flatten_blocks(blocks):
    """Flatten nested blocks (table children) into sequential blocks for Notion API.
    Notion API expects table children to be nested inside the table block.
    But when appending, we need to send them as a flat list with table having children.
    
    Actually, the Notion PATCH /children endpoint accepts blocks with nested children
    for table blocks. So we just return as-is.
    """
    # Count total top-level blocks
    return blocks


def add_blocks(page_id, blocks, batch_size=100):
    print(f"Step 3: Adding {len(blocks)} blocks...")
    total = 0
    for start in range(0, len(blocks), batch_size):
        batch = blocks[start:start+batch_size]
        body = {"children": batch}
        r = notion_api("PATCH", f"/blocks/{page_id}/children", body)
        if r:
            total += len(batch)
            batch_num = start // batch_size + 1
            total_batches = (len(blocks) + batch_size - 1) // batch_size
            print(f"  Batch {batch_num}/{total_batches}: +{len(batch)} blocks (total: {total})")
        else:
            print(f"  Retrying batch starting at {start} one by one...")
            for idx, b in enumerate(batch):
                r2 = notion_api("PATCH", f"/blocks/{page_id}/children", {"children": [b]})
                if r2:
                    total += 1
                else:
                    print(f"    Failed block {start + idx}: type={b.get('type', '?')}")
                time.sleep(0.35)
        time.sleep(0.4)
    return total


def main():
    with open(MD_FILE, "r", encoding="utf-8") as f:
        md = f.read()
    print(f"Read {len(md)} chars from {MD_FILE}")

    delete_all_blocks(PAGE_ID)
    time.sleep(1)

    update_title(PAGE_ID, NEW_TITLE)
    time.sleep(1)

    blocks = convert_md(md)
    print(f"\nConverted to {len(blocks)} blocks")

    total = add_blocks(PAGE_ID, blocks)
    print(f"\n✅ Done! Added {total}/{len(blocks)} blocks")


if __name__ == "__main__":
    main()
