#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

def humanize_text(text):
    """
    去除文本中的AI生成痕迹，使其更自然
    """
    # 1. 删除填充短语
    text = re.sub(r'为了实现这一目标', '为了实现这一点', text)
    text = re.sub(r'由于下雨的事实', '因为下雨', text)
    text = re.sub(r'在这个时间点', '现在', text)
    text = re.sub(r'在您需要帮助的情况下', '如果您需要帮助', text)
    text = re.sub(r'系统具有处理的能力', '系统可以处理', text)
    text = re.sub(r'值得注意的是数据显示', '数据显示', text)
    
    # 2. 删除过度强调意义的词汇
    text = re.sub(r'标志着.*的关键时刻', '成立于', text)
    text = re.sub(r'是.*的体现/证明/提醒', '是', text)
    text = re.sub(r'凸显/强调/彰显了其重要性/意义', '表明', text)
    text = re.sub(r'反映了更广泛的', '涉及', text)
    text = re.sub(r'象征着其持续的/永恒的/持久的', '长期的', text)
    
    # 3. 删除以-ing结尾的肤浅分析
    text = re.sub(r'突出/强调/彰显.*、确保.*、反映/象征.*、为.*做出贡献、培养/促进.*、涵盖.*、展示.*', '', text)
    
    # 4. 删除宣传和广告式语言
    text = re.sub(r'拥有（夸张用法）', '有', text)
    text = re.sub(r'充满活力的', '活跃的', text)
    text = re.sub(r'丰富的（比喻）', '多样的', text)
    text = re.sub(r'深刻的', '深入的', text)
    text = re.sub(r'增强其', '改善', text)
    text = re.sub(r'体现', '显示', text)
    text = re.sub(r'致力于', '专注于', text)
    text = re.sub(r'自然之美', '自然环境', text)
    text = re.sub(r'坐落于', '位于', text)
    text = re.sub(r'位于.*的中心', '主要位于', text)
    text = re.sub(r'开创性的（比喻）', '新的', text)
    text = re.sub(r'著名的', '知名的', text)
    text = re.sub(r'令人叹为观止的', '令人印象深刻的', text)
    text = re.sub(r'必游之地', '值得游览的地方', text)
    text = re.sub(r'迷人的', '有吸引力的', text)
    
    # 5. 删除模糊归因
    text = re.sub(r'行业报告显示', '报告显示', text)
    text = re.sub(r'观察者指出', '观察发现', text)
    text = re.sub(r'专家认为', '研究表明', text)
    text = re.sub(r'一些批评者认为', '批评者认为', text)
    text = re.sub(r'多个来源/出版物', '多个来源', text)
    
    # 6. 删除提纲式的"挑战与未来展望"部分
    text = re.sub(r'尽管其.*面临若干挑战.*', '尽管面临挑战', text)
    text = re.sub(r'尽管存在这些挑战', '尽管如此', text)
    text = re.sub(r'挑战与遗产', '挑战', text)
    text = re.sub(r'未来展望', '未来', text)
    
    # 7. 删除过度使用的"AI词汇"
    text = re.sub(r'此外', '而且', text)
    text = re.sub(r'与.*保持一致', '符合', text)
    text = re.sub(r'至关重要', '很重要', text)
    text = re.sub(r'深入探讨', '详细讨论', text)
    text = re.sub(r'强调', '指出', text)
    text = re.sub(r'持久的', '长期的', text)
    text = re.sub(r'增强', '改善', text)
    text = re.sub(r'培养', '发展', text)
    text = re.sub(r'获得', '得到', text)
    text = re.sub(r'突出（动词）', '强调', text)
    text = re.sub(r'相互作用', '影响', text)
    text = re.sub(r'复杂/复杂性', '复杂', text)
    text = re.sub(r'关键（形容词）', '重要', text)
    text = re.sub(r'格局（抽象名词）', '情况', text)
    text = re.sub(r'关键性的', '重要的', text)
    text = re.sub(r'展示', '显示', text)
    text = re.sub(r'织锦（抽象名词）', '复杂情况', text)
    text = re.sub(r'证明', '表明', text)
    text = re.sub(r'强调（动词）', '指出', text)
    text = re.sub(r'宝贵的', '有价值的', text)
    text = re.sub(r'充满活力的', '活跃的', text)
    
    # 8. 避免使用"是"（系动词回避）
    text = re.sub(r'作为/代表/标志着/充当 \[一个\]', '是', text)
    text = re.sub(r'拥有/设有/提供 \[一个\]', '有', text)
    
    # 9. 删除否定式排比
    text = re.sub(r'这不仅仅.*而是.*', '不仅是', text)
    text = re.sub(r'不仅.*而且.*', '不仅', text)
    
    # 10. 删除三段式法则
    text = re.sub(r'包括.*、.*和.*', '包括多个方面', text)
    text = re.sub(r'可以期待.*、.*和.*', '可以期待', text)
    
    # 11. 刻意换词（同义词循环）
    text = re.sub(r'主人公面临许多挑战。主要角色必须克服障碍。中心人物最终获得胜利。', '主人公面临挑战并最终获胜', text)
    
    # 12. 删除虚假范围
    text = re.sub(r'从.*到.*', '在范围内', text)
    
    # 13. 删除破折号过度使用
    text = re.sub(r'——', '，', text)
    
    # 14. 删除粗体过度使用
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # 15. 删除内联标题垂直列表
    text = re.sub(r'- \*\*.*：\*\*', '- ', text)
    
    # 16. 删除标题中的标题大写
    text = re.sub(r'## (.*)', r'## \1', text)
    
    # 17. 删除表情符号
    text = re.sub(r'[🚀💡✅🔥]', '', text)
    
    # 18. 删除弯引号
    text = re.sub(r'""', '"', text)
    
    # 19. 删除协作交流痕迹
    text = re.sub(r'希望这对您有帮助', '', text)
    text = re.sub(r'如果您想让我扩展任何部分，请告诉我', '', text)
    
    # 20. 删除知识截止日期免责声明
    text = re.sub(r'截至.*', '', text)
    text = re.sub(r'根据我最后的训练更新', '', text)
    text = re.sub(r'虽然具体细节有限/ scarce.*', '', text)
    text = re.sub(r'基于可用信息.*', '', text)
    
    # 21. 删除谄媚/卑躬屈膝的语气
    text = re.sub(r'好问题！', '', text)
    text = re.sub(r'您说得完全正确', '你说得对', text)
    text = re.sub(r'这是一个.*的好观点', '这是个好观点', text)
    
    # 22. 删除填充词和回避
    text = re.sub(r'可以潜在地可能被认为', '可能', text)
    text = re.sub(r'该政策可能会对结果产生一些影响', '该政策可能影响结果', text)
    
    # 23. 删除通用积极结论
    text = re.sub(r'未来看起来光明', '未来有前景', text)
    text = re.sub(r'激动人心的时代即将到来', '新阶段即将开始', text)
    text = re.sub(r'继续追求卓越的旅程', '继续发展', text)
    text = re.sub(r'向正确方向迈出的重要一步', '重要进展', text)
    
    # 24. 简化复杂的句子结构
    text = re.sub(r'AI公司正在疯狂抓取整个互联网的内容，用来训练他们的AI模型。', 'AI公司大规模抓取互联网内容训练AI模型。', text)
    text = re.sub(r'Miasma就是为了反击而生的！', 'Miasma就是为了反击AI爬虫而生的工具。', text)
    text = re.sub(r'启动服务器，将恶意流量引向它。', '启动服务器，把恶意流量引向它。', text)
    text = re.sub(r'Miasma会从毒泉中发送有毒的训练数据，加上多个自引用链接。', 'Miasma发送有毒训练数据和自引用链接。', text)
    text = re.sub(r'这是为那些垃圾机器准备的无限自助餐。', '这能有效对付AI爬虫。', text)
    
    # 25. 删除过度修饰
    text = re.sub(r'非常', '很', text)
    text = re.sub(r'极其', '非常', text)
    text = re.sub(r'完全', '很', text)
    text = re.sub(r'真正', '确实', text)
    
    # 26. 简化重复的表达
    text = re.sub(r'速度非常快，内存占用极小', '速度快，内存占用少', text)
    text = re.sub(r'不应该浪费计算资源来对抗互联网上的吸血鬼', '不用浪费计算资源对抗AI爬虫', text)
    
    return text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 humanizer.py <text>")
        sys.exit(1)
    
    input_text = sys.argv[1]
    output_text = humanize_text(input_text)
    print(output_text)