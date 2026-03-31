# OpenAI Data Agent 架构设计文档

> 基于 OpenAI 官方技术博客和 Agents SDK 文档整理，用于指导 Data Agent 代码开发

---

## 一、系统总览

### 1.1 什么是 Data Agent

Data Agent 是 OpenAI 内部构建的**数据自助分析智能体**，允许非技术用户通过自然语言查询公司数据仓库，自动生成 SQL 并返回结果/图表。

**核心能力：**
- 自然语言 → SQL 生成与执行
- 表结构理解与语义推理
- 查询结果可视化
- 数据血缘追溯

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户交互层                              │
│  Natural Language Input ←→ Agent Chat Interface ←→ Results  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Agent 编排层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Triage   │  │ Query    │  │ Analysis │  │ Visual    │  │
│  │ Agent    │→ │ Planning │→ │ Agent    │→ │ Agent     │  │
│  │          │  │ Agent    │  │          │  │           │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
│       ↑              │              │              │        │
│  ┌───────────────────┴──────────────┴──────────────┐        │
│  │           Guardrails (输入/输出/工具)            │        │
│  └─────────────────────────────────────────────────┘        │
│       ↑              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │
┌───────▼──────────────▼──────────────▼──────────────▼────────┐
│                     上下文增强层                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Enriched Context Store                 │   │
│  │  (Embeddings + RAG + Table Metadata + Code Context)  │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↑              ↑              ↑                      │
│  ┌────┴────┐   ┌─────┴─────┐  ┌────┴────┐                │
│  │ Schema  │   │ Query     │   │ Codex   │                │
│  │ Catalog │   │ History   │   │ Enrich. │                │
│  └─────────┘   └───────────┘   └─────────┘                │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    数据基础设施层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Data     │  │ Semantic │  │ Query    │  │ Vector    │  │
│  │ Warehouse│  │ Layer    │  │ Engine   │  │ Store     │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、上下文增强系统（核心）

这是 OpenAI Data Agent 最关键的设计。Agent 不仅依赖表 Schema，还需要**多层上下文**来理解数据含义。

### 2.1 三层上下文架构

```
Layer 1: Schema Catalog（表结构目录）
  ├── 表名、列名、数据类型
  ├── 主键/外键关系
  ├── 表描述与注释
  └── 来源：数据仓库元数据 API

Layer 2: Query History（查询历史）
  ├── 常用查询模式
  ├── 表间关联方式（JOIN 模式）
  ├── 业务含义标注（人工标注）
  └── 来源：查询日志聚合

Layer 3: Codex Enrichment（代码级上下文）
  ├── 表的 ETL 管道代码
  ├── 数据生成逻辑（如何从原始事件派生）
  ├── 数据更新频率与新鲜度保证
  ├── 数据范围与粒度说明
  ├── 业务假设与约束条件
  └── 来源：代码仓库 + Codex 分析
```

### 2.2 离线管道：上下文预计算

```
Daily Pipeline（每日离线运行）:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Schema   │───→│ Query    │───→│ Codex    │───→│ Normal-  │
│ Catalog  │    │ History  │    │ Enrich.  │    │ ized     │
└──────────┘    └──────────┘    └──────────┘    │ Context  │
                                                └────┬─────┘
                                                     │
┌──────────┐    ┌──────────┐                          │
│ Embed    │←───│ Aggreg-  │←─────────────────────────┘
│ ding     │    │ ation    │
│ API      │    └──────────┘
└────┬─────┘
     │
     ▼
┌──────────┐
│ Vector   │  ← 查询时通过 RAG 检索最相关上下文
│ Store    │
└──────────┘
```

**关键设计决策：**
- 每日离线聚合 → 归一化表示 → Embedding → 存储
- 查询时通过 RAG 检索，**不扫描原始元数据**
- 保证低延迟，即使面对数万张表

### 2.3 Codex Enrichment 详解

> **核心理念：Meaning Lives in Code**
> Schema 和查询历史只描述表的"形状"和"用法"，真正的含义在代码里。

```python
# 伪代码：Codex Enrichment 管道
class CodexEnrichment:
    """通过代码分析增强表理解"""

    def enrich_table(self, table_name: str) -> TableContext:
        # 1. 找到生成该表的 ETL 管道代码
        pipeline_code = self.codebase.search(
            f"pipeline that writes to {table_name}"
        )

        # 2. 用 Codex 分析代码逻辑
        enrichment = codex.analyze(
            f"Analyze this pipeline code and explain:\n"
            f"1. What data does this table actually contain?\n"
            f"2. How is each column derived?\n"
            f"3. What are the data freshness guarantees?\n"
            f"4. What is the granularity and scope?\n"
            f"5. What business assumptions does this encode?\n"
            f"\nCode:\n{pipeline_code}"
        )

        return enrichment
```

---

## 三、Agent 编排架构

### 3.1 多 Agent 协作模式

OpenAI 推荐**分工明确的多 Agent 架构**，通过 Handoffs 机制协调。

```python
# Agent 职责划分
agents = {
    "triage_agent": {
        "role": "意图识别与路由",
        "responsibilities": [
            "理解用户查询意图",
            "判断是简单查询还是复杂分析",
            "决定路由到哪个专家 Agent"
        ],
        "tools": ["handoff_to_query", "handoff_to_analysis", "handoff_to_faq"],
        "model": "gpt-5.4-mini"  # 快速模型，降低成本
    },

    "query_planning_agent": {
        "role": "SQL 生成与执行",
        "responsibilities": [
            "根据上下文生成 SQL",
            "验证 SQL 语法与语义",
            "执行查询并返回结果"
        ],
        "tools": [
            "search_tables",        # 查找相关表
            "get_table_schema",      # 获取表结构
            "get_table_context",     # 获取增强上下文（RAG）
            "execute_query",         # 执行 SQL
            "validate_sql"           # SQL 验证
        ],
        "model": "o4-mini"  # 推理模型，处理复杂 SQL
    },

    "analysis_agent": {
        "role": "结果分析与洞察",
        "responsibilities": [
            "解读查询结果",
            "生成业务洞察",
            "识别数据异常和趋势"
        ],
        "tools": [
            "run_python_code",       # 数据分析
            "generate_chart",        # 图表生成
            "compare_with_historical" # 历史对比
        ],
        "model": "o3"  # 最强推理能力
    },

    "visual_agent": {
        "role": "可视化呈现",
        "responsibilities": [
            "选择最佳图表类型",
            "生成可视化图表",
            "格式化输出"
        ],
        "tools": ["generate_chart", "export_to_csv"],
        "model": "gpt-5.4"  # 平衡性能和成本
    }
}
```

### 3.2 Handoff（交接）机制

```python
from agents import Agent, handoff, RunContextWrapper, Runner

# 创建交接
triage_agent = Agent(
    name="Triage Agent",
    instructions="分析用户意图，路由到合适的专家...",
    handoffs=[
        query_agent,                    # 直接交接
        handoff(
            agent=analysis_agent,
            on_handoff=on_analysis_handoff,  # 交接时触发
            input_type=HandoffContext,         # 交接时传入数据
        ),
        faq_agent,
    ],
    model="gpt-5.4-mini"
)

# 交接回调：预加载数据
async def on_analysis_handoff(ctx, input_data):
    """交接时预取相关表上下文"""
    ctx.context.relevant_tables = await search_tables(input_data.query)
    ctx.context.enriched_context = await rag_retrieve(input_data.query)
```

### 3.3 Input Filter（历史过滤）

```python
# 交接时控制下一个 Agent 看到的历史
handoff_obj = handoff(
    agent=analysis_agent,
    input_filter=lambda data: HandoffInputData(
        input_history=data.input_history,
        pre_handoff_items=data.pre_handoff_items,
        new_items=[item for item in data.new_items
                   if not item.tool_call],  # 过滤工具调用历史
        input_items=data.input_items,
        run_context=data.run_context,
    )
)
```

---

## 四、工具系统设计

### 4.1 工具分类

```
┌─────────────────────────────────────────────┐
│              Tool Registry                   │
├─────────────┬───────────────────────────────┤
│  数据工具    │  search_tables                │
│             │  get_table_schema              │
│             │  get_table_context (RAG)       │
│             │  execute_query                 │
│             │  validate_sql                  │
│             │  explain_query_plan            │
├─────────────┼───────────────────────────────┤
│  分析工具    │  run_python_code               │
│             │  detect_anomalies              │
│             │  calculate_statistics          │
│             │  compare_periods               │
├─────────────┼───────────────────────────────┤
│  可视化工具  │  generate_chart                │
│             │  export_to_csv                 │
│             │  create_dashboard              │
├─────────────┼───────────────────────────────┤
│  系统工具    │  get_user_permissions          │
│             │  audit_query_log               │
│             │  get_data_freshness            │
└─────────────┴───────────────────────────────┘
```

### 4.2 工具实现模式

```python
from agents import Agent, function_tool, RunContextWrapper
from pydantic import BaseModel

class SearchTablesInput(BaseModel):
    query: str
    limit: int = 10
    data_source: str | None = None

@function_tool
async def search_tables(
    ctx: RunContextWrapper[AppContext],
    query: str,
    limit: int = 10,
    data_source: str | None = None,
) -> str:
    """搜索与查询相关的数据表。

    使用 RAG 从 Enriched Context Store 中检索最相关的表，
    返回表名、描述、列信息和数据新鲜度。
    """
    # 1. RAG 检索相关表
    results = await ctx.context.vector_store.search(
        query=query,
        filter={"type": "table_context"},
        limit=limit
    )

    # 2. 权限过滤
    accessible = [
        r for r in results
        if r.table_name in ctx.context.user_permissions
    ]

    # 3. 格式化返回
    return format_table_results(accessible)


# 注册工具到 Agent
query_agent = Agent(
    name="Query Agent",
    instructions="...",
    tools=[search_tables, get_table_schema, execute_query],
)
```

### 4.3 Agent as Tool 模式

```python
# 将 Agent 包装为工具，支持结构化输入
query_agent = Agent(
    name="Query Agent",
    instructions="生成并执行 SQL 查询",
    output_type=QueryResult,
)

# 在 Triage Agent 中作为工具使用
triage_agent = Agent(
    name="Triage Agent",
    instructions="...",
    tools=[
        query_agent.as_tool(
            tool_name="generate_and_run_query",
            tool_description="生成 SQL 并执行，返回查询结果",
            parameters=QueryInput,
        ),
    ],
)
```

---

## 五、安全护栏（Guardrails）

### 5.1 三层护栏架构

```python
from agents import (
    input_guardrail, output_guardrail,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
)

# === 输入护栏 ===
@input_guardrail
async def query_safety_check(ctx, agent, user_input):
    """检查用户输入是否包含危险操作"""
    # 使用快速/廉价模型检查
    result = await Runner.run(safety_agent, user_input)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_dangerous,
    )

# === 输出护栏 ===
@output_guardrail
async def result_validation(ctx, agent, output):
    """验证 Agent 输出"""
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=output.row_count > 100000,  # 结果太大
    )

# === 工具护栏 ===
@function_tool
@tool_input_guardrail  # 工具调用前检查
@tool_output_guardrail  # 工具调用后检查
async def execute_query(ctx, sql: str) -> str:
    """执行 SQL 查询，带护栏"""
    ...
```

### 5.2 执行模式

```python
# 阻塞模式：护栏先执行，通过后才调用 Agent（省钱）
agent = Agent(
    name="Safe Agent",
    input_guardrails=[safety_check],  # run_in_parallel=False
)

# 并行模式：护栏和 Agent 同时执行（省时间）
agent = Agent(
    name="Fast Agent",
    input_guardrails=[parallel_safety_check],  # run_in_parallel=True
)
```

---

## 六、记忆与状态管理

### 6.1 会话状态流转

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ User    │────→│ Triage  │────→│ Query   │────→│ Analysis│
│ Input   │     │ Agent   │     │ Agent   │     │ Agent   │
└─────────┘     └────┬────┘     └────┬────┘     └────┬────┘
                     │               │               │
                     ▼               ▼               ▼
              ┌──────────────────────────────────────────┐
              │         Shared RunContext                 │
              │  ┌──────────────┐  ┌──────────────┐     │
              │  │ user_perms   │  │ query_history│     │
              │  │ relevant_tbl │  │ enriche_ctx  │     │
              │  │ session_data │  │ user_profile │     │
              │  └──────────────┘  └──────────────┘     │
              └──────────────────────────────────────────┘
```

### 6.2 RunContext 设计

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AppContext:
    """全局应用上下文，通过 RunContextWrapper 传递"""

    # 用户信息
    user_id: str
    user_permissions: list[str] = field(default_factory=list)
    user_role: str = "analyst"

    # 数据连接
    warehouse_client: Any = None
    vector_store: Any = None

    # 会话状态
    relevant_tables: list[str] = field(default_factory=list)
    enriched_context: dict = field(default_factory=dict)
    query_history: list[dict] = field(default_factory=list)

    # 配置
    max_rows: int = 10000
    query_timeout: int = 30


# 运行 Agent 时注入上下文
result = await Runner.run(
    triage_agent,
    user_input,
    context=AppContext(
        user_id="user_123",
        user_permissions=["sales", "marketing"],
        warehouse_client=warehouse,
        vector_store=vector_store,
    )
)
```

---

## 七、模型选择策略

### 7.1 分层模型选择

| 层级 | Agent | 推荐模型 | 理由 |
|------|-------|----------|------|
| 入口 | Triage Agent | gpt-5.4-mini | 快速、便宜，意图分类不需要强推理 |
| 核心 | Query Planning | o4-mini | SQL 生成需要推理能力，但不需最强 |
| 分析 | Analysis Agent | o3 | 洞察生成需要最强推理 |
| 输出 | Visual Agent | gpt-5.4 | 图表选择平衡性能和成本 |
| 护栏 | Guardrail Agent | gpt-5.4-nano | 简单分类，极低成本 |

### 7.2 选择原则

```
简单分类/路由  →  非推理模型（快 + 便宜）
SQL 生成/代码  →  推理模型（准确率高）
复杂分析/洞察  →  最强推理模型（深度思考）
多轮对话/格式化 →  通用模型（平衡）
护栏/检查      →  最小模型（成本优先）
```

---

## 八、代码项目结构

```
data-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 入口：FastAPI 服务
│   ├── config.py                  # 配置管理
│   │
│   ├── agents/                    # Agent 定义
│   │   ├── __init__.py
│   │   ├── triage.py              # Triage Agent
│   │   ├── query_planner.py       # 查询规划 Agent
│   │   ├── analyst.py             # 分析 Agent
│   │   ├── visualizer.py          # 可视化 Agent
│   │   └── guardrail_agents.py    # 护栏专用 Agent
│   │
│   ├── tools/                     # 工具定义
│   │   ├── __init__.py
│   │   ├── table_tools.py         # 表搜索/Schema 获取
│   │   ├── query_tools.py         # SQL 执行/验证
│   │   ├── analysis_tools.py      # 数据分析工具
│   │   ├── visual_tools.py        # 可视化工具
│   │   └── system_tools.py        # 系统工具（权限等）
│   │
│   ├── guardrails/                # 护栏定义
│   │   ├── __init__.py
│   │   ├── input_guardrails.py    # 输入安全检查
│   │   ├── output_guardrails.py   # 输出验证
│   │   └── tool_guardrails.py     # 工具级护栏
│   │
│   ├── context/                   # 上下文管理
│   │   ├── __init__.py
│   │   ├── app_context.py         # RunContext 定义
│   │   ├── handoffs.py            # 交接逻辑
│   │   └── input_filters.py       # 输入过滤器
│   │
│   ├── enrichment/                # 上下文增强系统
│   │   ├── __init__.py
│   │   ├── schema_catalog.py      # Layer 1: Schema 目录
│   │   ├── query_history.py       # Layer 2: 查询历史
│   │   ├── codex_enrichment.py    # Layer 3: 代码级上下文
│   │   ├── pipeline.py            # 离线聚合管道
│   │   └── vector_store.py        # 向量存储与 RAG 检索
│   │
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── table_context.py       # 表上下文模型
│   │   ├── query_result.py        # 查询结果模型
│   │   └── handoff_types.py       # 交接数据类型
│   │
│   └── prompts/                   # Prompt 管理
│       ├── triage.md
│       ├── query_planning.md
│       ├── analysis.md
│       └── visualization.md
│
├── pipelines/                     # 离线管道
│   ├── enrichment_pipeline.py     # 上下文增强管道
│   ├── embedding_pipeline.py      # Embedding 生成
│   └── scheduler.py               # 定时调度
│
├── api/                           # API 层
│   ├── routes.py                  # 路由定义
│   ├── websocket.py               # WebSocket 支持
│   └── middleware.py              # 认证/限流
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## 九、核心流程

### 9.1 查询处理主流程

```
用户输入: "上个月哪个产品线的收入最高？"
    │
    ▼
[Input Guardrail] ─── 危险？ ──→ 拒绝
    │ 安全
    ▼
[Triage Agent] ─── 判断意图 ──→ 数据查询
    │ handoff(query_planning_agent, context={"intent": "ranking"})
    ▼
[Query Planning Agent]
    │ 1. search_tables("产品线 收入 上月")
    │    → RAG 返回: revenue_by_product_line, dim_product, dim_date
    │
    │ 2. get_table_context("revenue_by_product_line")
    │    → Codex Enrichment: "该表按日汇总，货币单位 USD..."
    │
    │ 3. 生成 SQL:
    │    SELECT product_line, SUM(revenue) as total_revenue
    │    FROM revenue_by_product_line r
    │    JOIN dim_date d ON r.date_id = d.id
    │    WHERE d.month = '2026-02'
    │    GROUP BY product_line
    │    ORDER BY total_revenue DESC
    │    LIMIT 10
    │
    │ 4. validate_sql(sql) ✅
    │ 5. execute_query(sql) → 结果
    │
    │ handoff(analysis_agent, context={"query_result": results})
    ▼
[Analysis Agent]
    │ 1. 解读结果："企业服务产品线收入最高，达到 $2.3M..."
    │ 2. 趋势分析：环比增长 15%
    │ 3. 异常检测：发现云服务产品线下降 8%
    │
    │ handoff(visual_agent, context={"insights": [...], "data": results})
    ▼
[Visual Agent]
    │ 1. 选择图表：水平柱状图（排名类数据）
    │ 2. generate_chart(type="bar_horizontal", data=...)
    │
    ▼
[Output Guardrail] ─── 数据泄露？结果过大？ ──→ 修正
    │ 安全
    ▼
返回用户: 图表 + 洞察文字
```

### 9.2 离线管道流程

```
每日凌晨 2:00 触发
    │
    ▼
[Schema Catalog Sync]
    │ 从数据仓库拉取最新表结构
    │ 更新表描述、列类型、关系
    ▼
[Query History Aggregation]
    │ 聚合过去 24h 查询日志
    │ 提取 JOIN 模式、常用过滤条件
    │ 人工标注合并
    ▼
[Codex Enrichment]
    │ 对每个表：
    │   1. 定位 ETL 管道代码
    │   2. Codex 分析代码逻辑
    │   3. 提取：含义、粒度、更新频率、业务约束
    ▼
[Context Normalization]
    │ 合并三层上下文 → 统一 TableContext 格式
    ▼
[Embedding Generation]
    │ 使用 text-embedding-3-large 生成向量
    ▼
[Vector Store Update]
    │ 写入/更新向量数据库
    ▼
[Health Check]
    │ 验证采样表的 RAG 检索质量
    │ 告警低质量表
    ▼
完成，等待下次触发
```

---

## 十、关键技术要点

### 10.1 RAG 检索策略

```python
# 分阶段检索：先宽后窄
async def retrieve_context(query: str, ctx: AppContext):
    # 阶段 1：粗筛相关表（top-20）
    candidates = await ctx.vector_store.search(
        query=query,
        top_k=20,
        filter={"type": "table_context"}
    )

    # 阶段 2：用强模型精选（top-5）
    selector_prompt = f"""
    用户查询: {query}
    候选表: {[c.table_name for c in candidates]}
    
    请选择最相关的 5 张表，并说明每张表的作用。
    """

    selected = await Runner.run(
        table_selector_agent,  # gpt-5.4-mini，快且准
        selector_prompt,
    )

    # 阶段 3：获取完整增强上下文
    full_context = await ctx.vector_store.get(
        ids=[t.id for t in selected.tables]
    )

    return full_context
```

### 10.2 SQL 生成最佳实践

```python
# Query Agent 的 Instructions 模板
QUERY_AGENT_INSTRUCTIONS = """
你是一个 SQL 专家。根据用户的自然语言查询生成 SQL。

## 可用上下文
{enriched_context}

## 规则
1. 优先使用已标注的常用 JOIN 模式
2. 注意表的数据新鲜度，不要查询超过数据更新周期的数据
3. 注意表的粒度（日/周/月），避免不当聚合
4. 时间范围必须明确（WHERE 条件）
5. LIMIT 默认 100，最多 10000
6. 不要使用子查询嵌套超过 3 层

## 输出格式
返回 JSON:
{
  "sql": "...",
  "explanation": "为什么这样写",
  "tables_used": [...],
  "confidence": 0.95,
  "warnings": ["可能不精确的地方"]
}
"""
```

### 10.3 错误处理与回退

```python
async def safe_query_execution(sql: str, ctx: AppContext):
    """带重试和回退的查询执行"""

    try:
        # 尝试 1：直接执行
        result = await ctx.warehouse.execute(sql)
        return result

    except SyntaxError:
        # 回退 1：让 Agent 修复 SQL
        fix_result = await Runner.run(
            sql_fix_agent,
            f"SQL 有语法错误，请修复: {sql}\n错误: {e}",
        )
        return await ctx.warehouse.execute(fix_result.fixed_sql)

    except TimeoutError:
        # 回退 2：添加 LIMIT 或简化查询
        simplified = await Runner.run(
            sql_simplify_agent,
            f"查询超时，请简化: {sql}",
        )
        return await ctx.warehouse.execute(simplified.simplified_sql)

    except PermissionError:
        # 回退 3：返回用户可访问的替代表
        alternatives = await suggest_alternative_tables(sql, ctx)
        return {"error": "无权限", "alternatives": alternatives}
```

---

## 十一、性能优化

### 11.1 延迟优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 入口路由 | Triage Agent 用 nano 模型 | < 200ms |
| 上下文检索 | RAG 预计算 + 向量索引 | < 100ms |
| 并行护栏 | input_guardrail run_in_parallel=True | 与 Agent 并行 |
| 工具调用 | execute_query 异步 + 连接池 | < 500ms |
| 模型选择 | 分层模型（nano→mini→base→pro） | 按需消耗 |

### 11.2 成本优化

| 策略 | 节省 |
|------|------|
| 简单查询用 nano/mini 模型 | 90% token 成本 |
| 护栏用最小模型 | 护栏成本 < 5% 总成本 |
| 离线预计算上下文 | 避免运行时重复分析 |
| Handoff 时过滤工具历史 | 减少 40%+ context tokens |
| FAQ 命中直接返回 | 零大模型调用 |

---

## 十二、监控与可观测性

### 12.1 Tracing

```python
from agents import Runner, trace

async def handle_query(user_input: str, ctx: AppContext):
    with trace("data_agent", group_id=ctx.user_id):
        # 自动追踪所有 Agent 调用、工具使用、Handoff
        result = await Runner.run(triage_agent, user_input, context=ctx)
        return result

    # Trace 包含：
    # - 每个 Agent 的调用时间
    # - 每个工具的输入/输出
    # - Handoff 路径
    # - Token 消耗
    # - Guardrail 触发记录
```

### 12.2 关键指标

```
查询成功率: result.successful_queries / total_queries
平均延迟: avg(query_end_time - query_start_time)
SQL 准确率: avg(human_rating) (人工评估)
上下文相关性: avg(retrieved_tables ∩ actually_used_tables)
护栏触发率: guardrail_triggers / total_queries
模型成本: sum(token_cost) per query per model_tier
```

---

## 十三、总结

### 核心设计原则

1. **上下文 > 模型**：再强的模型也不如给它足够的上下文。三层上下文（Schema + History + Codex）是 Agent 理解数据的关键。

2. **离线计算 > 在线推理**：上下文增强、Embedding、Codex 分析全部离线完成，查询时只做 RAG 检索，保证低延迟。

3. **分而治之**：多 Agent 架构，每个 Agent 职责单一，通过 Handoff 协作。

4. **分层模型**：不是所有任务都需要最强模型，路由/护栏/FAQ 用小模型，SQL 生成和分析用推理模型。

5. **护栏优先**：输入/输出/工具三层护栏，防止危险 SQL、数据泄露、过大结果。

6. **代码即文档**：把 Slack 讨论和设计决策写进代码仓库，让 Agent（和新人）能发现它们。

### 技术栈推荐

| 组件 | 推荐方案 |
|------|----------|
| Agent 框架 | OpenAI Agents SDK (Python) |
| 模型 API | OpenAI Responses API |
| 向量数据库 | Pinecone / Weaviate / pgvector |
| 数据仓库连接 | SQLAlchemy + async |
| Web 框架 | FastAPI |
| 监控 | OpenAI Tracing + Langfuse |
| 调度 | Celery / Airflow |

---

*文档版本: v1.0*
*最后更新: 2026-03-28*
*参考资料: OpenAI Blog, OpenAI Agents SDK Docs, OpenAI Developer Learning Track*
