# 周摘要 - 2026年第12周

## 每日要点
- 周一（3/16）：doc2slides 数势科技包河区方案 PPT 多次迭代，修复布局/图表匹配，评分达100分并发邮件
- 周二（3/17）：GTC 2026 爆文输出、Kimi Attention Residuals 论文公众号文章发Notion、PPT 生成继续调优（v3-v12迭代）
- 周三（3/18）：12000字论文解读、PPT HTML 布局问题诊断（只有文字缺图表）、LLM 模型配置路径修复、Twitter 文案改写
- 周四（3/19）：低活跃日，无超过阈值会话
- 周五（3/20）：doc2slides 重大升级——从规则匹配改为 LLM 智能匹配、布局自适应、配色灵活化；安装 chartgen-skill 和锐捷 VPN；技能发布 ClawHub
- 周六（3/21）：doc2slides v2.8.0 发布，修复 LLM"偷懒"空白页问题，增加用户自定义指令支持；ClawHub suspicious 排查；ChartGen API Key 过期待更新
- 周日（3/22）：doc2slides v3.4.1 发布，修复 fallback 模板缩进 bug；创建 GitHub 仓库 lifei68801/opt；context-compression 技能代码审查 7 项修复并通过 gstack 10/10

## 重要决策汇总
1. **doc2slides 架构升级**：规则匹配 → LLM 智能匹配，从模板驱动转为 AI 原生生成
2. **doc2slides 用户交互改进**：增加自定义指令输入，不再自动触发生成
3. **GitHub 仓库 opt 创建**：托管 Agent 角色和技能代码
4. **ClawHub 账号被标记**：所有新发布均被安全扫描拦截，确认为账号级别标记而非内容问题
5. **context-compression 技能质量提升**：修复递归防护、消息顺序、安全写入等 7 个问题

## 用户偏好更新
- PPT 质量要求高，不接受布局简单、内容空白的生成结果
- 偏好 LLM 智能方案而非规则兜底
- 技能发布前需完整测试和代码审查

---
*详细见 daily/ 目录*
