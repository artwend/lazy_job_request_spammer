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
2. Python 3.11 or higher (uses built-in `tomllib`)

### Configuration

1. Enable 2FA on your Gmail account
2. Generate an App Password:
   - Visit: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password

3. Create config file at one of these locations (searched in order):
   
   **Current directory:**
   ```
   ./gmail_sender_config.toml
   ```
   
   **Windows:**
   ```
   C:\Users\<YourUsername>\gmail_sender_config.toml
   ```
   
   **Linux/macOS:**
   ```
   ~/gmail_sender_config.toml
   ```

4. Add your credentials to the config file:
   ```toml
   [gmail]
   sender_email = "your.email@gmail.com"
   app_password = "xxxx xxxx xxxx xxxx"
   ```
   
   Or copy the example file:
   ```bash
   cp gmail_sender_config.toml.example ~/.gmail_sender_config.toml
   # Edit with your credentials
   ```

## Sending follow-up requests from CSV

Create an optional recruiter mapping file in the project directory:

```toml
[recruiters]
"Steadforce" = "recruiter@steadforce.com"
"Mobileye" = "hr@mobileye.com"
```

Then run:

```bash
python send_followup_requests.py /path/to/Übersicht\ Bewerbungen.csv --dry-run
```

To actually send emails, omit `--dry-run`.
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
