import argparse
import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import tomllib
from typing import Dict, List, Optional

from config import load_config, read_credentials, read_exceptions
from gmail_sender import GmailSender

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"]

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


def build_message(record: ApplicationRecord, templates: dict) -> dict:
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
    return {
        "subject": templates["subject"].format(**ctx),
        "body": templates["body"].format(**ctx),
    }


class SentLog:
    """Read → update → save lifecycle for the sent-followup CSV log."""

    _HEADER = ["date", "company", "position", "email"]

    def __init__(self, path: Path) -> None:
        self._path = path
        self._rows: List[List[str]] = []
        self._keys: set[tuple[str, str]] = set()
        self._load()

    # -- read --
    def _load(self) -> None:
        if not self._path.exists():
            return
        with open(self._path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header and header[:4] != self._HEADER:
                # No proper header – treat first line as data
                f.seek(0)
                reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    self._rows.append(row)
                    self._keys.add((row[1], row[2]))

    # -- update --
    def add(self, company: str, position: str, email: str) -> None:
        row = [datetime.now().strftime("%Y-%m-%d %H:%M"), company, position, email]
        self._rows.append(row)
        self._keys.add((company, position))

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._keys

    # -- save --
    def save(self) -> None:
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self._HEADER)
            writer.writerows(self._rows)


def send_followups(
    csv_path: Path,
    threshold_days: int,
    dry_run: bool = False,
    config_file: Optional[str] = None,
    recruiter_map_path: Optional[Path] = None,
    sent_log_path: Optional[Path] = None,
) -> int:
    resolved_config = os.path.expandvars(config_file) if config_file else None

    recruiter_map = load_recruiter_map(Path(os.path.expandvars(recruiter_map_path)) if recruiter_map_path else None)
    records = parse_csv(csv_path, recruiter_map)

    config = load_config(resolved_config)
    sender_email, app_password = read_credentials(config)
    sender = GmailSender(sender_email, app_password)

    skip_status, skip_companies = read_exceptions(config)
    templates = config["follow_up"]

    sent_log = SentLog(sent_log_path or Path("sent_followups.csv"))

    count_sent = 0
    for record in records:
        if skip_status and record.status == skip_status:
            continue
        if skip_companies and record.company in skip_companies:
            print(f"⏭️  Skipping {record.company} / {record.position}: company in exceptions list")
            continue
        if not should_follow_up(record, threshold_days):
            continue
        if not record.recruiter_email:
            print(f"⚠️ Skipping {record.company} / {record.position}: no recruiter email found")
            continue
        if (record.company, record.position) in sent_log:
            print(f"⏭️  Skipping {record.company} / {record.position}: already sent previously")
            continue

        message = build_message(record, templates)

        print(f"Sending to {record.recruiter_email}: {record.company} - {record.position}")
        if dry_run:
            print("DRY RUN: email not sent")
            count_sent += 1
            continue

        if sender.send_email([record.recruiter_email], message["subject"], message["body"]):
            sent_log.add(record.company, record.position, record.recruiter_email)
            count_sent += 1

        if count_sent >= 25:
            break

    sent_log.save()
    return count_sent


def main() -> int:
    parser = argparse.ArgumentParser(description="Send follow-up requests from job application CSV data.")
    parser.add_argument("csv_file", type=Path, help="Path to the CSV file")
    parser.add_argument("--days", type=int, default=30, help="Only follow up on applications older than this many days")
    parser.add_argument("--dry-run", action="store_true", help="Show which emails would be sent without sending")
    parser.add_argument("--config", type=str, default=None, help="Path to the TOML config file")
    parser.add_argument("--recruiter-map", type=Path, default=Path("recruiter_emails.toml"), help="Optional recruiter email mapping TOML file")
    parser.add_argument("--sent-log", type=Path, default=None, help="Path to CSV log of sent emails (default: sent_followups.csv)")

    args = parser.parse_args()

    count = send_followups(
        csv_path=args.csv_file,
        threshold_days=args.days,
        dry_run=args.dry_run,
        config_file=args.config,
        recruiter_map_path=args.recruiter_map,
        sent_log_path=args.sent_log,
    )

    print(f"\nDone. Follow-up emails sent: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
