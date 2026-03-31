#!/bin/bash
# 每日 AI 热点新闻采集脚本
# 此脚本由定时任务调用，不需要单独执行

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始采集 AI 热点新闻..."

# 设置工作目录
cd /root/.openclaw/workspace

# 执行 Python 脚本
python3 scripts/daily_ai_news.py
