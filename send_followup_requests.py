import argparse
import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import tomllib
from typing import Dict, List, Optional

from config import load_credentials
from gmail_sender import GmailSender

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"]

with open("follow_up.toml", "rb") as f:
    _TEMPLATES = tomllib.load(f)

@dataclass
class ApplicationRecord:
    submitted_on: Optional[datetime]
    response_date: Optional[datetime]
    company: str
    position: str
    status: str
    recruiter_email: Optional[str]
    raw: Dict[str, str]


def parse_date(value: str) -> Optional[datetime]:
    if not value or not value.strip():
        return None

    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def find_email_in_text(text: str) -> Optional[str]:
    if not text:
        return None
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def load_recruiter_map(path: Optional[Path] = None) -> Dict[str, str]:
    if path is None:
        path = Path.cwd() / "recruiter_emails.toml"
    if not path.exists():
        return {}

    import tomllib

    with open(path, "rb") as f:
        config = tomllib.load(f)

    return config.get("recruiters", {}) or {}


def normalize_field_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def parse_csv(path: Path, recruiter_map: Dict[str, str]) -> List[ApplicationRecord]:
    with open(path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        rows = [
            {normalize_field_name(key): value.strip() for key, value in row.items() if key is not None}
            for row in reader
        ]

    records: List[ApplicationRecord] = []
    for row in rows:
        submitted_on = parse_date(row.get("beworben_am", ""))
        response_date = parse_date(row.get("vorstellungstermin_am", "")) or parse_date(row.get("antwortdatum", ""))
        company = row.get("beworben_bei", "").strip()
        position = row.get("beworben_als", "").strip()
        status = row.get("stand_der_bewerbung", "").strip().lower()
        recruiter_email = None

        # print(f"date={submitted_on}, response_date={response_date}, company='{company}', position='{position}', status='{status}'")

        # Look for email in row values
        for value in row.values():
            recruiter_email = find_email_in_text(value)
            if recruiter_email:
                break

        # If no email found, try mapping by company or recruiter name
        if not recruiter_email and company:
            recruiter_email = recruiter_map.get(company) or recruiter_map.get(company.lower())

        records.append(
            ApplicationRecord(
                submitted_on=submitted_on,
                response_date=response_date,
                company=company,
                position=position,
                status=status,
                recruiter_email=recruiter_email,
                raw=row,
            )
        )

    return records


def should_follow_up(record: ApplicationRecord, threshold_days: int) -> bool:
    date = record.response_date or record.submitted_on
    if not date:
        return False
    return datetime.now() - date > timedelta(days=threshold_days)


def build_message(record: ApplicationRecord) -> dict:
    submitted = (
        record.submitted_on.strftime('%d.%m.%Y')
        if record.submitted_on
        else 'an earlier date'
    )
    ctx = {
        "position": record.position,
        "company": record.company,
        "status": record.status,
        "submitted_on": submitted,
    }
    tmpl = _TEMPLATES["follow_up"]
    return {
        "subject": tmpl["subject"].format(**ctx),
        "body": tmpl["body"].format(**ctx),
    }


def send_followups(
    csv_path: Path,
    threshold_days: int,
    dry_run: bool = False,
    config_file: Optional[str] = None,
    recruiter_map_path: Optional[Path] = None,
) -> int:
    recruiter_map = load_recruiter_map(Path(os.path.expandvars(recruiter_map_path)) if recruiter_map_path else None)
    records = parse_csv(csv_path, recruiter_map)

    sender_email, app_password = load_credentials(os.path.expandvars(config_file) if config_file else None)
    sender = GmailSender(sender_email, app_password)

    count_sent = 0
    for record in records:
        if record.status == "absage":
            continue
        if not should_follow_up(record, threshold_days):
            continue
        if not record.recruiter_email:
            print(f"⚠️ Skipping {record.company} / {record.position}: no recruiter email found")
            continue

        subject, body = build_message(record)

        print(f"Sending to {record.recruiter_email}: {record.company} - {record.position}")
        if dry_run:
            print("DRY RUN: email not sent")
            count_sent += 1
            continue

        if sender.send_email([record.recruiter_email], subject, body):
            count_sent += 1

    return count_sent


def main() -> int:
    parser = argparse.ArgumentParser(description="Send follow-up requests from job application CSV data.")
    parser.add_argument("csv_file", type=Path, help="Path to the CSV file")
    parser.add_argument("--days", type=int, default=30, help="Only follow up on applications older than this many days")
    parser.add_argument("--dry-run", action="store_true", help="Show which emails would be sent without sending")
    parser.add_argument("--config", type=str, default=None, help="Path to the TOML config file")
    parser.add_argument("--recruiter-map", type=Path, default=Path("recruiter_emails.toml"), help="Optional recruiter email mapping TOML file")

    args = parser.parse_args()

    count = send_followups(
        csv_path=args.csv_file,
        threshold_days=args.days,
        dry_run=args.dry_run,
        config_file=args.config,
        recruiter_map_path=args.recruiter_map,
    )

    print(f"\nDone. Follow-up emails sent: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
