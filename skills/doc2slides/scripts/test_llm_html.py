#!/usr/bin/env python3
# Part of doc2slides skill.

#!/usr/bin/env python3
"""
Test LLM-based HTML generation with dashboard layout.

Usage:
  python test_llm_html.py --test dashboard
  python test_llm_html.py --test big_number
  python test_llm_html.py --data slide.json --output slide.html
"""

import sys
import json
import argparse
import asyncio
from pathlib import Path

# Add current dir to path
CURRENT_DIR = Path(__file__).parent
sys.path.insert(0, str(CURRENT_DIR))

from dashboard_prompts import EXAMPLE_DASHBOARD_DATA, EXAMPLE_BIG_NUMBER_DATA


async def test_dashboard():
    """Test dashboard slide generation."""
    print("=" * 60)
    print("Testing DASHBOARD layout generation...")
    print("=" * 60)
    
    try:
        from llm_generate_html import LLMHTMLGenerator
        
        generator = LLMHTMLGenerator()
        html = await generator.generate_slide_html(EXAMPLE_DASHBOARD_DATA)
        
        # Save output
        output_file = CURRENT_DIR.parent / "test_dashboard.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Dashboard HTML generated: {output_file}")
        print(f"   File size: {len(html)} bytes")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_big_number():
    """Test big number slide generation."""
    print("=" * 60)
    print("Testing BIG_NUMBER layout generation...")
    print("=" * 60)
    
    try:
        from llm_generate_html import LLMHTMLGenerator
        
        generator = LLMHTMLGenerator()
        html = await generator.generate_slide_html(EXAMPLE_BIG_NUMBER_DATA)
        
        # Save output
        output_file = CURRENT_DIR.parent / "test_big_number.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Big Number HTML generated: {output_file}")
        print(f"   File size: {len(html)} bytes")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_custom(data_file: str, output_file: str):
    """Test custom slide generation."""
    print("=" * 60)
    print(f"Testing custom slide from {data_file}...")
    print("=" * 60)
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            slide_data = json.load(f)
        
        from llm_generate_html import LLMHTMLGenerator
        
        generator = LLMHTMLGenerator()
        html = await generator.generate_slide_html(slide_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Custom HTML generated: {output_file}")
        print(f"   File size: {len(html)} bytes")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description='Test LLM HTML generation')
    parser.add_argument('--test', choices=['dashboard', 'big_number'], help='Run built-in test')
    parser.add_argument('--data', help='Custom slide data JSON file')
    parser.add_argument('--output', help='Output HTML file')
    
    args = parser.parse_args()
    
    if args.test == 'dashboard':
        await test_dashboard()
    elif args.test == 'big_number':
        await test_big_number()
    elif args.data and args.output:
        await test_custom(args.data, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
