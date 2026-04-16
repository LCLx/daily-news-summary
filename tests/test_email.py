#!/usr/bin/env python3
"""
Test Gmail SMTP email delivery using the last generated HTML preview.
Run test_claude.py first to produce generated/preview.html.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO

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
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    recipients = [e.strip() for e in EMAIL_TO.split(',')]
    subject = f"[TEST] 📰 每日新闻摘要 - {datetime.now().strftime('%Y年%m月%d日')}"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText(html, 'html'))

    print(f"Sending test email to {', '.join(recipients)}...")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        print("✅ Email sent.")
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)
