# 会话管理方案 v2 - 保留 10 轮 + 压缩历史

## 需求
1. 每次会话只保留最近 10 轮对话
2. 10 轮以外的上下文采用压缩输入
3. 完整会话记录保存到 session 文件

## 方案设计

### OpenClaw 内置机制

**配置：**
```json
{
  "agents": {
    "defaults": {
      "contextTokens": 100000,
      "compaction": {
        "mode": "default"  // 自动压缩，保留关键信息
      }
    }
  }
}
```

**工作原理：**
- OpenClaw 自动检测上下文超限
- 触发压缩时，使用模型生成摘要
- 原始会话文件（.jsonl）完整保留
- 压缩后的摘要替代历史消息

### 补充方案：会话摘要服务

由于 OpenClaw 不支持精确控制"保留 N 轮"，我们通过定时摘要来补充：

**每 6 小时执行：**
1. 检查会话消息数
2. 超过 20 轮时，生成摘要存入 `memory/sessions/`
3. 摘要包含：关键决策、用户偏好、待办事项

### 如何检索历史

**方式 1：语义检索**
```
memory_search query="之前讨论的定时任务"
```

**方式 2：查看完整历史**
```
sessions_history sessionKey="agent:main:qqbot:direct:xxx"
```

**方式 3：读取会话文件**
```
read path="~/.openclaw/agents/main/sessions/<id>.jsonl"
```

---

## 配置生效

已配置：
- ✅ contextTokens: 100000
- ✅ compaction.mode: default
- ✅ 会话摘要定时任务（每 6 小时）

---

## 监控

当前上下文：89K / 100K (89%)

当接近 100K 时，OpenClaw 会自动压缩历史消息。

---

## 完整会话保留

所有会话完整保存在：
```
~/.openclaw/agents/main/sessions/<session-id>.jsonl
```

这些文件不会被删除或修改，只是加载时会压缩。
