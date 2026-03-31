# 会话压缩方案（保留记忆）

## 问题分析

**根本原因：**
1. 每条消息包含重复的系统提示（Conversation info、QQ 提示等）
2. 历史消息累积导致上下文超限
3. 删除会话会丢失记忆

**当前配置：**
```json
"compaction": {
  "mode": "safeguard"  // 仅在必要时压缩
}
```

---

## 解决方案

### 1. 启用自动压缩

**配置 OpenClaw compaction：**
```json
"agents": {
  "defaults": {
    "compaction": {
      "mode": "auto",           // 自动压缩
      "threshold": 0.7,         // 70% 时触发
      "preserveRecent": 10      // 保留最近 10 轮对话
    },
    "contextTokens": 150000     // 限制上下文窗口
  }
}
```

### 2. 会话摘要机制

**当会话过长时（每 20 轮对话）：**
1. 生成会话摘要
2. 存入 `memory/sessions/<sessionKey>.md`
3. 原始会话保留，但只加载摘要

**摘要结构：**
```markdown
# 会话摘要 - YYYY-MM-DD

## 关键决策
- [决策1]
- [决策2]

## 重要信息
- 用户偏好：xxx
- 任务结果：xxx

## 待办事项
- [ ] 待完成任务

## 相关会话
- 完整记录：`~/.openclaw/agents/main/sessions/<id>.jsonl`
```

### 3. 分层记忆架构

```
┌─────────────────────────────────────┐
│   当前上下文（活跃会话）              │
│   - 最近 10 轮对话                   │
│   - 约 20K tokens                   │
├─────────────────────────────────────┤
│   会话摘要（compressed sessions）    │
│   - memory/sessions/*.md            │
│   - 按需检索                         │
├─────────────────────────────────────┤
│   长期记忆（MEMORY.md）              │
│   - 用户偏好、重要决策               │
│   - 每次会话更新                     │
└─────────────────────────────────────┘
```

### 4. 按需检索

**当需要历史信息时：**
1. 使用 `memory_search` 检索相关摘要
2. 使用 `sessions_history` 查看完整历史
3. 按需加载关键上下文

---

## 定时任务

### 会话摘要任务（每 6 小时）

**任务内容：**
1. 扫描活跃会话
2. 对超过 20 轮的会话生成摘要
3. 存入 `memory/sessions/<key>.md`
4. 更新 `MEMORY.md` 的关键信息

### 执行时间
- 00:00、06:00、12:00、18:00

---

## 配置修改

### 步骤 1：更新 compaction 配置

```bash
openclaw config set agents.defaults.compaction.mode "auto"
openclaw config set agents.defaults.compaction.threshold 0.7
openclaw config set agents.defaults.contextTokens 150000
```

### 步骤 2：创建会话摘要 cron 任务

---

## 监控指标

- 上下文使用率 < 70%
- 会话摘要覆盖率 > 80%
- 关键信息保留率 = 100%

---

## 生效时间

2026-03-06 创建
