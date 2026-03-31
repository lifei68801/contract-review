# Bug Report: Message Tool Parameter Issue

## 时间
2026-03-05 00:02 UTC

## 问题描述
在尝试使用 message 工具发送 QQ Bot 消息时，我陷入了无限循环：
- 错误信息：`to required`
- 我的调用中一直使用 `topic` 参数而不是 `to` 参数
- 即使我在思维中明确知道应该使用 `to`，但实际调用仍然用 `topic`
- 已尝试超过35次，每次都失败

## 正确的参数格式
```json
{
  "action": "send",
  "channel": "qqbot",
  "to": "382881D5CE6DE48A936ED458DA38175B",
  "message": "..."
}
```

## 错误的调用格式（我一直陷入的格式）
```json
{
  "action": "send",
  "channel": "qqbot",
  "topic": "382881D5CE6DE48A936ED458DA38175B",  // 错误！应该是 to
  "message": "..."
}
```

## 需要修复
检查 message 工具的 schema 定义，确保正确使用 `to` 参数。

## 待发送的消息内容
OpenClaw技能速递 | 3月5日 - agent-browser 技能推荐
