#!/usr/bin/env python3
"""
Test configured LLM output with real RSS articles, skipping email sending.
Saves generated/preview.html and generated/preview.json for inspection.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipelines.email_pipeline import generate_digest, save_preview

if __name__ == '__main__':
    email_html, parsed = generate_digest()
    if email_html:
        save_preview(email_html, parsed)
