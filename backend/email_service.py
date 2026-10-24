import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    RESEND_API_KEY,
    RESEND_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME
)
from logger import logger

# In-memory notification & email log for real-time verification
EMAIL_DELIVERY_LOGS = []

def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> dict:
    """
    Dispatches transactional emails via:
    1. Resend HTTP REST API (Best for Vercel/Cloud Serverless, port 443, never blocked)
    2. Standard SMTP Fallback (e.g. Gmail App Password)
    """
    success = False
    delivery_note = ""

    # Priority 1: Resend HTTP REST API
    if RESEND_API_KEY:
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": f"{SMTP_FROM_NAME} <{RESEND_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            if text_content:
                payload["text"] = text_content

            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code in [200, 201]:
                data = res.json()
                success = True
                delivery_note = f"Dispatched via Resend API (ID: {data.get('id')})"
                logger.info(f"🚀 Email delivered to {to_email} via Resend API (ID: {data.get('id')})")
            else:
                logger.warning(f"Resend API returned status {res.status_code}: {res.text}. Trying SMTP...")
        except Exception as resend_err:
            logger.warning(f"Resend API dispatch error: {resend_err}. Trying SMTP...")

    # Priority 2: SMTP Fallback if Resend wasn't active or had an error
    if not success and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = to_email

            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            if html_content:
                msg.attach(MIMEText(html_content, "html"))

            try:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())
                success = True
                delivery_note = "Dispatched via SMTP (Port 587 STARTTLS)"
            except Exception as e587:
                logger.warning(f"SMTP 587 note: {e587}. Trying Port 465 SSL...")
                with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=8) as server:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())
                success = True
                delivery_note = "Dispatched via SMTP (Port 465 SSL)"
        except Exception as smtp_err:
            logger.warning(f"SMTP failed: {smtp_err}")
            delivery_note = f"Failed (Socket closed: {smtp_err})"

    if not delivery_note:
        delivery_note = "Not dispatched (No RESEND_API_KEY or SMTP credentials)"

    record = {
        "to": to_email,
        "subject": subject,
        "delivery_method": delivery_note,
        "success": success
    }
    EMAIL_DELIVERY_LOGS.append(record)
    logger.info(f"📧 Notification Recorded for {to_email} | Subject: '{subject}' | Method: {delivery_note}")
    return record
