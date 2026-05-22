from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import (
    ProposalCall,
    fetch_html,
    html_to_text,
    is_future_or_today,
    normalize_text,
    parse_deadline,
    utc_now,
    write_payload,
)


SOURCE_URL = "https://user.spring8.or.jp/?p=26156&lang=en"


def extract_calls(text: str, source_url: str) -> list[ProposalCall]:
    fetched_at = utc_now()
    calls: list[ProposalCall] = []
    sections = [
        ("BLs with biannual calls", "BLs with sixannual calls"),
        ("BLs with sixannual calls", "Notes"),
    ]

    for section_title, next_title in sections:
        block_match = re.search(
            rf"{re.escape(section_title)}(?P<block>.*?){re.escape(next_title)}",
            text,
            re.IGNORECASE,
        )
        block = block_match.group("block") if block_match else ""

        section_calls = extract_section_calls(section_title, block, source_url, fetched_at)
        if section_calls:
            calls.extend(section_calls)
        else:
            calls.append(
                ProposalCall(
                    facility="SPring-8",
                    call_type=section_title,
                    title=f"{section_title}: no open call found",
                    status="closed",
                    deadline_text=None,
                    deadline_date=None,
                    deadline_time=None,
                    timezone=None,
                    source_url=source_url,
                    fetched_at=fetched_at,
                )
            )

    return calls


def extract_section_calls(
    section_title: str, block: str, source_url: str, fetched_at: str
) -> list[ProposalCall]:
    calls: list[ProposalCall] = []
    deadline_matches = list(
        re.finditer(
            r"(?P<label>[^:]{10,120}?Proposals?)\s*:\s*"
            r"(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4},?\s+\d{1,2}:\d{2}\s*(?:am|pm)?)",
            block,
            re.IGNORECASE,
        )
    )

    for match in deadline_matches:
        label = normalize_text(match.group("label"))
        label = re.sub(r"^Deadline\s+for\s+", "", label, flags=re.IGNORECASE)
        label = clean_title(label)
        if should_skip_call(label):
            continue
        deadline_text = normalize_text(match.group("deadline"))
        deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)
        if not is_future_or_today(deadline_date):
            continue
        calls.append(
            ProposalCall(
                facility="SPring-8",
                call_type=section_title,
                title=label,
                status="open",
                deadline_text=deadline_text,
                deadline_date=deadline_date,
                deadline_time=deadline_time,
                timezone=timezone_label,
                source_url=source_url,
                fetched_at=fetched_at,
            )
        )

    return calls


def clean_title(label: str) -> str:
    known_titles = [
        "Non-Proprietary Priority Proposals and Proprietary Proposals",
        "General Proposals and Graduate Student Proposals",
    ]
    for title in known_titles:
        if title.lower() in label.lower():
            return title
    return label.strip(" :;-")


def should_skip_call(label: str) -> bool:
    ignored_titles = {
        "Non-Proprietary Priority Proposals and Proprietary Proposals",
    }
    return label in ignored_titles


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape SPring-8 proposal call deadlines.")
    parser.add_argument("--url", default=SOURCE_URL, help="SPring-8 proposal calls page URL.")
    parser.add_argument(
        "--output",
        default="data/spring8_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        calls = extract_calls(text, args.url)
        write_payload("spring8", calls, Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {len(calls)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
