#!/usr/bin/env python3
"""
CogView 图像生成脚本
使用智谱 AI API 生成图片
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# 智谱 API 配置
API_KEY = "1e5a08233246a4c7f4bb6a9ffacdf634.ohofkR0w9RYC8ZRx"
API_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"

def generate_image(prompt: str, size: str = "1024x1024", model: str = "cogview-3-plus") -> dict:
    """调用智谱 API 生成图片"""
    
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"API 错误: {e.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)

def download_image(url: str, output_path: str) -> str:
    """下载图片到本地"""
    try:
        urllib.request.urlretrieve(url, output_path)
        return output_path
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="使用智谱 CogView 生成图片")
    parser.add_argument("prompt", help="图片描述")
    parser.add_argument("--size", "-s", default="1024x1024", 
                        choices=["768x768", "1024x1024", "1024x768", "768x1024"],
                        help="图片尺寸")
    parser.add_argument("--model", "-m", default="cogview-3-plus",
                        choices=["cogview-3", "cogview-3-plus"],
                        help="模型选择")
    parser.add_argument("--output", "-o", default=None,
                        help="输出路径")
    
    args = parser.parse_args()
    
    # 生成图片
    print(f"正在生成图片: {args.prompt}")
    print(f"尺寸: {args.size}, 模型: {args.model}")
    
    result = generate_image(args.prompt, args.size, args.model)
    
    if "data" not in result or len(result["data"]) == 0:
        print("生成失败: 未返回图片", file=sys.stderr)
        sys.exit(1)
    
    image_url = result["data"][0]["url"]
    print(f"图片 URL: {image_url}")
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/tmp/cogview_{timestamp}.png"
    
    # 下载图片
    download_image(image_url, output_path)
    print(f"图片已保存: {output_path}")
    
    # 输出路径供脚本调用
    print(f"OUTPUT:{output_path}")

if __name__ == "__main__":
    main()
