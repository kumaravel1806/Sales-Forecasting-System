import os
import smtplib
from email.message import EmailMessage


def send_email(subject: str, body: str, to_email: str) -> bool:
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    pwd = os.getenv('SMTP_PASS')
    if not host or not user or not pwd:
        # Placeholder: not configured
        print('[notify] email not configured; subject=', subject)
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = to_email
        msg.set_content(body)
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        print('[notify] email send failed:', e)
        return False


def send_sms(body: str, to_number: str) -> bool:
    # Twilio placeholder: just log; integrate twilio client later
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    from_num = os.getenv('TWILIO_FROM_NUMBER')
    if not sid or not token or not from_num:
        print('[notify] sms not configured; body=', body)
        return False
    # Placeholder only
    print(f"[notify] SMS to {to_number}: {body}")
    return True
