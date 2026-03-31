#!/bin/bash
# 会话摘要生成脚本
# 每 6 小时执行，对活跃会话生成摘要

set -e

MEMORY_DIR="/root/.openclaw/workspace/memory/sessions"
SESSIONS_DIR="/root/.openclaw/agents/main/sessions"
MEMORY_FILE="/root/.openclaw/workspace/MEMORY.md"

mkdir -p "$MEMORY_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "===== 开始会话摘要生成 ====="

# 获取当前活跃会话
CURRENT_SESSION=$(cat ~/.openclaw/agents/main/sessions/sessions.json 2>/dev/null | \
  jq -r '."agent:main:qqbot:direct:382881d5ce6de48a936ed458da38175b".sessionId' 2>/dev/null)

if [ -z "$CURRENT_SESSION" ]; then
  log "未找到活跃会话"
  exit 0
fi

SESSION_FILE="$SESSIONS_DIR/${CURRENT_SESSION}.jsonl"

if [ ! -f "$SESSION_FILE" ]; then
  log "会话文件不存在: $SESSION_FILE"
  exit 0
fi

# 统计消息数量
MSG_COUNT=$(jq -s 'map(select(.type == "message")) | length' "$SESSION_FILE" 2>/dev/null || echo "0")

log "当前会话消息数: $MSG_COUNT"

# 如果消息数超过 20，生成摘要
if [ "$MSG_COUNT" -gt 20 ]; then
  SUMMARY_FILE="$MEMORY_DIR/qqbot-direct-$(date +%Y-%m-%d).md"

  # 提取关键用户消息
  USER_MSGS=$(jq -s 'map(select(.type == "message" and .message.role == "user")) |
    .[-20:] | .[] | .message.content[0].text' "$SESSION_FILE" 2>/dev/null | \
    grep -v "^Conversation info" | grep -v "^Sender" | grep -v "^你正在通过" | \
    grep -v "^【" | head -10)

  # 提取关键助手回复
  ASST_MSGS=$(jq -s 'map(select(.type == "message" and .message.role == "assistant")) |
    .[-20:] | .[] | .message.content[] | select(.type == "text") | .text' "$SESSION_FILE" 2>/dev/null | \
    head -10)

  # 生成摘要文件
  cat > "$SUMMARY_FILE" << EOF
# 会话摘要 - $(date +%Y-%m-%d)

## 会话信息
- Session ID: $CURRENT_SESSION
- 消息数: $MSG_COUNT
- 文件: $SESSION_FILE

## 用户关键输入
$(echo "$USER_MSGS" | head -5)

## 重要决策/任务
（需手动补充）

## 待办事项
（需手动补充）

---
*自动生成于 $(date '+%Y-%m-%d %H:%M:%S')*
EOF

  log "摘要已生成: $SUMMARY_FILE"
else
  log "消息数未超过阈值，跳过摘要生成"
fi

log "===== 完成 ====="
