---
name: doc-to-ppt
description: 将 PDF、Word、PPT 文件转换为结构化 PPT。读取多个文档文件，提取核心内容，提炼要点，生成专业的 PowerPoint 演示文稿。可参考用户提供的 PPT 模板格式。触发场景：(1) 用户发送 PDF/Word/PPT 文件要求生成 PPT (2) 用户要求整理文档内容并输出演示文稿 (3) 用户说"帮我做个PPT"、"把这份文档转成PPT"。
---

# Doc-to-PPT

将多个文档文件转换为结构化 PPT 演示文稿。

## Quick Start

```bash
# 1. 提取文件内容
python scripts/extract_content.py /path/to/file.pdf

# 2. 生成 PPT
python scripts/generate_ppt.py --output output.pptx --title "演示标题" --slides '[{"title":"章节1","content":["要点1","要点2"]}]'

# 3. 使用模板
python scripts/generate_ppt.py --output output.pptx --template /path/to/template.pptx --title "演示标题" --slides slides.json
```

## 工作流程

### 1. 接收文件

用户可发送多个文件（PDF、Word、PPT），系统自动识别并处理。

### 2. 提取内容

使用 `scripts/extract_content.py` 提取每个文件的文本内容：

```bash
python scripts/extract_content.py document.pdf
python scripts/extract_content.py document.docx
python scripts/extract_content.py slides.pptx
```

输出格式：
```json
{
  "success": true,
  "text": "提取的文本内容...",
  "pages": 10,
  "file": "document.pdf",
  "type": ".pdf"
}
```

### 3. 提炼要点

阅读提取的文本内容，按照以下原则提炼核心要点：

**提炼原则：**
- 每个主题生成 1 张幻灯片
- 每张幻灯片 3-5 个要点
- 每个要点 1-2 句话，简洁有力
- 保留关键数据、结论、行动建议
- 去除冗余、重复、过渡性内容

**结构建议：**
- 封面：标题 + 副标题
- 概述：背景、目的、范围
- 核心内容：分章节展示
- 总结：关键结论 + 下一步

### 4. 生成 PPT

使用 `scripts/generate_ppt.py` 生成演示文稿：

**输入格式：**
```json
[
  {
    "title": "章节标题",
    "content": ["要点一", "要点二", "要点三"]
  },
  {
    "title": "下一章节",
    "content": ["要点一", "要点二"]
  }
]
```

**命令示例：**
```bash
# 从 JSON 文件生成
python scripts/generate_ppt.py -o output.pptx -t "演示标题" --slides slides.json

# 使用模板（保持格式风格）
python scripts/generate_ppt.py -o output.pptx -t "演示标题" --template user_template.pptx --slides slides.json

# 管道输入
echo '[{"title":"第一章","content":["要点1","要点2"]}]' | python scripts/generate_ppt.py -o output.pptx -t "标题"
```

### 5. 参考用户模板

如果用户提供了参考 PPT：
1. 先用 `extract_content.py` 提取模板内容
2. 分析模板的结构、章节划分、内容密度
3. 按相似风格组织新内容

## 依赖安装

```bash
pip install pdfplumber python-docx python-pptx
```

或使用 PyPDF2 作为 PDF 备选：
```bash
pip install PyPDF2 python-docx python-pptx
```

## 最佳实践

**内容提炼：**
- 先通读全文，理解整体结构
- 标记关键概念、数据、结论
- 按"是什么-为什么-怎么做"组织
- 使用金字塔原理：结论先行

**PPT 设计：**
- 标题简洁有力（≤10字）
- 要点控制在 3-5 个
- 避免大段文字，用关键词
- 数据用对比、趋势呈现

**质量检查：**
- 确保逻辑连贯，章节衔接自然
- 检查关键信息是否遗漏
- 确认幻灯片数量合理（一般 10-20 页）
