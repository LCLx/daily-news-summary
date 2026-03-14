import imaplib
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid

from core.config import GMAIL_USER, GMAIL_APP_PASSWORD


def send_email_gmail(subject, body_html, recipients):
    """
    Send an HTML email via Gmail SMTP using an App Password.
    Returns list of Message-IDs for the sent emails.

    Args:
        subject: Email subject line
        body_html: Complete HTML email body
        recipients: List of recipient addresses
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_USER or GMAIL_APP_PASSWORD not set, skipping email")
        return []

    message_ids = []
    try:
        print(f"Sending email via Gmail to {len(recipients)} recipient(s)...")
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
        print("✅ Email sent.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
    return message_ids


def delete_sent_emails(message_ids):
    """
    Delete sent emails from Gmail's Sent folder by Message-ID via IMAP.

    Args:
        message_ids: List of Message-ID strings to delete
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not message_ids:
        return

    try:
        time.sleep(2)
        print("🗑️ Deleting sent emails...")
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

        if deleted:
            print(f"✅ Deleted {deleted} sent email(s)")
        else:
            print("No matching sent emails found")
        mail.logout()
    except Exception as e:
        print(f"⚠️ Failed to delete sent emails: {e}")
