#!/usr/bin/env python3
"""
Test Gmail email delivery using the last generated HTML preview.
Run test_claude.py first to produce generated/preview.html.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO
from core.mailer import delete_sent_emails, send_email_gmail

PREVIEW_PATH = os.path.join(os.path.dirname(__file__), '..', 'generated', 'preview.html')

if __name__ == '__main__':
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("❌ GMAIL_USER or GMAIL_APP_PASSWORD not set in .env")
        sys.exit(1)
    if not EMAIL_TO:
        print("❌ EMAIL_TO not set in .env")
        sys.exit(1)
    if not os.path.exists(PREVIEW_PATH):
        print(f"❌ {PREVIEW_PATH} not found — run tests/test_claude.py first")
        sys.exit(1)

    with open(PREVIEW_PATH, 'r') as f:
        html = f.read()

    from datetime import datetime

    recipients = [e.strip() for e in EMAIL_TO.split(',')]
    subject = f"[TEST] 📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"

    print(f"Sending test email to {', '.join(recipients)}...")
    msg_ids = send_email_gmail(subject, html, recipients)
    if not msg_ids:
        sys.exit(1)
    delete_sent_emails(msg_ids)
