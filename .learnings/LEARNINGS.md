# LEARNINGS.md - 学到的教训

---

## [LRN-20260309-001] crontab 中文注释问题

**Logged**: 2026-03-09T12:00:00Z
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
crontab 文件包含中文注释会导致任务不执行

### Details
定时任务不执行，`*/10 * * * *` 格式的任务被忽略。排查发现 crontab 文件包含 UTF-8 编码的中文注释，可能影响 crond 解析。

### Suggested Action
crontab 文件应避免包含非 ASCII 字符，即使注释行也应使用英文

### Metadata
- Source: error
- Tags: crontab, encoding
- Pattern-Key: crontab.ascii_only

### Resolution
- **Resolved**: 2026-03-09T12:30:00Z
- **Notes**: 重写 crontab 文件，全部使用 ASCII 注释

---

## [LRN-20260308-001] crontab 时区陷阱

**Logged**: 2026-03-08T10:00:00Z
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
系统时区是 Asia/Beijing，crontab 时间直接按本地时间解读

### Details
错误做法：在 Beijing 时区的系统上写 UTC 时间 `0 4 * * *` (实际变成凌晨4点执行)
正确做法：直接写北京时间 `0 12 * * *`

### Suggested Action
设置 crontab 前必须先 `timedatectl` 确认系统时区

### Metadata
- Source: error
- Tags: crontab, timezone
- Pattern-Key: crontab.timezone_check

### Resolution
- **Resolved**: 2026-03-08T10:30:00Z
- **Notes**: 设置任务前先检查系统时区

---

## [LRN-20260308-002] session 截断阈值问题

**Logged**: 2026-03-08T14:00:00Z
**Priority**: critical
**Status**: resolved
**Area**: infra

### Summary
截断脚本用行数限制会导致 context_window_exceeded

### Details
截断脚本用行数限制（2000行），但 session 文件每行内容巨大（最大单行 120KB），导致截断后文件仍然过大

### Suggested Action
改用文件大小限制（100KB）+ 单行大小限制（4000字符）

### Metadata
- Source: error
- Related Files: ~/.openclaw/workspace/skills/context-compression/scripts/truncate-sessions-safe.sh
- Tags: session, truncation, context
- Pattern-Key: session.size_limit

### Resolution
- **Resolved**: 2026-03-08T15:00:00Z
- **Notes**: 修改截断脚本，使用文件大小而非行数限制

---

## [LRN-20260309-002] cron delivery.to 限制

**Logged**: 2026-03-09T08:00:00Z
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
cron 配置的 delivery.to 只影响任务结果 announce，不影响子任务内部的 message 调用

### Details
小红书内容生成等任务的 QQ 发送失败，错误目标地址 `qqbot:c2c:1EB96E7CE9D733AF126AD522948151C3`
根因：cron 子任务内的消息发送需要显式指定目标地址

### Suggested Action
在每个任务的 payload 里明确指定 QQ 目标地址

### Metadata
- Source: error
- Tags: cron, qqbot, delivery
- Pattern-Key: cron.explicit_target

### Resolution
- **Resolved**: 2026-03-09T09:00:00Z
- **Notes**: 在任务 payload 中显式指定 `to: qqbot:c2c:382881D5CE6DE48A936ED458DA38175B`
