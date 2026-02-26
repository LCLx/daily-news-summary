#!/usr/bin/env python3
"""
Quick visual test for image rendering in email template.
Uses mock articles with different image aspect ratios (no Claude call needed).
Run: uv run tests/test_images.py
Then open generated/preview_images.html in a browser.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.renderer import build_email_html_from_json

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# picsum.photos supports /w/h path for arbitrary aspect ratios
MOCK_SECTIONS = [
    {
        'category': '图片渲染测试',
        'emoji': '🖼️',
        'items': [
            {
                'title_zh': '横版宽图 (1200×630, 约 2:1)',
                'summary_zh': '常见的新闻配图比例，应正常显示不变形。',
                'image_url': 'https://picsum.photos/1200/630',
                'link': 'https://example.com',
                'title': 'Wide landscape image',
                'source': 'Test',
                'published': '2026-02-25',
            },
            {
                'title_zh': '竖版长图 (600×900, 约 2:3)',
                'summary_zh': '竖版图片，应按比例缩小至框内，不拉伸不裁切。',
                'image_url': 'https://picsum.photos/600/900',
                'link': 'https://example.com',
                'title': 'Tall portrait image',
                'source': 'Test',
                'published': '2026-02-25',
            },
            {
                'title_zh': '超长竖图 (400×1200, 约 1:3)',
                'summary_zh': '极端竖版比例，应显示在约 133×400px 的框内，不变形。',
                'image_url': 'https://picsum.photos/400/1200',
                'link': 'https://example.com',
                'title': 'Very tall image',
                'source': 'Test',
                'published': '2026-02-25',
            },
            {
                'title_zh': '正方形图 (600×600)',
                'summary_zh': '正方形图片，应正常缩放。',
                'image_url': 'https://picsum.photos/600/600',
                'link': 'https://example.com',
                'title': 'Square image',
                'source': 'Test',
                'published': '2026-02-25',
            },
        ],
    }
]

html = build_email_html_from_json(MOCK_SECTIONS)
output_path = os.path.join(OUTPUT_DIR, 'preview_images.html')
with open(output_path, 'w') as f:
    f.write(html)

print(f"✅ Saved to {output_path}")
print("   Open in browser to verify image rendering.")
