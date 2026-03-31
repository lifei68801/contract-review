---
name: cogview-image
description: 使用智谱 CogView 模型生成图片。当用户要求画图、生成图片、AI作画时使用。
---

# CogView 图像生成

使用智谱 AI 的 CogView 模型生成图片。

## 快速使用

```bash
# 基础用法
python3 ~/.openclaw/workspace/skills/cogview-image/scripts/generate.py "一只可爱的橘猫"

# 指定尺寸
python3 ~/.openclaw/workspace/skills/cogview-image/scripts/generate.py "一只可爱的橘猫" --size 768x768

# 指定输出路径
python3 ~/.openclaw/workspace/skills/cogview-image/scripts/generate.py "一只可爱的橘猫" -o /tmp/cat.png
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `prompt` | 图片描述（必填） | - |
| `--size` | 图片尺寸: 768x768, 1024x1024, 1024x768, 768x1024 | 1024x1024 |
| `-o, --output` | 输出路径 | /tmp/cogview_{timestamp}.png |
| `--model` | 模型: cogview-3, cogview-3-plus | cogview-3-plus |

## 使用流程

1. 用户说"画一张..."、"生成图片..."、"帮我画..."
2. 调用脚本生成图片
3. 使用 `<qqimg>` 标签发送给用户

## 示例

**用户**: 帮我画一只可爱的柴犬

**操作**:
```bash
python3 ~/.openclaw/workspace/skills/cogview-image/scripts/generate.py "一只可爱的柴犬，毛茸茸，表情憨厚" -o /tmp/shiba.png
```

**回复**:
```
这是你要的柴犬图！

<qqimg>/tmp/shiba.png</qqimg>
```

## 注意事项

- 图片 URL 有效期约 6 小时，生成后请立即使用
- 生成的图片带有水印
- 复杂场景建议详细描述，效果更好
