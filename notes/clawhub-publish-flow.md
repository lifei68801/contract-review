# ClawHub 技能发布流程

## 正常流程（CLI 可用时）

```bash
# 1. 登录
clawhub login

# 2. 发布（自动同意条款）
clawhub publish --accept-license-terms

# 3. 等待审核通过
```

## 备用流程（CLI 有 bug 时用 curl）

当 CLI 的 `--accept-license-terms` 参数不生效时：

```bash
# 1. 先用 CLI 创建版本（会失败，但能创建 versionId）
clawhub publish --accept-license-terms

# 2. 用 curl 直接调 API 确认发布
curl -X POST "https://clawhub.com/api/skills/{skillName}/versions/{versionId}/publish" \
  -H "Authorization: Bearer $(cat ~/.config/clawhub/auth.json | jq -r '.token')" \
  -H "Content-Type: application/json"
```

## 已知问题

- CLI 的 `--accept-license-terms` 参数有时不生效
- 需要用 curl 直接调 API 的 `/publish` 端点

## 最近发布记录

- **context-compression@3.6.3** (2026-03-10)
  - versionId: k9795gq0h6qnzafyvqncffy31s82nwhs
  - 用 curl 绕过 CLI bug
