# ERRORS.md - 错误记录

---

*此文件用于记录命令失败、API 报错等错误信息*

格式参考：

```markdown
## [ERR-YYYYMMDD-XXX] skill_or_command_name

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
Brief description of what failed

### Error
\`\`\`
Actual error message or output
\`\`\`

### Context
- Command/operation attempted
- Input or parameters used

### Suggested Fix
If identifiable, what might resolve this

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
```
