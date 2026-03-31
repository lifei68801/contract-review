# Data Flow & State Machine

Memento-Skills 的完整数据流和状态转换。

## 完整请求生命周期

```
[用户输入 Query]
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Phase 1: 技能发现 (Skill Discovery)              │
│                                                   │
│  Gateway.discover()                               │
│  → 扫描所有已注册 skill 的 metadata               │
│  → 返回 SkillManifest 列表                        │
└───────┬─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Phase 2: 技能检索 (Skill Retrieval)              │
│                                                   │
│  Gateway.search(query)                            │
│  ├─ 关键词召回 → keyword_matches                  │
│  ├─ 向量召回 → embedding_matches                  │
│  ├─ RRF 融合排序 → ranked_candidates              │
│  └─ 返回 Top-K SkillManifest                      │
└───────┬─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Phase 3: 前置校验 (Pre-flight Checks)            │
│                                                   │
│  Provider 校验链：                                │
│  ├─ skill_name 存在性检查                         │
│  ├─ required_keys 环境变量检查                    │
│  ├─ dependencies 可用性检查                       │
│  ├─ allowed_tools 策略检查                        │
│  └─ 任一失败 → SkillExecutionResponse(FAILED)     │
└───────┬─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Phase 4: 执行路由 (Execution Routing)            │
│                                                   │
│  判断 execution_mode：                            │
│  ├─ Knowledge → Phase 5A                         │
│  └─ Playbook → Phase 5B                          │
└───────┬─────────────────────────────────────────┘
        │
   ┌────┴────────────────────────────┐
   ▼                                 ▼
┌──────────────┐             ┌──────────────────┐
│  Phase 5A    │             │  Phase 5B         │
│  Knowledge   │             │  Playbook          │
│              │             │                    │
│ LLM 读取     │             │ 1. 列出可用脚本    │
│ SKILL.md     │             │ 2. 构建 prompt     │
│ + refs       │             │    (含脚本列表)    │
│              │             │ 3. LLM 调用        │
│ LLM 返回：   │             │ 4. tool_calls?     │
│ - 文本答案   │             │    ├─ 是 → 逐个    │
│ - tool_calls │             │    │   执行工具    │
│ - NOT_RELEV  │             │    │   ├─ 策略检查 │
│              │             │    │   └─ 沙箱执行 │
│              │             │    └─ 否 → 文本    │
│              │             │ 5. fallback 处理   │
└──────┬───────┘             └────────┬──────────┘
       │                              │
       └──────────────┬───────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  Phase 6: 结果封装 (Response Packaging)           │
│                                                   │
│  SkillExecutionOutcome → SkillExecutionResponse   │
│  ├─ ok / status / error_code                      │
│  ├─ summary (LLM 生成的结果摘要)                  │
│  ├─ output (主输出)                               │
│  ├─ artifacts (生成的文件列表)                     │
│  └─ diagnostics (执行诊断)                        │
└─────────────────────────────────────────────────┘
```

## 状态机

```
                  ┌──────────────┐
                  │   IDLE       │
                  └──────┬───────┘
                         │ search(query)
                         ▼
                  ┌──────────────┐
            ┌────▶│  RETRIEVING  │
            │     └──────┬───────┘
            │            │ found candidates
            │            ▼
            │     ┌──────────────┐
            │     │  VALIDATING  │◄─────┐
            │     └──────┬───────┘      │
            │            │ pass         │
            │            ▼              │
            │     ┌──────────────┐      │
            │     │  ROUTING     │      │
            │     └──────┬───────┘      │
            │            │              │
            │     ┌──────┴──────┐      │
            │     ▼             ▼      │
            │  ┌────────┐  ┌────────┐  │
            │  │KNOWLEDGE│ │PLAYBOOK│  │
            │  └───┬────┘  └───┬────┘  │
            │      │           │       │
            │      └─────┬─────┘       │
            │            ▼             │
            │     ┌──────────────┐      │
            │     │  EXECUTING   │──────┘
            │     └──────┬───────┘  (tool_call loop)
            │            │
            │     ┌──────┴──────┐
            │     ▼             ▼
            │  ┌────────┐  ┌────────┐
            │  │SUCCESS │  │FAILED  │──────▶ NOT_RELEVANT
            │  └───┬────┘  └───┬────┘
            │      │           │
            │      └─────┬─────┘
            │            ▼
            │     ┌──────────────┐
            └─────│  RESPONDING  │
                  └──────┬───────┘
                         ▼
                  ┌──────────────┐
                  │   DONE       │
                  └──────────────┘

failed states:
- KEY_MISSING → required API key 不存在
- DEPENDENCY_MISSING → pip install 失败
- POLICY_BLOCKED → 策略拒绝
- TIMEOUT → 执行超时
- EXECUTION_ERROR → 代码运行异常
```

## 错误恢复策略

| 错误类型 | 恢复策略 |
|---------|---------|
| INPUT_REQUIRED | 返回提示让用户补充输入 |
| INPUT_INVALID | 返回错误说明 + 示例 |
| KEY_MISSING | 明确告知缺少哪个 Key |
| DEPENDENCY_ERROR | 自动 pip install，失败则降级 |
| POLICY_BLOCKED | 返回被拦截原因 |
| TIMEOUT | 返回已生成的部分结果 |
| EXECUTION_ERROR | 返回错误堆栈 + 建议 |
| NOT_RELEVANT | 尝试下一个候选 skill |

## 技能生命周期

```
[安装] ──▶ [加载] ──▶ [索引] ──▶ [就绪]
                                    │
                              ┌─────┴─────┐
                              ▼           ▼
                           [检索]      [更新]
                              │           │
                              ▼           ▼
                           [执行] ◀── [重新索引]
                              │
                         ┌────┴────┐
                         ▼         ▼
                      [成功]    [失败]
                         │         │
                         ▼         ▼
                      [归档]    [重试/降级]
```
