import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_test_email(to_email):
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    from_email = os.getenv("EMAIL_FROM", smtp_user)

    print(f"Attempting to send test email to {to_email}...")
    print(f"Using host: {smtp_host}:{smtp_port}")
    print(f"From: {from_email}")

    subject = "EventEngine - Manual SMTP Test"
    body = "This is a manual test to verify SMTP functionality in your EventEngine project."

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.set_debuglevel(1)  # Enable debug level 1 to see SMTP transaction
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        print("\nSUCCESS: Email reported as sent by Gmail!")
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")

if __name__ == "__main__":
    target_email = "viraj.pisal24@vit.edu"  # Target email from user log
    send_test_email(target_email)
