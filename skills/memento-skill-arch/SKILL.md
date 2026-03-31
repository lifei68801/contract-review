---
name: memento-skill-arch
description: AI Agent 技能系统架构设计参考。基于 Memento-Skills 开源项目，提供完整的 Skill 框架设计模式，包括六层上下文体系、双执行模式（Knowledge/Playbook）、多路召回检索（关键词+向量）、沙箱执行、策略治理、渐进式信息披露等核心架构。当用户需要设计或优化 AI Agent 技能系统、构建 Skill Framework、实现 Text-to-SQL Agent、设计 Agent Skill 生命周期管理、或参考成熟开源 Agent 架构时激活。
---

# Memento Skill Architecture

基于 [Memento-Skills](https://github.com/Memento-Teams/Memento-Skills) 深度提炼的 AI Agent 技能系统架构指南。

## 核心理念

Skill 不是 prompt 模板，而是**可执行的知识包**。每个 Skill = SKILL.md（知识）+ scripts（能力）+ references（上下文）。

## 架构总览

```
用户 Query
    │
    ▼
┌──────────────────┐
│   Gateway (契约)  │  ← discover / search / execute
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│   Provider (编排) │  ← 检索 → 校验 → 路由 → 执行
└───────┬──────────┘
        │
   ┌────┴────┐
   ▼         ▼
Retrieval   Execution
(多路召回)   (双模式执行)
```

## 1. Skill 数据模型

```python
class Skill(BaseModel):
    name: str                          # 唯一标识
    description: str                   # 功能描述（用于检索 + 触发）
    content: str                       # SKILL.md 全文
    dependencies: list[str]            # pip 依赖
    version: int                       # 版本号
    files: dict[str, str]              # 技能文件映射
    references: dict[str, str]         # 渐进式披露的参考文档
    source_dir: Optional[str]          # 技能目录路径
    execution_mode: ExecutionMode      # knowledge | playbook
    entry_script: Optional[str]        # playbook 入口脚本
    required_keys: list[str]           # 运行所需的 API Key
    parameters: Optional[dict]         # 参数 schema（OpenAI/Anthropic 兼容）
    allowed_tools: list[str]           # 允许使用的工具白名单
```

**关键设计：**
- `is_playbook` 自动推断：目录下除 SKILL.md 外还有文件 → Playbook
- `to_embedding_text()` 用于语义检索：name + description + content + dependencies

## 2. 双执行模式

### Knowledge 模式（纯推理）
SKILL.md 注入 prompt，LLM 直接生成答案或 tool_calls。
- 适用：问答、分析、建议、内容生成
- 无需执行任何代码

### Playbook 模式（代码执行）
LLM 理解 SKILL.md 后生成/调用脚本，在沙箱中执行。
- 适用：数据处理、文件操作、API 调用、复杂计算
- 自动列出目录下所有可用脚本，拼入 prompt

**判断逻辑：**
```python
def is_playbook(source_dir):
    # 目录下除 SKILL.md 外有任何文件 → Playbook
    for p in Path(source_dir).rglob("*"):
        if p.is_file() and not p.name.startswith(".") and p.name != "SKILL.md":
            return True
    return False
```

## 3. 多路召回检索

### 3.1 关键词召回（Keyword Recall）
- 对 skill name 做分词匹配
- 支持别名映射（如 "ppt" → "doc2slides"）
- 支持前缀匹配和模糊匹配

### 3.2 向量召回（Embedding Recall）
- 存储：sqlite-vec（轻量级，无需外部向量数据库）
- 距离度量：cosine
- 线程安全：跨线程时重建连接
- 自动维度检测：从 embedding API 推断

```python
# 核心流程
async def search(query, k=10, min_score=0.0):
    vec = await embed_query(query)
    rows = db.execute("""
        SELECT skill_name, distance
        FROM skill_embeddings
        WHERE embedding MATCH ?
        ORDER BY distance LIMIT ?
    """, (vec_bytes, k))
    return [EmbeddingMatch(name, 1.0 - distance) for name, distance in rows]
```

### 3.3 混合排序
- 多路召回结果合并
- RRF (Reciprocal Rank Fusion) 或加权融合
- 可配置各路权重

## 4. 执行引擎

### 4.1 执行流程

```
execute(skill, query, params)
    │
    ├─ 1. 过滤工具（allowed_tools 白名单）
    ├─ 2. 选择相关 references（渐进式披露）
    ├─ 3. 构建 prompt
    │     ├─ skill 内容
    │     ├─ 可用脚本列表（Playbook）
    │     ├─ 工具摘要
    │     ├─ 环境信息（平台、时间、工作目录）
    │     └─ 相关 references
    │
    ├─ 4. LLM 调用（tool_calls 或纯文本）
    │     │
    │     ├─ has tool_calls → 逐个执行
    │     │     ├─ 校验工具是否在白名单
    │     │     ├─ Policy 检查
    │     │     └─ Sandbox 执行
    │     │
    │     ├─ [NOT_RELEVANT] → 标记不相关
    │     └─ 纯文本 → fallback 处理
    │
    └─ 5. 返回 SkillExecutionOutcome
```

### 4.2 渐进式信息披露

**不要一次性把所有 references 塞进 prompt。**

```python
def _select_relevant_references(skill.references, query):
    # 只选择与 query 相关的 references
    # 每个 reference 截断到 2000 字符
    # 按 query 关键词匹配 + embedding 相似度排序
```

**三层加载：**
1. **Metadata**（~100 tokens）：name + description，始终在上下文
2. **SKILL.md body**（<5k tokens）：技能触发时加载
3. **references/ scripts/ assets/**：按需加载，不占用常驻上下文

### 4.3 错误分类体系

```python
class ErrorType(str, Enum):
    INPUT_REQUIRED = "input_required"       # 需要更多输入
    INPUT_INVALID = "input_invalid"         # 输入格式错误
    RESOURCE_MISSING = "resource_missing"   # 缺少文件/依赖
    PERMISSION_DENIED = "permission_denied" # 权限不足
    TIMEOUT = "timeout"                     # 执行超时
    DEPENDENCY_ERROR = "dependency_error"   # 依赖缺失
    EXECUTION_ERROR = "execution_error"     # 代码执行失败
    POLICY_BLOCKED = "policy_blocked"       # 策略拦截
    ENVIRONMENT_ERROR = "environment_error" # 环境问题
    UNAVAILABLE = "unavailable"             # 服务不可用
    INTERNAL_ERROR = "internal_error"       # 内部错误
```

## 5. Gateway 契约层

Gateway 是 Agent 层与 Skill 系统之间的**唯一接口契约**：

```python
class SkillGateway(Protocol):
    def discover(self) -> list[SkillManifest]: ...
    async def search(self, query, k=5, cloud_only=False) -> list[SkillManifest]: ...
    async def execute(self, skill_name, params, options=None) -> SkillExecutionResponse: ...
```

**统一响应格式：**
```python
class SkillExecutionResponse(BaseModel):
    ok: bool                    # 是否成功
    status: SkillStatus         # success/partial/failed/blocked/timeout
    error_code: SkillErrorCode  # 错误分类
    summary: str                # 结果摘要
    output: Any                 # 主输出
    outputs: dict[str, Any]     # 多输出映射
    artifacts: list[str]        # 生成的文件列表
    diagnostics: dict           # 诊断信息
    skill_name: str             # 技能名
```

## 6. 策略治理（Policy）

- **allowed_tools 白名单**：每个 skill 声明可用工具，执行时强制过滤
- **required_keys 前置检查**：缺少 API Key 时提前报错，不进入 LLM 调用
- **Sandbox 隔离**：Playbook 在沙箱中执行，限定资源和时间
- **依赖自动安装**：执行前检查 dependencies，自动 pip install

## 7. 关键设计模式

### 模式 A：技能目录约定
```
skill-name/
├── SKILL.md          # 必需：知识 + 指令
├── references/       # 可选：按需加载的参考文档
│   ├── api.md
│   └── schema.md
├── scripts/          # 可选：可执行脚本
│   └── main.py
└── assets/           # 可选：输出用资源
    └── template.html
```

### 模式 B：渐进式 Prompt 构建
```
Prompt = System指令
       + SKILL.md 内容
       + 相关 references（截断 2000 字符）
       + 可用脚本列表
       + 工具摘要
       + 环境上下文（平台/时间/路径）
       + 用户 query
```

### 模式 C：不相关标记
LLM 可以返回 `[NOT_RELEVANT]` 标记 query 与 skill 不匹配，避免强行执行。

### 模式 D：操作结果追踪
```python
class SkillExecutionOutcome(BaseModel):
    operation_results: list[dict]  # 已执行的 tool 调用明细
    artifacts: list[str]           # 生成的文件路径
```
用户可以看到每一步 tool 调用的输入和输出。

## 8. 实现建议

### 技术选型
| 组件 | Memento 方案 | 替代方案 |
|------|-------------|----------|
| 向量存储 | sqlite-vec | ChromaDB / Qdrant / pgvector |
| Embedding | OpenAI 兼容 API | 本地模型 (sentence-transformers) |
| LLM | OpenAI 兼容 | 任意 |
| 沙箱 | uv + 进程隔离 | Docker / Firecracker |
| 数据校验 | Pydantic | dataclass / zod |

### 落地步骤
1. 定义 Skill 数据模型（参考 schema.py）
2. 实现本地 Skill 加载器（扫描目录 → 解析 SKILL.md）
3. 实现关键词召回 + 向量召回
4. 实现双模式执行引擎（Knowledge / Playbook）
5. 实现 Gateway 契约层
6. 添加策略治理（工具白名单、Key 检查、沙箱）

### 参考文件
- 详细的 Prompt 模板和代码示例：见 `references/implementation-examples.md`
- 数据流和状态机：见 `references/data-flow.md`
