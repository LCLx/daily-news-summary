import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import GMAIL_USER, GMAIL_APP_PASSWORD


def send_email_gmail(subject, body_html, recipients):
    """
    Send an HTML email via Gmail SMTP using an App Password.

    Args:
        subject: Email subject line
        body_html: Complete HTML email body
        recipients: List of recipient addresses
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_USER or GMAIL_APP_PASSWORD not set, skipping email")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = 'undisclosed-recipients:;'
    msg.attach(MIMEText(body_html, 'html'))

    try:
        print(f"Sending email via Gmail to {len(recipients)} recipient(s)...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        print("✅ Email sent.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
