# EMAIL CONFIGURATION GUIDE

To enable automatic emails when participants register, you need to configure email settings.

## Option 1: Using Gmail (Easiest)

1. Open the .env file in your project root
2. Add these lines:

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

3. Get Gmail App Password:
   - Go to: https://myaccount.google.com/apppasswords
   - Create a new app password
   - Copy the 16-character password
   - Use it as SMTP_PASSWORD

## Option 2: Using SendGrid (Recommended for Production)

1. Sign up at: https://sendgrid.com
2. Get your API key
3. Add to .env:

SENDGRID_API_KEY=your-sendgrid-api-key
EMAIL_FROM=noreply@yourdomain.com

## After Configuration:

1. Restart the API server (close and run python run.py again)
2. Register for an event
3. Check your email inbox for confirmation

## Test Email Setup:

Run this command to test:
python -c "from notifications.email import get_email_service; svc = get_email_service(); print('Email service configured:', svc.is_configured())"

## Important Notes:

- Without email configuration, registrations still work but no email is sent
- Participants can still register and get QR codes in the browser
- Email is optional but recommended for better user experience
