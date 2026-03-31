# TOOLS.md - Tool Configuration & Notes

> Document tool-specific configurations, gotchas, and credentials here.

---

## Credentials Location

All credentials stored in `.credentials/` (gitignored):
- `example-api.txt` — Example API key

---

## [Tool Name]

**Status:** ✅ Working | ⚠️ Issues | ❌ Not configured

**Configuration:**
```
Key details about how this tool is configured
```

**Gotchas:**
- Things that don't work as expected
- Workarounds discovered

**Common Operations:**
```bash
# Example command
tool-name --common-flag
```

---

## ClawHub CLI

**Status:** ⚠️ Issues with v0.7.0

**Configuration:**
- Config: `~/.config/clawhub/config.json`
- Token: `clh_g3xV8yPJ-...` (lifei68801 account)
- Registry: `https://clawhub.ai/api` (changed from `api.clawhub.ai`)

**Gotchas:**
1. **CLI v0.7.0 bug**: `acceptLicenseTerms` field not sent, causing publish to fail
2. **API URL change**: Old `api.clawhub.ai` no longer resolves, use `clawhub.ai/api`
3. **Security scanner**: SKILL.md must declare `metadata.permissions` and `metadata.behavior`

**Workaround for publish:**
```bash
# Direct API call with acceptLicenseTerms
payload='{"slug":"skill-name","displayName":"Skill Name","version":"1.0.0","changelog":"...","tags":["latest"],"acceptLicenseTerms":true}'
curl -X POST "https://clawhub.ai/api/v1/skills" \
  -H "Authorization: Bearer $TOKEN" \
  -F "payload=$payload" \
  -F "files=@SKILL.md"
```

**Common Operations:**
```bash
# Check skill status
curl -s "https://clawhub.ai/api/v1/skills/<slug>" -H "Authorization: Bearer $TOKEN"

# Check whoami
curl -s "https://clawhub.ai/api/v1/whoami" -H "Authorization: Bearer $TOKEN"
```

---

## Web Search Plus

**Status:** ✅ Working (Serper)
**Config:** `~/.openclaw/workspace/skills/web-search-plus/config.json`
**Key:** SERPER_API_KEY in `.env`
**Free tier:** 2500 searches/month
**Usage:** `python3 scripts/search.py -q "query"`
**Auto-routing:** enabled, fallback=serper
**Note:** 这个技能没出现在 available_skills 列表里，需要手动调用脚本

---

## 写作规范

**内容生成工具**: 所有写内容、写文章、生成文案的任务，必须使用 autowriter 技能，不要自己直接写
**微信文章**: 必须参考 `微信公众号写作指南.md`（旧版 `技术文章撰写风格指南.md` 已备份）
**去AI味**: 写任何文章、内容、或输出文本时，必须使用 humanizer 技能去除 AI 生成痕迹
**核心原则**: 有观点、有情绪、有立场，拒绝千篇一律

## 搜索规范

**首选搜索**: web-search-plus（`skills/web-search-plus/`），Serper + Tavily 双引擎
**备选搜索**: agent-browser（`skills/agent-browser/`），仅在 web-search-plus 无结果时使用
**优先级**: web-search-plus > agent-browser > web_search
**web-search-plus 用法**: `cd ~/.openclaw/workspace/skills/web-search-plus && python3 scripts/search.py -q "query"`

## 技能创建与优化规范

**skill-creator**: 当需要创建新技能、优化现有技能、或审查技能质量时，激活 skill-creator 技能（内置，无需安装）

## 技能安装规范

**安装后扫描**: 每次通过 ClawHub 安装新技能后，必须使用 skill-vetter 扫描安全性和质量
**流程**: `clawhub install <slug>` → `skill-vetter scan <技能目录>`

---

## What Goes Here

- Tool configurations and settings
- Credential locations (not the credentials themselves!)
- Gotchas and workarounds discovered
- Common commands and patterns
- Integration notes

## Why Separate?

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

---

*Add whatever helps you do your job. This is your cheat sheet.*
