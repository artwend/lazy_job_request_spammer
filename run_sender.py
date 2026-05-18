from gmail_sender import GmailSender
from config import load_credentials


def main():
    try:
        sender_email, app_password = load_credentials()
    except (FileNotFoundError, KeyError) as e:
        print(f"✗ Error loading credentials: {e}")
        return 1

    sender = GmailSender(sender_email, app_password)

    # Example 1: Send simple email
    print("Example 1: Simple email")
    sender.send_email(
        recipient_emails=["recipient@example.com"],
        subject="Hello from Gmail Sender",
        body="This is a test email sent using Python!"
    )

    print()

    # Example 2: Send HTML email
    print("Example 2: HTML email")
    html_body = """
    <html>
      <body>
        <h1>Welcome!</h1>
        <p>This is an <b>HTML email</b> with formatting.</p>
      </body>
    </html>
    """
    sender.send_email(
        recipient_emails=["recipient@example.com"],
        subject="HTML Email Example",
        body=html_body,
        is_html=True
    )

    print()

    # Example 3: Send bulk personalized emails
    print("Example 3: Bulk emails")
    recipients = {
        "user1@example.com": "Hello User 1, this is your personalized message!",
        "user2@example.com": "Hello User 2, this is your personalized message!",
    }
    results = sender.send_bulk_emails(recipients, "Personalized Message")
    print(f"Bulk send results: {results}")


if __name__ == "__main__":
    raise SystemExit(main())
