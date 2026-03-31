# Implementation Examples

基于 Memento-Skills 源码的核心实现代码片段，可直接参考或改造。

## 1. Skill 加载与解析

```python
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

class Skill(BaseModel):
    name: str
    description: str
    content: str                    # SKILL.md 全文
    dependencies: list[str] = []
    references: dict[str, str] = {} # references/ 目录文件
    source_dir: Optional[str] = None
    allowed_tools: list[str] = []   # 工具白名单
    required_keys: list[str] = []   # 必需的 API Key

def load_skill_from_dir(skill_dir: Path) -> Skill:
    """从目录加载 Skill"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Missing SKILL.md in {skill_dir}")

    content = skill_md.read_text(encoding="utf-8")

    # 解析 YAML frontmatter
    name = skill_dir.name
    description = ""
    deps = []
    if content.startswith("---"):
        end = content.index("---", 3)
        header = content[3:end]
        for line in header.split("\n"):
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("dependencies:"):
                # 解析列表
                pass
        content = content[end + 3:].strip()

    # 加载 references
    refs = {}
    ref_dir = skill_dir / "references"
    if ref_dir.exists():
        for f in ref_dir.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                refs[f.stem] = f.read_text(encoding="utf-8")

    return Skill(
        name=name,
        description=description,
        content=content,
        references=refs,
        source_dir=str(skill_dir),
    )
```

## 2. 向量召回（sqlite-vec 实现）

```python
import sqlite3
import threading
import numpy as np

class EmbeddingRecall:
    def __init__(self, db_path: str, dim: int = 1536):
        self._db_path = db_path
        self._dim = dim
        self._lock = threading.Lock()
        self._conn = self._init_db()

    def _init_db(self) -> sqlite3.Connection:
        import sqlite_vec
        conn = sqlite3.connect(self._db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS skill_embeddings
            USING vec0(
                skill_name TEXT PRIMARY KEY,
                embedding float[{self._dim}] distance_metric=cosine
            )
        """)
        conn.commit()
        return conn

    def upsert(self, skill_name: str, embedding: list[float]):
        vec_bytes = np.array(embedding, dtype=np.float32).tobytes()
        with self._lock:
            self._conn.execute(
                "DELETE FROM skill_embeddings WHERE skill_name = ?",
                (skill_name,)
            )
            self._conn.execute(
                "INSERT INTO skill_embeddings (skill_name, embedding) VALUES (?, ?)",
                (skill_name, vec_bytes)
            )
            self._conn.commit()

    def search(self, query_embedding: list[float], k: int = 10) -> list[tuple[str, float]]:
        vec_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
        rows = self._conn.execute("""
            SELECT skill_name, distance
            FROM skill_embeddings
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
        """, (vec_bytes, k)).fetchall()
        return [(name, max(0.0, 1.0 - dist)) for name, dist in rows]
```

## 3. 多路召回 + 混合排序

```python
from dataclasses import dataclass

@dataclass
class RecallResult:
    skill_name: str
    score: float
    source: str  # "keyword" | "embedding"

def multi_recall(
    query: str,
    skills: dict[str, Skill],
    embedding_recall: EmbeddingRecall,
    embedding_client,  # OpenAI 兼容 API
    k: int = 10,
    keyword_weight: float = 0.4,
    embedding_weight: float = 0.6,
) -> list[RecallResult]:
    """多路召回 + RRF 融合排序"""

    # 1. 关键词召回
    keyword_results = keyword_search(query, skills)

    # 2. 向量召回
    query_vec = embedding_client.embed(query)
    embedding_results = embedding_recall.search(query_vec, k)

    # 3. RRF 融合
    scores: dict[str, float] = {}
    for rank, (name, _) in enumerate(keyword_results):
        rrf = 1.0 / (rank + 1 + 60)  # k=60 常数
        scores[name] = scores.get(name, 0) + keyword_weight * rrf

    for rank, (name, sim) in enumerate(embedding_results):
        rrf = 1.0 / (rank + 1 + 60)
        scores[name] = scores.get(name, 0) + embedding_weight * rrf

    # 排序返回
    return sorted(
        [RecallResult(name, score, "hybrid") for name, score in scores.items()],
        key=lambda x: x.score,
        reverse=True,
    )[:k]

def keyword_search(query: str, skills: dict[str, Skill], k: int = 10) -> list[tuple[str, float]]:
    """简单关键词匹配"""
    query_lower = query.lower()
    results = []
    for name, skill in skills.items():
        text = f"{name} {skill.description}".lower()
        # 分词匹配
        hits = sum(1 for word in query_lower.split() if word in text)
        if hits > 0:
            score = hits / max(len(query_lower.split()), 1)
            results.append((name, score))
    return sorted(results, key=lambda x: x[1], reverse=True)[:k]
```

## 4. Prompt 构建模板

```python
SKILL_EXECUTE_PROMPT = """
## Skill: {skill_name}

{description}

### Instructions

{skill_content}

{scripts_section}

## Available Tools

{tools_summary}

## Environment

- Platform: {platform_info}
- Current time: {current_datetime}
- Current year: {current_year}
- Output directory: {output_dir}

{references_section}

## Task

{query}

Instructions:
- Read the skill instructions carefully
- Use the available tools when needed
- Save output files to the output directory
- If the query is not relevant to this skill, respond with [NOT_RELEVANT] followed by a brief explanation
"""
```

## 5. 工具白名单过滤

```python
def filter_tools_by_allowed_list(all_tools: list[dict], allowed: list[str]) -> list[dict]:
    """根据 allowed_tools 过滤可用工具"""
    if not allowed:
        return all_tools  # 空白名单 = 不限制
    return [t for t in all_tools if t.get("name", "") in allowed]
```

## 6. 执行器核心逻辑（简化版）

```python
class SkillExecutor:
    async def execute(self, skill: Skill, query: str) -> SkillExecutionOutcome:
        # 1. 渐进式披露：选择相关 references
        refs = self._select_relevant_references(skill.references, query)

        # 2. 构建 prompt
        prompt = self._build_prompt(skill, query, refs)

        # 3. LLM 调用
        response = await self._llm.chat(messages=[{"role": "user", "content": prompt}])

        # 4. 处理响应
        if response.has_tool_calls:
            return await self._execute_tool_calls(skill, response.tool_calls)
        elif response.text.startswith("[NOT_RELEVANT]"):
            return SkillExecutionOutcome(success=False, error="not_relevant")
        else:
            return SkillExecutionOutcome(success=True, result=response.text)

    def _select_relevant_references(self, refs: dict, query: str) -> dict:
        """只选择与 query 相关的 references，每个截断 2000 字符"""
        if not refs:
            return {}
        # 简单实现：关键词匹配
        query_words = set(query.lower().split())
        selected = {}
        for name, content in refs.items():
            name_words = set(name.lower().replace("-", " ").split())
            if query_words & name_words:
                selected[name] = content[:2000]
        return selected
```

## 7. Gateway 契约实现

```python
from typing import Protocol

class SkillGateway(Protocol):
    """Agent 层依赖的唯一接口"""
    def discover(self) -> list[dict]: ...
    async def search(self, query: str, k: int = 5) -> list[dict]: ...
    async def execute(self, skill_name: str, params: dict) -> dict: ...

class SkillProvider:
    """Gateway 的默认实现"""
    def __init__(self, skills: dict[str, Skill], recall: EmbeddingRecall):
        self._skills = skills
        self._recall = recall

    def discover(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]

    async def search(self, query: str, k: int = 5) -> list[dict]:
        results = multi_recall(query, self._skills, self._recall, ...)
        return [{"name": r.skill_name, "score": r.score} for r in results]

    async def execute(self, skill_name: str, params: dict) -> dict:
        skill = self._skills.get(skill_name)
        if not skill:
            return {"ok": False, "status": "failed", "error_code": "SKILL_NOT_FOUND"}
        outcome = await self._executor.execute(skill, params.get("request", ""))
        return {
            "ok": outcome.success,
            "status": "success" if outcome.success else "failed",
            "output": outcome.result,
            "artifacts": outcome.artifacts,
        }
```
