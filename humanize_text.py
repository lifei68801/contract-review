#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def humanize_text(text):
    """
    去除文本中的AI生成痕迹，使其更自然
    """
    
    # 1. 删除填充短语
    text = re.sub(r'此外，', '', text)
    text = re.sub(r'基于大模型的', '', text)
    text = re.sub(r'智能代码审查工具', '', text)
    text = re.sub(r'自动检测', '', text)
    
    # 2. 删除过度强调意义的词汇
    text = re.sub(r'基于大模型的', '', text)
    text = re.sub(r'智能代码审查工具', '', text)
    text = re.sub(r'自动检测代码质量问题、安全漏洞和最佳实践违反情况', '', text)
    
    # 3. 简化安装方法描述
    text = re.sub(r'安装方法：', '安装：', text)
    text = re.sub(r'```bash\nclawhub install ai-code-review\n```', '```bash\nclawhub install ai-code-review\n```', text)
    
    # 4. 简化使用方法
    text = re.sub(r'使用方法：', '怎么用：', text)
    text = re.sub(r'1. 支持多种编程语言（Python、JavaScript、Java、Go、Rust等）', '支持多种语言（Python、JS、Java、Go、Rust等）', text)
    text = re.sub(r'2. 可以集成到CI/CD流程中', '能接入CI/CD流程', text)
    text = re.sub(r'3. 支持实时代码审查和批量文件审查', '支持实时和批量审查', text)
    text = re.sub(r'4. 提供详细的改进建议和最佳实践指导', '给具体改进建议', text)
    
    # 5. 简化适用场景
    text = re.sub(r'适用场景：', '适合谁用：', text)
    text = re.sub(r'- 代码质量检查和优化', '- 检查代码质量', text)
    text = re.sub(r'- 安全漏洞检测', '- 找安全漏洞', text)
    text = re.sub(r'- 代码规范统一', '- 统一代码风格', text)
    text = re.sub(r'- 团队代码审查自动化', '- 自动化团队审查', text)
    text = re.sub(r'- 学习最佳实践', '- 学习好代码写法', text)
    
    # 6. 删除过度宣传性语言
    text = re.sub(r'AI Code Review - ', '', text)
    
    # 7. 简化句子结构
    text = re.sub(r'，自动检测代码质量问题、安全漏洞和最佳实践违反情况。', '。', text)
    
    return text

# 原始文本
original_text = """AI Code Review - 基于大模型的智能代码审查工具，自动检测代码质量问题、安全漏洞和最佳实践违反情况。

安装方法：
```bash
clawhub install ai-code-review
```

使用方法：
1. 支持多种编程语言（Python、JavaScript、Java、Go、Rust等）
2. 可以集成到CI/CD流程中
3. 支持实时代码审查和批量文件审查
4. 提供详细的改进建议和最佳实践指导

适用场景：
- 代码质量检查和优化
- 安全漏洞检测
- 代码规范统一
- 团队代码审查自动化
- 学习最佳实践"""

# 处理文本
humanized_text = humanize_text(original_text)

print("=== 去除AI痕迹后的文本 ===")
print(humanized_text)