import base64
import imaplib
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid

import requests

from core.config import (
    GMAIL_USER, GMAIL_APP_PASSWORD,
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN,
)


def _get_access_token():
    """Exchange refresh token for a short-lived access token via Google OAuth2."""
    resp = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': GMAIL_CLIENT_ID,
        'client_secret': GMAIL_CLIENT_SECRET,
        'refresh_token': GMAIL_REFRESH_TOKEN,
        'grant_type': 'refresh_token',
    })
    resp.raise_for_status()
    return resp.json()['access_token']


def _send_via_api(subject, body_html, recipients):
    """Send HTML email via Gmail REST API (HTTPS only, no SMTP)."""
    access_token = _get_access_token()
    message_ids = []

    for recipient in recipients:
        msg = MIMEMultipart('alternative')
        msg_id = make_msgid()
        msg['Message-ID'] = msg_id
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg.attach(MIMEText(body_html, 'html'))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': f'Bearer {access_token}'},
            json={'raw': raw},
        )
        resp.raise_for_status()
        message_ids.append(resp.json().get('id'))

    return message_ids


def _send_via_smtp(subject, body_html, recipients):
    """Send HTML email via Gmail SMTP (legacy fallback)."""
    message_ids = []
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        for recipient in recipients:
            msg = MIMEMultipart('alternative')
            msg_id = make_msgid()
            msg['Message-ID'] = msg_id
            msg['Subject'] = subject
            msg['From'] = GMAIL_USER
            msg['To'] = recipient
            msg.attach(MIMEText(body_html, 'html'))
            server.sendmail(GMAIL_USER, [recipient], msg.as_string())
            message_ids.append(msg_id)
    return message_ids


def send_email_gmail(subject, body_html, recipients):
    """
    Send an HTML email via Gmail.

    Prefers OAuth2 REST API (works in environments without SMTP access).
    Falls back to SMTP if OAuth2 credentials are not set.
    """
    use_api = GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN
    use_smtp = GMAIL_USER and GMAIL_APP_PASSWORD

    if not use_api and not use_smtp:
        print("⚠️ No Gmail credentials set (OAuth2 or SMTP), skipping email")
        return []

    try:
        print(f"Sending email to {len(recipients)} recipient(s)...")
        if use_api:
            print("  (via Gmail API / HTTPS)")
            ids = _send_via_api(subject, body_html, recipients)
        else:
            print("  (via Gmail SMTP)")
            ids = _send_via_smtp(subject, body_html, recipients)
        print("✅ Email sent.")
        return ids
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return []


def delete_sent_emails(message_ids):
    """
    Delete sent emails from Gmail.

    Uses Gmail API if OAuth2 is available, otherwise IMAP.
    For API-sent emails, message_ids are Gmail message IDs (not Message-ID headers).
    """
    if not message_ids:
        return

    use_api = GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN

    try:
        time.sleep(2)
        print("🗑️ Deleting sent emails...")

        if use_api:
            # Gmail API cannot remove the SENT label (system label).
            # For self-sent emails, trashing would remove from Inbox too.
            # Skip cleanup in API mode — Sent copy is harmless.
            print("ℹ️ Skipping Sent cleanup (Gmail API mode)")
            return
        else:
            if not GMAIL_USER or not GMAIL_APP_PASSWORD:
                return
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            mail.select('"[Gmail]/Sent Mail"')

            deleted = 0
            for msg_id in message_ids:
                _, data = mail.search(None, f'HEADER Message-ID "{msg_id}"')
                nums = data[0].split()
                for num in nums:
                    mail.store(num, '+FLAGS', '\\Deleted')
                    deleted += 1
            mail.expunge()
            print(f"✅ Deleted {deleted} sent email(s)" if deleted else "No matching sent emails found")
            mail.logout()
    except Exception as e:
        print(f"⚠️ Failed to delete sent emails: {e}")
