# Gmail Mail Sender

A simple Python utility to send emails via Gmail's SMTP server.

## Features

- Send plain text and HTML emails
- Bulk email sending with personalization
- Easy-to-use `GmailSender` class
- Error handling and logging

## Setup

### Prerequisites

1. Gmail account with 2-Factor Authentication enabled
2. Python 3.6+

### Configuration

1. Enable 2FA on your Gmail account
2. Generate an App Password:
   - Visit: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password

3. Update credentials in the script:
   ```python
   SENDER_EMAIL = "your.email@gmail.com"
   APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   ```

## Usage

```python
from lazy_job_request_spamer import GmailSender

sender = GmailSender("your.email@gmail.com", "your-app-password")

# Send simple email
sender.send_email(
    recipient_emails=["recipient@example.com"],
    subject="Hello",
    body="This is a test email"
)

# Send HTML email
sender.send_email(
    recipient_emails=["recipient@example.com"],
    subject="HTML Email",
    body="<h1>Hello</h1>",
    is_html=True
)

# Send bulk emails
recipients = {
    "user1@example.com": "Personalized message for user1",
    "user2@example.com": "Personalized message for user2"
}
sender.send_bulk_emails(recipients, "Subject")
```

## License

MIT
