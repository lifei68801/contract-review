---
name: coding-net
description: 查询和操作 Coding 开放平台（e.coding.net）的迭代、事项（需求/缺陷/任务）、团队成员等数据。当用户涉及 Coding 平台操作时触发，如「查迭代」「查事项」「当前迭代的需求」「Coding 上的 bug」「团队成员列表」「assignee」。所有 API 均需环境变量 CODING_TOKEN。
---

# Coding Open API Skill

## 环境配置

| 变量 | 必须 | 说明 |
|------|------|------|
| `CODING_TOKEN` | **是** | Bearer Token，`export CODING_TOKEN=...` |
| `CODING_DEFAULT_PROJECT_NAME` | **是** | 默认项目名，推荐值：`biaopin-swiftagent` |
| `CODING_DEFAULT_ITERATION_CODE` | **是** | 默认迭代 Code，需先查询迭代列表后填写（见下方配置流程） |

## 首次安装：必须完成以下配置

> **每次新会话均需重新 export，或写入 shell 配置文件（~/.zshrc / ~/.bashrc）永久生效。**

**第一步：设置 Token（必须）**
```bash
export CODING_TOKEN=your_token_here
```

**第二步：设置默认项目（推荐 `biaopin-swiftagent`）**
```bash
export CODING_DEFAULT_PROJECT_NAME=biaopin-swiftagent
```

**第三步：查询迭代列表，获取当前迭代 Code（必须完成）**

先运行以下代码查看所有迭代：
```python
import sys; sys.path.insert(0, "path/to/coding-net/scripts")
from iterations import get_iteration_list_code_and_name
for it in get_iteration_list_code_and_name():
    print(it['code'], it['name'])
```
从输出中找到当前正在进行的迭代，记下其 `code`。

**第四步：设置默认迭代（必须）**
```bash
export CODING_DEFAULT_ITERATION_CODE=<上一步看到的 code>
```

**完成后即可零参数查询：**
```python
result = describe_issue_list()   # project_name 和 iteration 均走默认值
```

## 脚本结构

```
scripts/
├── core.py        — HTTP 客户端、Token 解析、CodingAPIError
├── iterations.py  — 迭代 API（依赖 core）
├── issues.py      — 事项 API（依赖 core + iterations）
└── members.py     — 团队成员 API（依赖 core）
```

在 Python 中使用（脚本已处理 sys.path，直接 import 即可）：

```python
import sys
sys.path.insert(0, "path/to/scripts")
from iterations import get_iteration_list_code_and_name
from issues import describe_issue, describe_issue_list
from members import get_team_members_id_and_name
```

## 公开函数速查

### iterations.py

```python
get_iteration_list_code_and_name(project_name=None, *, token=None) -> [{'code': int, 'name': str}]
```
分页拉取全量迭代列表。返回的 `code` 即 `describe_issue_list(iteration=...)` 所需值。

### issues.py

```python
describe_issue_list(
    project_name=None, *,   # 省略时读 CODING_DEFAULT_PROJECT_NAME
    issue_type="ALL",       # ALL / REQUIREMENT / DEFECT / MISSION
    limit="2000",
    assignee_ids=None,      # [int] — 来自 get_team_members_id_and_name 的 id
    iteration=None,         # int  — 省略时读 CODING_DEFAULT_ITERATION_CODE
    status_types=None,      # None→TODO+PROCESSING; []→不过滤; ['TODO',...]→指定
    base_issue_type=None,   # REQUIREMENT / DEFECT / MISSION
    token=None,
) -> dict  # Response.IssueList 每条含 Code/Name/IssueStatusName/Priority/CreatorName/HandlerName/StartDate/DueDate
```

```python
describe_issue(project_name=None, issue_code=0, *, token=None) -> dict
# 返回 {Name, Description, IssueStatusName, AssigneeName, CreatorName}
```

### members.py

```python
get_team_members_id_and_name(*, token=None) -> [{'id': int, 'name': str}]
```
分页拉取全量团队成员。`id` 可用于 `describe_issue_list(assignee_ids=[...])` 过滤。

## 常见工作流

**查当前迭代所有未完成事项：**
```python
iterations = get_iteration_list_code_and_name(project_name)
# 选择目标迭代 code（通常取最新一个）
result = describe_issue_list(project_name, iteration=iterations[-1]['code'])
issues = result['Response']['IssueList']
```

**按成员过滤事项：**
```python
members = get_team_members_id_and_name()
uid = next(m['id'] for m in members if m['name'] == '张三')
result = describe_issue_list(project_name, iteration=code, assignee_ids=[uid])
```

**查单条事项详情（含描述）：**
```python
detail = describe_issue(project_name, issue_code=12345)
```
