import smtplib
import os
import sys
import tomllib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional


def load_credentials(config_file: Optional[str] = None) -> tuple:
    """
    Load Gmail credentials from a TOML config file.
    
    Searches in multiple locations:
    - Current directory: ./gmail_sender_config.toml
    - Home directory: ~/gmail_sender_config.toml
    
    Args:
        config_file: Path to config file. If None, searches default locations
        
    Returns:
        Tuple of (sender_email, app_password)
        
    Raises:
        FileNotFoundError: If config file doesn't exist in any location
        KeyError: If config file missing required fields
    """
    if config_file is None:
        # Define search paths for different platforms
        home = Path.home()
        cwd = Path.cwd()
        search_paths = [
            cwd / "gmail_sender_config.toml",
            home / "gmail_sender_config.toml"
        ]
        
        # Find first existing config file
        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = str(path)
                break
        
        if config_file is None:
            paths_str = "\n  ".join(str(p) for p in search_paths)
            raise FileNotFoundError(
                f"Config file not found in any of these locations:\n  {paths_str}\n"
                f"Create a TOML file with:\n"
                f"[gmail]\n"
                f'sender_email = "your.email@gmail.com"\n'
                f'app_password = "xxxx xxxx xxxx xxxx"'
            )
    
    with open(config_file, "rb") as f:
        config = tomllib.load(f)
    
    gmail_config = config.get("gmail", {})
    sender_email = gmail_config.get("sender_email")
    app_password = gmail_config.get("app_password")
    
    if not sender_email or not app_password:
        raise KeyError("Config file must contain [gmail] section with 'sender_email' and 'app_password'")
    
    return sender_email, app_password


class GmailSender:
    """
    A simple Gmail mail sender using SMTP.
    
    To use this:
    1. Enable 2-Factor Authentication on your Gmail account
    2. Generate an App Password: https://myaccount.google.com/apppasswords
    3. Use the generated app password (not your regular Gmail password)
    """
    
    def __init__(self, sender_email: str, app_password: str):
        """
        Initialize Gmail sender.
        
        Args:
            sender_email: Your Gmail address (e.g., your.email@gmail.com)
            app_password: Your Gmail app password (16 characters, no spaces)
        """
        self.sender_email = sender_email
        self.app_password = app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def send_email(
        self,
        recipient_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """
        Send an email via Gmail.
        
        Args:
            recipient_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            is_html: If True, body is treated as HTML; if False, as plain text
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipient_emails)
            
            # Attach body
            mime_type = "html" if is_html else "plain"
            message.attach(MIMEText(body, mime_type))
            
            # Connect to Gmail SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, recipient_emails, message.as_string())
            
            print(f"✓ Email sent successfully to {', '.join(recipient_emails)}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("✗ Authentication failed. Check your email and app password.")
            return False
        except smtplib.SMTPException as e:
            print(f"✗ SMTP error occurred: {e}")
            return False
        except Exception as e:
            print(f"✗ Error sending email: {e}")
            return False
    
    def send_bulk_emails(
        self,
        recipients_dict: dict,
        subject: str,
        is_html: bool = False
    ) -> dict:
        """
        Send personalized emails to multiple recipients.
        
        Args:
            recipients_dict: Dictionary with {email: body_text}
            subject: Email subject
            is_html: If True, body is treated as HTML
            
        Returns:
            Dictionary with {email: success_status}
        """
        results = {}
        for email, body in recipients_dict.items():
            results[email] = self.send_email([email], subject, body, is_html)
        return results


# Example usage
if __name__ == "__main__":
    # Load credentials from config file
    try:
        SENDER_EMAIL, APP_PASSWORD = load_credentials()
    except (FileNotFoundError, KeyError) as e:
        print(f"✗ Error loading credentials: {e}")
        exit(1)
    
    # Initialize sender
    sender = GmailSender(SENDER_EMAIL, APP_PASSWORD)
    
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
