# email_alert.py
import smtplib
import ssl
from email.message import EmailMessage
import os

def send_email_alert(smtp_server: str, smtp_port: int, username: str, password: str,
                     subject: str, body: str, to_emails: list, attachment_path: str = None):
    """
    Send an email with optional attachment.
    Uses SMTP_SSL (recommended for Gmail with app password).
    """
    msg = EmailMessage()
    msg["Subject"] ="  URGENT SAFETY ALERT: CRITICAL DROWSINESS DETECTED"
    msg["From"] = username
    msg["To"] = ", ".join(to_emails)
    msg.set_content("subject :  URGENT SAFETY ALERT: CRITICAL DROWSINESS DETECTED\n"
    "   This automated message from the Driver Drowsiness Detection System indicates a high-risk situation: Critical Drowsiness (Sleeping) was detected for [Driver's Name].\n"

"Action Required: Please contact the driver immediately. Safety intervention is strongly advised.\n"

'Sincerely,\n\n'

"The Driver Drowsiness Detection System Team")

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            data = f.read()
            maintype = "image"
            subtype = "jpeg"
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
        server.login(username, password)
        server.send_message(msg)
