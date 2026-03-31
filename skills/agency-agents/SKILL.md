---
name: agency-agents
description: AI Agent 角色管理器。支持浏览、编辑、激活 156+ 个专业 AI Agent 角色，并提供 Web 管理界面。
version: 1.0.0
permissions:
  - read
  - write
  - exec
behavior:
  - Browsing and editing agent prompts
  - Activating agents by modifying SOUL.md
---

# Agency Agents Manager

管理 156+ 个专业 AI Agent 角色的 OpenClaw 技能。

## 命令

### /agency-serve
启动 Web 管理界面服务（端口 3456）。

```bash
cd ~/.openclaw/workspace/skills/agency-agents && node scripts/server.js
```

### /agency-list
列出所有 Agent（按分类统计）。

```bash
node ~/.openclaw/workspace/skills/agency-agents/scripts/scan-agents.js /tmp/agency-agents ~/.openclaw/workspace/skills/agency-agents/data
```

或直接查询 API：
```bash
curl http://localhost:3456/api/agents | python3 -m json.tool
```

### /agency-activate <slug>
激活指定 Agent（将其提示词写入 SOUL.md）。

```bash
node ~/.openclaw/workspace/skills/agency-agents/scripts/activate-agent.js <category/filename>
# 例如：
node ~/.openclaw/workspace/skills/agency-agents/scripts/activate-agent.js design/design-ui-designer
```

### /agency-deactivate
恢复默认 SOUL.md。

```bash
node ~/.openclaw/workspace/skills/agency-agents/scripts/activate-agent.js --restore
```

## API 端点

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/agents` | 所有 Agent 列表（支持 ?category= &search= &sort= 参数） |
| GET | `/api/agents/:slug` | 单个 Agent 详情 |
| GET | `/api/categories` | 分类列表 |
| PUT | `/api/agents/:slug` | 更新 Agent 内容 |
| POST | `/api/agents/:slug/activate` | 激活 Agent |
| POST | `/api/agents/deactivate` | 恢复默认 SOUL.md |
| GET | `/api/status` | 当前状态 |

## 文件结构

```
agency-agents/
├── SKILL.md              # 本文件
├── scripts/
│   ├── scan-agents.js    # 扫描 Agent 文件，生成索引
│   ├── server.js         # Web API 服务
│   └── activate-agent.js # Agent 激活/恢复脚本
├── web/
│   └── index.html        # 前端管理界面（单文件）
└── data/
    └── agents-index.json # Agent 索引（自动生成）
```

## 注意事项

- 首次使用前需要运行 `scan-agents.js` 生成索引
- 激活 Agent 会备份原始 SOUL.md 到 `SOUL.md.backup.default`
- 纯 Node.js 实现，无需任何外部依赖
