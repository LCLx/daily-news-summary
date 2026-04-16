import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid

import requests

from core.config import (
    GMAIL_USER,
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


def send_email_gmail(subject, body_html, recipients):
    """Send an HTML email via Gmail REST API (OAuth2)."""
    if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
        print("⚠️ Gmail OAuth2 credentials not set, skipping email")
        return []

    try:
        print(f"Sending email to {len(recipients)} recipient(s) via Gmail API...")
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

        print("✅ Email sent.")
        return message_ids
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return []


def delete_sent_emails(message_ids):
    """
    Delete sent emails from Gmail.

    Gmail API cannot remove the SENT label (system label).
    For self-sent emails, trashing would remove from Inbox too.
    Skip cleanup in API mode — Sent copy is harmless.
    """
    if not message_ids:
        return
    print("ℹ️ Skipping Sent cleanup (Gmail API mode)")
