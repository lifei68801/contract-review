# 数据分析 Agent 产品优化设计方案

> 基于 OpenAI 内部数据 Agent 架构深度拆解，转化为可落地的产品优化指导

---

## 一、问题定义

### 1.1 现状痛点

企业数据分析场景中普遍存在三类问题：

**数据发现成本极高**
- 企业级数据仓库通常包含数万张表，光"找到正确的表"就要消耗分析师数小时
- 表名相似但语义不同（`user_login` 包含登出用户 vs `user_active` 不包含），需要大量领域知识才能区分
- 表结构变更无人通知，分析师依赖的表可能已失效

**分析错误难以察觉**
- SQL 容易写错：多对多 JOIN 导致笛卡尔积、WHERE 条件推送位置错误、NULL 处理不当
- 错误是静默的——查询返回了结果但不正确，用户无法察觉
- 缺乏"黄金 SQL"作为参照标准

**数据治理与 AI 能力脱节**
- LLM 能力再强，面对混乱的元数据也无法产出正确结果
- 传统数据字典维护成本高，更新滞后于实际数据变更
- 表的"真正含义"藏在创建它的代码里，不在 schema 描述中

### 1.2 设计目标

| 目标 | 指标 |
|------|------|
| 自然语言查询准确率 | 单轮对话完成率 > 80% |
| 查询响应时间 | < 30s（含推理） |
| 错误自愈能力 | 自动检测并修复 > 60% 的常见 SQL 错误 |
| 用户覆盖范围 | 支持非技术用户独立完成分析 |

---

## 二、核心架构：六层上下文体系

这是整个设计最关键的部分。不是简单给 LLM 一个 SQL 生成 prompt，而是构建六层结构化知识体系。

```
┌─────────────────────────────────────────────────────────┐
│                    用户自然语言查询                         │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L6: 自学习记忆层                          │
│  用户纠错 + Agent 自发现规则，持久化存储                    │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L5: 组织知识层                            │
│  Slack / 文档 / Notion 中的指标定义、内部代号、事故记录     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L4: 代码语义推断层（核心差异化）             │
│  爬取数据管道代码，自动推断表的真正含义                      │
│  → 粒度、更新频率、数据范围、唯一性约束、过滤条件            │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L3: 专家描述层                            │
│  领域专家人工维护的表/列说明，捕获业务语义和历史坑            │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L2: 查询推理层                            │
│  从历史 SQL 学习表关联模式、常用过滤条件、JOIN 惯例          │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 L1: 元数据层（基础）                       │
│  Schema（列名、类型、约束）+ 表血缘（上下游依赖关系）        │
└─────────────────────────────────────────────────────────┘
```

### 2.1 L1: 元数据层（Metadata Layer）

**职责：** 提供结构化的表和列基本信息

**数据来源：**
```sql
-- 从数据仓库系统表自动采集
SELECT table_name, column_name, data_type, is_nullable,
       column_default, comment
FROM information_schema.columns
WHERE table_schema = 'production';

-- 表血缘关系（从 DAG 调度系统获取）
SELECT source_table, target_table, transform_type
FROM data_lineage
WHERE target_table = '{query_table}';
```

**存储结构：**
```json
{
  "table": "user_daily_active",
  "schema": [
    {"name": "user_id", "type": "bigint", "nullable": false},
    {"name": "activity_date", "type": "date", "nullable": false},
    {"name": "session_count", "type": "int", "nullable": true},
    {"name": "platform", "type": "varchar(20)", "nullable": true}
  ],
  "lineage": {
    "upstream": ["raw_events", "user_profile"],
    "downstream": ["engagement_report", "retention_analysis"],
    "transform_type": "aggregation"
  }
}
```

**实现要点：**
- 定时从数据仓库系统表同步，建议每小时一次
- 血缘关系优先从调度系统（如 Airflow DAG）获取，其次从查询日志推断
- 列级血缘如果不可用，至少维护表级血缘

### 2.2 L2: 查询推理层（Query Inference Layer）

**职责：** 从历史查询中学习表关联模式和常见用法

**核心思路：** 分析过去 30 天的 SQL 查询日志，提取表间关联规则

```python
class QueryInferenceEngine:
    """
    从历史 SQL 日志中学习：
    1. 哪些表经常一起 JOIN
    2. JOIN 的条件是什么
    3. 常用的 WHERE 过滤模式
    4. 聚合函数使用习惯
    """

    def extract_join_patterns(self, sql_logs: list[dict]) -> dict:
        """
        返回格式：
        {
            "table_pairs": [
                {
                    "tables": ["orders", "users"],
                    "frequency": 342,
                    "join_condition": "orders.user_id = users.id",
                    "join_type": "LEFT"
                }
            ],
            "filter_patterns": [
                {
                    "table": "orders",
                    "column": "created_at",
                    "common_ops": ["BETWEEN", ">="],
                    "frequency": 891
                }
            ]
        }
        """
        ...

    def get_table_affinity(self, table_name: str, top_k: int = 5) -> list:
        """返回与指定表最常关联的 top_k 张表"""
        ...
```

**关键设计：**
- 只保留高频模式（出现 > 10 次的关联），过滤噪声
- 区分 INNER JOIN 和 LEFT JOIN 的使用场景
- 记录 JOIN 条件的具体列，而不只是表名

### 2.3 L3: 专家描述层（Expert Description Layer）

**职责：** 存储人工维护的业务语义描述，弥补 schema 注释的不足

**核心问题 schema 解决不了的：**
- `status` 列的值 1/2/3 分别代表什么？（`1=active, 2=suspended, 3=deleted`）
- 这张表的数据是从哪天开始的？有历史断层吗？
- 哪些列是计算列，不应该直接 SUM？

**数据结构：**
```json
{
  "table": "user_daily_active",
  "expert_notes": {
    "table_level": "日活跃用户表，注意只包含 APP 端数据，不包含 Web 端",
    "important_warnings": [
      "2025-06-01 之后登录逻辑变更，前后数据不可直接比较",
      "test_mode=true 的用户已过滤，但未包含已删除用户的去激活数据"
    ],
    "column_level": {
      "session_count": "只统计时长 > 3秒 的会话，短会话不计入",
      "platform": "iOS/Android/WebSDK 三个值，H5 归入 WebSDK"
    }
  },
  "maintainer": "data-team@company.com",
  "last_updated": "2026-03-20"
}
```

**维护策略：**
- 支持 Agent 自动生成草稿 + 人工审核确认
- 每次 Agent 犯错并被用户纠正后，自动生成一条 expert_note 建议
- 提供简易 Web 界面让分析师直接补充说明

### 2.4 L4: 代码语义推断层（Code Semantic Layer）⭐ 核心差异化

**职责：** 爬取生成这张表的数据管道代码，自动推断表的真正语义

**为什么这是最关键的一层：**

传统方式依赖人写文档描述表含义，但文档永远滞后。表的"真实面目"藏在创建它的 SQL/Python 代码里：
- 代码里的 WHERE 条件 = 表的数据范围
- GROUP BY 的列 = 表的粒度
- JOIN 的逻辑 = 表包含/不包含哪些数据
- 定时任务的 cron 表达式 = 表的更新频率

**实现方案：**

```python
class CodeSemanticAnalyzer:
    """
    核心能力：从 ETL/Transform 代码推断表的语义属性
    """

    def analyze_table(self, table_name: str, pipeline_code: str) -> dict:
        """
        分析生成该表的管道代码，返回推断结果
        """
        ast = self.parse(pipeline_code)

        result = {
            "granularity": self._infer_granularity(ast),
            "update_frequency": self._infer_frequency(ast),
            "data_range": self._infer_data_range(ast),
            "uniqueness": self._infer_uniqueness(ast),
            "filters_applied": self._infer_filters(ast),
            "join_semantics": self._infer_join_semantics(ast),
        }
        return result

    def _infer_granularity(self, ast) -> str:
        """
        从 GROUP BY 子句推断表的粒度
        例：GROUP BY user_id, DATE(created_at)
        → "per_user_per_day"
        """
        group_by = ast.find("GROUP BY")
        if not group_by:
            return "row_level"  # 无聚合，行级数据

        dimensions = self._extract_groupby_columns(group_by)
        return self._dimensions_to_granularity(dimensions)

    def _infer_data_range(self, ast) -> dict:
        """
        从 WHERE 子句推断数据的时间/空间范围
        例：WHERE created_at >= '2024-01-01' AND status != 'deleted'
        → {"time_start": "2024-01-01", "exclusions": ["deleted users"]}
        """
        where_clause = ast.find("WHERE")
        if not where_clause:
            return {"note": "no explicit filter in pipeline"}

        conditions = self._extract_conditions(where_clause)
        return self._conditions_to_range(conditions)

    def _infer_frequency(self, ast) -> str:
        """
        从调度配置推断更新频率
        例：Airflow schedule_interval="0 6 * * *"
        → "daily at 6:00 AM"
        """
        schedule = ast.find("schedule_interval")
        return self._cron_to_human(schedule)
```

**推断结果示例：**

```json
{
  "table": "user_daily_active",
  "inferred_semantics": {
    "granularity": "per_user_per_day",
    "update_frequency": "daily at 6:00 AM UTC",
    "data_range": {
      "time_start": "2024-01-01",
      "exclusions": ["users with test_mode=true", "bots"],
      "dedup_logic": "one row per user per day, last session wins"
    },
    "uniqueness": {
      "natural_key": ["user_id", "activity_date"],
      "constraint": "UNIQUE(user_id, activity_date)"
    },
    "filters_applied": [
      "session_duration > 3 seconds",
      "platform IN (iOS, Android, WebSDK)",
      "NOT is_bot"
    ],
    "join_semantics": "LEFT JOIN user_profile → includes users without profile",
    "source_tables": ["raw_events", "user_profile", "session_metadata"]
  }
}
```

**为什么代码推断比 schema + 历史查询更准确：**

| 信息类型 | Schema | 历史查询 | 代码推断 |
|---------|--------|---------|---------|
| 表粒度 | ❌ | ⚠️ 部分 | ✅ GROUP BY 直接得到 |
| 数据范围 | ❌ | ⚠️ 不完整 | ✅ WHERE 条件精确 |
| 更新频率 | ❌ | ⚠️ 间接推测 | ✅ cron 直接读取 |
| 包含/排除逻辑 | ❌ | ❌ | ✅ JOIN + WHERE 精确 |
| 数据来源 | ❌ | ❌ | ✅ 直接追溯 |

### 2.5 L5: 组织知识层（Organizational Knowledge Layer）

**职责：** 接入企业内部知识源，获取指标定义、业务术语、历史事故

**数据源：**
- Slack/企业微信 历史讨论
- Confluence/Notion/飞书文档
- 数据团队 Wiki
- 事故复盘报告（Post-mortem）

**实现方式：**

```python
class KnowledgeRetriever:
    """
    从企业内部知识源检索与查询相关的上下文
    """

    def __init__(self, config: dict):
        self.embeddings = EmbeddingStore(config["vector_db"])
        self.sources = KnowledgeSourceManager(config["sources"])

    def search(self, query: str, user_context: dict) -> list[dict]:
        """
        语义检索相关知识片段
        返回按相关性排序的结果
        """
        # 1. 识别查询中提到的指标/术语
        entities = self._extract_entities(query)

        # 2. 向量检索相关知识
        results = self.embeddings.search(
            query=query,
            filters={"entity": entities},
            top_k=5
        )

        # 3. 优先返回权威来源
        ranked = self._rank_by_authority(results)

        return ranked[:3]  # 只取最相关的 3 条，避免上下文膨胀
```

**关键原则：少而精**
- 不要把所有检索到的知识都塞进 prompt
- 优先级：专家描述 > 代码推断 > 历史查询 > 组织知识
- 每层最多贡献 2-3 条最相关信息

### 2.6 L6: 自学习记忆层（Self-Learning Memory Layer）

**职责：** 持久化存储 Agent 运行过程中的纠错和自发现规则

**三种学习来源：**

```python
class MemoryStore:
    """
    三种学习来源：
    1. 用户显式纠错："不对，这个表包含的是所有用户，不是活跃用户"
    2. Agent 自我发现：查询结果为空 → 自动记录可能的过滤条件
    3. 成功模式：用户确认了查询结果 → 记录该表的正确用法
    """

    def record_correction(self, table: str, wrong_assumption: str,
                          correct_info: str, user_id: str):
        """
        用户纠错记录
        例：table="user_metrics", wrong="包含所有用户",
            correct="仅包含有付费行为的用户"
        """
        entry = {
            "type": "user_correction",
            "table": table,
            "wrong": wrong_assumption,
            "correct": correct_info,
            "confidence": 1.0,  # 用户确认，最高置信度
            "reported_by": user_id,
            "created_at": datetime.now()
        }
        self.store.append(entry)

    def record_self_discovery(self, table: str, observation: str,
                              evidence: str):
        """
        Agent 自发现记录
        例：table="event_log", observation="2024年前的数据格式不同",
            evidence="pre-2024 rows have NULL in session_id"
        """
        entry = {
            "type": "self_discovery",
            "table": table,
            "observation": observation,
            "evidence": evidence,
            "confidence": 0.7,  # Agent 推断，中等置信度
            "created_at": datetime.now()
        }
        self.store.append(entry)

    def record_success_pattern(self, query: str, tables_used: list[str],
                               result_confirmed: bool):
        """
        成功模式记录
        当用户确认查询结果正确时，记录表组合和使用方式
        """
        ...
```

**去重与合并：**
- 同一张表的同一维度纠错，取最新一条（人类认知会变化）
- 同一观察多条记录，提高置信度
- 超过 90 天无引用的记录自动降权

---

## 三、Agent 推理循环

### 3.1 核心流程

```
用户输入: "上个月各渠道的新增注册用户数"

         ┌─────────────────────────────┐
         │  Step 1: 意图理解            │
         │  拆解为结构化分析需求          │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │  Step 2: 数据发现            │
         │  从六层上下文定位正确的表       │
         │  → 查 schema (L1)           │
         │  → 查历史关联 (L2)           │
         │  → 查专家描述 (L3)           │
         │  → 查代码推断 (L4)           │
         │  → 查组织知识 (L5)           │
         │  → 查历史记忆 (L6)           │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │  Step 3: 验证与比较          │
         │  "我选的表真的对吗？"          │
         │  → 比较候选表的语义           │
         │  → 检查数据范围是否匹配       │
         │  → 确认粒度是否正确           │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │  Step 4: 生成查询            │
         │  生成 SQL → 执行 → 检查结果   │
         └──────────┬──────────────────┘
                    ▼
         ┌─────────────────────────────┐
         │  Step 5: 结果验证            │
         │  → 行数是否合理？             │
         │  → 数值范围是否合理？         │
         │  → 与历史记忆是否矛盾？       │
         └──────────┬──────────────────┘
               ┌─────┴─────┐
               │  异常？     │
               ├─────────────┤
          Yes  │             │  No
               ▼             ▼
         ┌───────────┐ ┌───────────┐
         │ 自诊断修复  │ │ 返回结果   │
         │ → 重新分析  │ │ + 推理过程  │
         │ → 重新生成  │ │ + 可审计   │
         └───────────┘ └───────────┘
```

### 3.2 Step 2 上下文组装策略

**核心原则：少而精，不堆砌**

```python
class ContextAssembler:
    """
    上下文组装器：从六层中选择最相关的信息
    关键：不是每层都给全部信息，而是按查询相关性精准选择
    """

    def assemble(self, query: str, candidate_tables: list[str]) -> str:
        sections = []

        # L1: 候选表的 schema（精简版，只给列名和类型）
        for table in candidate_tables[:5]:  # 最多 5 张候选表
            schema = self.metadata.get_schema(table, compact=True)
            sections.append(f"## {table}\n{schema}")

        # L2: 候选表之间的高频 JOIN 模式（如果有）
        joins = self.query_inference.get_join_patterns(candidate_tables)
        if joins:
            sections.append(f"## 常见关联方式\n{self._format_joins(joins)}")

        # L3: 专家描述（只有候选表有的才给）
        expert = self.expert_descriptions.get(candidate_tables)
        if expert:
            sections.append(f"## 重要说明\n{expert}")

        # L4: 代码推断语义（候选表有的才给，只给关键字段）
        code_sem = self.code_analyzer.get_semantics(candidate_tables)
        if code_sem:
            sections.append(f"## 数据特征\n{code_sem}")

        # L5: 组织知识（按 query 语义检索，最多 2 条）
        org_knowledge = self.knowledge.search(query, top_k=2)
        if org_knowledge:
            sections.append(f"## 相关知识\n{org_knowledge}")

        # L6: 历史记忆（只有相关的纠错/发现）
        memory = self.memory.search(candidate_tables, query)
        if memory:
            sections.append(f"## 注意事项\n{memory}")

        return "\n\n".join(sections)

    def _format_joins(self, joins) -> str:
        """简洁的 JOIN 模式描述"""
        lines = []
        for j in joins[:5]:  # 最多 5 个模式
            lines.append(
                f"- {j['tables'][0]} {j['join_type']} JOIN {j['tables'][1]} "
                f"ON {j['join_condition']} (近30天使用 {j['frequency']} 次)"
            )
        return "\n".join(lines)
```

### 3.3 Step 3 验证逻辑（防止过度自信）

这是 Agent 质量的关键。必须强制 Agent 花时间验证，而不是直接选表就跑。

**Prompt 设计要点：**

```
在你确定要使用某张表之前，请执行以下检查：

1. 语义匹配度：这张表的内容是否精确回答了用户的问题？
   - 例：用户问"新增注册"，你是否选了包含历史注册数据的宽表？

2. 数据完整性：这张表是否缺少用户需要的维度？
   - 例：用户要按渠道分析，表里是否有渠道字段？

3. 粒度正确性：表的粒度是否与查询粒度匹配？
   - 例：用户要按天统计，表是月汇总级别的话需要换表

4. 时间范围：表的数据是否覆盖了用户要求的时间段？
   - 例：用户问上个月，但表的数据只到上周

5. 已知陷阱：是否有专家描述或历史记忆提示这张表有坑？

如果以上任何一点不确定，请：
- 列出你的候选表及其优劣势
- 询问用户确认，或者选择置信度最高的并说明风险
- 不要在不确定的情况下直接生成查询
```

### 3.4 Step 5 结果验证规则

```python
class ResultValidator:
    """
    查询结果的自动验证器
    """

    def validate(self, query: str, sql: str, result: pd.DataFrame) -> ValidationResult:
        checks = []

        # 1. 空结果检查
        if len(result) == 0:
            checks.append(Check(
                level="ERROR",
                message="查询返回 0 行",
                suggestion="可能选错了表或过滤条件过严，建议检查 WHERE 条件"
            ))

        # 2. 行数合理性
        expected_range = self._estimate_row_count(query)
        if len(result) > expected_range * 10:
            checks.append(Check(
                level="WARNING",
                message=f"返回 {len(result)} 行，远超预期 {expected_range}",
                suggestion="可能存在多对多 JOIN 导致的笛卡尔积"
            ))

        # 3. 数值范围检查
        for col in result.select_dtypes(include='number').columns:
            stats = result[col].describe()
            if stats['max'] > 0 and stats['min'] < 0:
                checks.append(Check(
                    level="WARNING",
                    message=f"列 {col} 同时包含正负值",
                    suggestion="检查是否有 NULL 被转为 0 或计算错误"
                ))

        # 4. NULL 比例检查
        for col in result.columns:
            null_ratio = result[col].isnull().mean()
            if null_ratio > 0.5:
                checks.append(Check(
                    level="WARNING",
                    message=f"列 {col} 有 {null_ratio:.0%} 为 NULL",
                    suggestion="可能 LEFT JOIN 丢失数据，检查关联条件"
                ))

        # 5. 与历史记忆对比
        memory_conflicts = self.memory.check_conflicts(query, result)
        if memory_conflicts:
            checks.append(Check(
                level="WARNING",
                message=f"与历史记录矛盾: {memory_conflicts}",
                suggestion="核实数据范围或表选择是否正确"
            ))

        return ValidationResult(checks=checks)

    def _estimate_row_count(self, query: str) -> int:
        """根据查询意图粗估预期行数"""
        # "各渠道" → 通常 3-20 行
        # "按天" → 通常 7-365 行
        # "每个用户" → 通常 1000+ 行
        ...
```

---

## 四、安全模型

### 4.1 设计原则：最简权限继承

不做花哨的 AI 安全对齐，用最朴素的权限模型：

```
┌────────────────────────────────────────────────┐
│  用户 Token                                      │
│  └── 用户身份 → 数据权限组                         │
│        └── 可读表列表 (user.readable_tables)       │
│        └── 可写表列表 (user.writable_tables)       │
│              └── Agent 只能访问这些表               │
└────────────────────────────────────────────────┘
```

### 4.2 实现方案

```python
class SecurityGuard:
    """
    安全守卫：在 SQL 执行前进行权限检查和改写
    """

    def check_and_rewrite(self, sql: str, user_token: str) -> str:
        user_perms = self.auth.get_permissions(user_token)

        # 1. 提取 SQL 中引用的所有表
        referenced_tables = self.sql_parser.extract_tables(sql)

        # 2. 检查读权限
        for table in referenced_tables:
            if table not in user_perms.readable:
                raise PermissionDenied(
                    f"用户无权访问表 {table}。"
                    f"请联系管理员申请权限。"
                )

        # 3. 检查是否包含写操作
        if self.sql_parser.has_write_operations(sql):
            # 所有写操作强制重定向到临时 schema
            sql = self._redirect_to_temp_schema(sql, user_token)

        # 4. 检查危险操作
        self._block_dangerous_operations(sql)

        # 5. 添加行数限制
        sql = self._add_row_limit(sql, max_rows=100000)

        return sql

    def _redirect_to_temp_schema(self, sql: str, user_token: str) -> str:
        """
        将 CREATE TABLE / INSERT INTO 的目标改为临时 schema
        例：INSERT INTO analytics.temp_results_{user_id}_...
        """
        temp_schema = f"temp_agent_{hashlib.md5(user_token).hexdigest()[:8]}"
        # 确保临时 schema 存在
        self.db.execute(f"CREATE SCHEMA IF NOT EXISTS {temp_schema}")
        # 替换目标表
        return sql  # 改写逻辑
```

### 4.3 安全规则清单

| 规则 | 实现 |
|------|------|
| 读权限继承 | Agent 只能查用户有权查的表 |
| 写操作隔离 | 强制写入临时 schema，定时清理（7天） |
| 行数限制 | SELECT 最多 10 万行，防止 OOM |
| 危险操作拦截 | 禁止 DROP、TRUNCATE、ALTER |
| 结果脱敏 | 自动检测身份证/手机号列，查询结果中 mask |
| 审计日志 | 每次查询记录：用户、SQL、表、时间、行数 |
| 可见性控制 | 只在私聊/个人界面使用，不在公共频道展示 |

---

## 五、评估体系

### 5.1 持续回归测试（Evals）

像单元测试一样持续评估 Agent 质量。

```python
class AgentEval:
    """
    评估集格式：
    {
        "query": "上个月各渠道的新增注册用户数",
        "expected_tables": ["user_registration", "channel_mapping"],
        "expected_sql_pattern": "GROUP BY channel",
        "golden_sql": "SELECT ...",
        "golden_result_checksum": "sha256:abc123..."
    }
    """

    def run_eval(self, eval_set: list[dict]) -> EvalReport:
        results = []
        for case in eval_set:
            # 1. 让 Agent 处理查询
            agent_output = self.agent.run(case["query"])

            # 2. 表选择评估
            table_match = self._eval_table_selection(
                agent_output.tables_used,
                case["expected_tables"]
            )

            # 3. SQL 语义评估（不是字符串匹配）
            sql_similarity = self._eval_sql_semantic(
                agent_output.sql,
                case["golden_sql"]
            )

            # 4. 结果数据评估
            result_match = self._eval_result_data(
                agent_output.result,
                case["golden_result_checksum"]
            )

            results.append({
                "case_id": case["id"],
                "table_selection": table_match,
                "sql_semantic": sql_similarity,
                "result_accuracy": result_match,
                "overall": table_match * 0.3 + sql_similarity * 0.3 + result_match * 0.4
            })

        return EvalReport(results=results)
```

### 5.2 评估维度

| 维度 | 权重 | 评估方法 | 优秀标准 |
|------|------|---------|---------|
| 表选择正确率 | 30% | 与黄金 SQL 引用的表对比 | > 90% |
| SQL 语义相似度 | 30% | AST 级别比较，非字符串匹配 | > 85% |
| 结果数据准确率 | 40% | 执行结果与黄金结果的数值对比 | > 95% |
| 错误自愈率 | 追踪 | Agent 自动修复错误的比率 | > 60% |
| 响应时间 | 监控 | 端到端延迟 | P95 < 30s |

### 5.3 评估集维护

```python
# 评估集来源：
# 1. 人工编写的黄金标准（覆盖核心场景）
# 2. 生产环境中用户确认正确的查询自动归入
# 3. Agent 犯错后被人工纠正的案例

class EvalSetManager:
    def add_from_production(self, query: str, sql: str,
                            result: pd.DataFrame, user_confirmed: bool):
        """从生产环境收集评估用例"""
        if not user_confirmed:
            return
        case = {
            "id": f"prod_{uuid4().hex[:8]}",
            "source": "production",
            "query": query,
            "golden_sql": sql,
            "golden_result_checksum": hashlib.sha256(
                result.to_csv().encode()
            ).hexdigest(),
            "added_at": datetime.now().isoformat()
        }
        self.eval_set.append(case)

    def add_from_failure(self, query: str, wrong_sql: str,
                         correct_sql: str, user_id: str):
        """从错误案例学习"""
        case = {
            "id": f"failure_{uuid4().hex[:8]}",
            "source": "user_correction",
            "query": query,
            "wrong_sql": wrong_sql,
            "golden_sql": correct_sql,
            "corrected_by": user_id,
            "added_at": datetime.now().isoformat()
        }
        self.eval_set.append(case)
```

---

## 六、Prompt 工程原则

### 6.1 反直觉发现：少即是多

OpenAI 团队评估发现：

| 做法 | 效果 | 原因 |
|------|------|------|
| 上下文越多越好 | ❌ 变差 | 噪声干扰推理 |
| Prompt 规定越细越好 | ❌ 变差 | 过度约束推向错误路径 |
| 暴露全部工具 | ❌ 变差 | Agent 选择困难 |
| 精简高层引导 | ✅ 最好 | 让模型自己推理 |

### 6.2 Prompt 模板设计

```python
AGENT_SYSTEM_PROMPT = """
你是一个数据分析助手。你的任务是将用户的自然语言问题转化为准确的 SQL 查询。

## 核心原则

1. 准确性优先于速度。如果不确定哪张表正确，先比较候选表再决定。
2. 永远不要在不确定的情况下执行查询。先验证，再执行。
3. 如果查询结果看起来不合理，主动诊断原因并告知用户。

## 可用数据源

{assembled_context}

## 你的职责

- 理解用户的分析意图
- 从可用数据源中选择正确的表
- 生成 SQL 并执行
- 验证结果的合理性
- 向用户清晰地展示结论

## 输出格式

1. 先简要说明你的分析思路
2. 展示推理过程（选择了哪些表，为什么）
3. 展示结果
4. 补充注意事项或局限性
"""

# 注意：不要在 prompt 中规定"必须使用 LEFT JOIN"、"GROUP BY 必须包含..."
# 这些细节约束会让模型走向错误路径
# 高层引导 + 让模型自主推理 = 更好的结果
```

### 6.3 工具设计原则

```
❌ 反模式：暴露 20+ 细粒度工具
   - search_by_table_name
   - search_by_column_name
   - get_table_schema
   - get_table_lineage
   - get_expert_notes
   - get_code_semantics
   - ... (Agent 选择困难，经常选错工具)

✅ 正确做法：合并为 2-3 个高层工具
   - search_tables(query, intent) → 返回候选表 + 摘要信息
   - analyze_data(query, tables) → 生成 SQL + 执行 + 验证
   - explain_result(sql, result) → 解释结果并标注风险
```

---

## 七、技术实现路线图

### Phase 1: 基础可用（4-6 周）

| 模块 | 交付物 | 优先级 |
|------|--------|--------|
| L1 元数据层 | Schema 自动采集 + 表血缘 | P0 |
| L2 查询推理层 | 历史 SQL 日志分析，提取 JOIN 模式 | P0 |
| Agent 基础循环 | 意图理解 → 表选择 → SQL 生成 → 执行 | P0 |
| 安全基础 | 权限继承 + 行数限制 + 审计日志 | P0 |

### Phase 2: 上下文增强（4-6 周）

| 模块 | 交付物 | 优先级 |
|------|--------|--------|
| L3 专家描述层 | 表/列说明 CRUD + Agent 辅助生成草稿 | P1 |
| L4 代码语义推断层 | ETL 代码爬取 + 自动语义推断 | P1 |
| L6 自学习记忆层 | 纠错记录 + 成功模式记录 | P1 |
| 结果验证器 | 空结果/行数/NULL/数值范围检查 | P1 |

### Phase 3: 高级能力（4-6 周）

| 模块 | 交付物 | 优先级 |
|------|--------|--------|
| L5 组织知识层 | 向量检索 + 内部文档接入 | P2 |
| 评估体系 | 黄金 SQL 集成 + 持续回归 | P2 |
| 错误自愈 | 常见 SQL 错误自动诊断修复 | P2 |
| 多轮对话 | 上下文保持 + 追问引导 | P2 |

### Phase 4: 规模化（持续）

| 模块 | 交付物 | 优先级 |
|------|--------|--------|
| 多用户隔离 | 用户级别的记忆和权限 | P2 |
| 评估集自动扩充 | 从生产环境收集用例 | P2 |
| 性能优化 | 上下文缓存 + 查询结果缓存 | P3 |
| 可观测性 | Agent 推理过程全链路追踪 | P3 |

---

## 八、技术选型建议

| 组件 | 建议方案 | 理由 |
|------|---------|------|
| LLM | GPT-4o / Claude 3.5 / GLM-5 | 复杂推理需要强模型，不是模型不够强而是数据治理要跟上 |
| 向量数据库 | pgvector / Milvus | L5 组织知识层的语义检索 |
| 元数据存储 | PostgreSQL | Schema + 血缘 + 专家描述统一存储 |
| SQL 解析 | sqlglot / moz-sql-parse | SQL AST 解析、安全改写、模式匹配 |
| 任务编排 | 自研 Agent Loop | 不建议用 LangChain，定制 loop 更灵活 |
| 前端交互 | Web + IM Bot (飞书/企微/Slack) | 同时支持专业分析场景和即时查询 |

---

## 九、关键指标与监控

### 9.1 产品指标

```
核心漏斗：
用户提问 → Agent 理解 → 选表正确 → SQL 正确 → 结果正确 → 用户满意
  100%      ~98%         ~85%        ~90%       ~95%       ~80%

各环节转化率是持续优化的重点
```

### 9.2 监控仪表盘

| 指标 | 计算方式 | 告警阈值 |
|------|---------|---------|
| 单轮完成率 | 用户一次提问得到满意结果的比例 | < 60% |
| 错误自愈率 | Agent 自动修复错误的比例 | < 50% |
| P95 响应时间 | 端到端延迟 | > 45s |
| 上下文命中率 | 六层上下文被引用的比例 | < 30% |
| 日活用户数 | 每日使用 Agent 的独立用户 | < 预期的 50% |

---

## 十、反直觉教训清单

这些是 OpenAI 实际踩坑后总结的，最容易犯的错：

1. **工具不是越多越好** → 精简到 2-3 个高层工具
2. **上下文不是越多越好** → 精选最相关的 2-3 条
3. **Prompt 不是越细越好** → 高层引导，让模型自己推理
4. **评估不要用字符串匹配** → SQL AST 语义比较 + 结果数据对比
5. **安全不要搞花哨的 AI 对齐** → 权限继承 + 写隔离 + 审计日志
6. **代码 > Schema** → 表的真正含义活在创建它的代码里
7. **让 Agent 多花时间验证** → 过度自信是最大质量杀手
8. **数据治理 > 模型能力** → 模型再强，面对混乱数据也白搭

---

## 附录 A：完整 Prompt 模板

```python
FULL_AGENT_PROMPT = """
## 角色
你是一个企业级数据分析助手，帮助用户通过自然语言查询公司数据。

## 核心原则
1. 准确性 > 速度。宁可多花 10 秒验证，也不要给出错误结果
2. 不确定就问。宁可向用户确认，也不要在不确定时猜测
3. 透明。每一步推理过程都展示给用户

## 可用数据
{context}

## 输出格式
你的每次回复必须包含：

### 1. 分析思路（2-3 句话）
简要说明你打算怎么分析这个问题

### 2. 数据选择
列出你打算使用的表，以及选择理由

### 3. 查询结果
以表格形式展示结果

### 4. 注意事项
标注数据的局限性、潜在风险、需要关注的异常
"""
```

## 附录 B：L4 代码语义推断的 AST 匹配规则

```python
class SQLSemanticPatterns:
    """
    常见的 SQL 语义推断规则
    """

    patterns = {
        "granularity": {
            "GROUP BY user_id, DATE(created_at)": "per_user_per_day",
            "GROUP BY user_id, region": "per_user_per_region",
            "GROUP BY DATE(created_at)": "per_day",
            "no GROUP BY": "row_level",
        },
        "update_frequency": {
            "schedule_interval='@daily'": "daily",
            "schedule_interval='@hourly'": "hourly",
            "schedule_interval='0 6 * * 1-5'": "weekday_morning",
        },
        "exclusion_patterns": {
            "WHERE status != 'deleted'": "excludes_deleted_records",
            "WHERE is_test = false": "excludes_test_data",
            "WHERE user_type = 'real'": "real_users_only",
        },
        "join_semantics": {
            "LEFT JOIN": "includes_unmatched_left_rows",
            "INNER JOIN": "only_matching_rows",
            "RIGHT JOIN": "includes_unmatched_right_rows",
        },
        "deduplication": {
            "ROW_NUMBER() OVER (PARTITION BY": "row_number_dedup",
            "DISTINCT": "simple_dedup",
            "GROUP BY": "group_by_dedup",
        }
    }
```

---

*文档版本: v1.0*
*基于: OpenAI "Inside Our In-House Data Agent" (2026-01-29)*
*适用场景: 企业级数据分析产品 / BI 智能助手 / Text-to-SQL 系统*
