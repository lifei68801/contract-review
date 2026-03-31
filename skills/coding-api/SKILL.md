# CODING API 技能

对接 CODING 项目协同 API，实现需求管理、Bug 管理、迭代管理等功能的自动化。

## 能力范围

### 已支持功能

- [x] 查询事项列表（需求/Bug/任务）
- [x] 创建事项（需求/Bug/任务）
- [x] 修改事项状态
- [x] 查询事项详情
- [x] 创建迭代
- [x] 查询迭代列表
- [x] 触发构建
- [x] 创建合并请求

### 触发方式

用户发送包含以下关键词的消息时，自动调用 CODING API：

| 关键词 | 功能 |
|-------|------|
| `查询需求`、`查看需求` | 查询项目需求列表 |
| `查询Bug`、`查看缺陷` | 查询项目 Bug 列表 |
| `创建需求`、`新建需求` | 创建新需求 |
| `创建Bug`、`新建Bug`、`提交Bug` | 创建新 Bug |
| `查询迭代`、`查看迭代` | 查询迭代列表 |
| `触发构建`、`开始构建` | 触发 CI 构建 |

## 配置要求

使用前需要配置以下信息（在 `config.json` 中）：

```json
{
  "team": "your-team-name",
  "token": "your-personal-access-token",
  "default_project": "default-project-name"
}
```

### 获取方式

1. **团队名称（team）**: CODING 团队域名前缀，如 `your-team.coding.net` 中的 `your-team`
2. **访问令牌（token）**: 个人账户设置 > 访问令牌 > 新建令牌，勾选 `collaboration:issue:rw` 权限
3. **默认项目（default_project）**: 项目名称，如 `SwiftAgent`

## API 端点

- **Base URL**: `https://e.coding.net/open-api`
- **请求方式**: POST
- **认证方式**: `Authorization: token {your-token}`

## 使用示例

### 查询需求

```
用户：查询 SwiftAgent 项目的需求
助手：正在查询 SwiftAgent 项目的需求列表...
[返回需求列表]
```

### 创建 Bug

```
用户：创建一个 Bug：登录页面样式错乱，优先级高
助手：已创建 Bug：
- 标题：登录页面样式错乱
- 类型：缺陷
- 优先级：高
- 状态：待处理
```

### 查询迭代

```
用户：查询 SwiftAgent 的迭代
助手：当前项目迭代：
- ChartGen V1.6（进行中）
- ChartGen V1.5（已完成）
```

## 相关文档

- 详细 API 文档: `docs/CODING-OpenAPI-Guide.md`
- CODING 官方文档: https://coding.net/help/openapi

## 注意事项

1. 访问令牌需要足够的权限（至少 `collaboration:issue:rw`）
2. API 频率限制：每秒最多 30 次请求
3. 创建令牌后请妥善保管，刷新后无法再次查看
