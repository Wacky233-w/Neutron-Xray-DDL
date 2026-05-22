from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, normalize_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://www.bnl.gov/nsls2/"


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "Next deadline for proposals and beam time requests"
    marker = re.search(r"Next deadline for proposals and beam time requests", text, re.IGNORECASE)
    if not marker:
        raise ValueError(f"Could not find {title}.")

    block = text[marker.start() : marker.start() + 500]
    deadline_match = re.search(
        r"(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}(?:\s+at\s+\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|am|pm))?)",
        block,
        re.IGNORECASE,
    )
    if not deadline_match:
        raise ValueError(f"Could not find deadline for {title}.")

    deadline_text = normalize_text(deadline_match.group("deadline")).strip(" :;-")
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="NSLS-II",
        call_type=title,
        title=title,
        status="open" if deadline_date else "unknown",
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        timezone=timezone_label,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape NSLS-II proposal deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="NSLS-II page URL.")
    parser.add_argument(
        "--output",
        default="data/nsls2_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        call = extract_call(text, args.url)
        write_payload("nsls2", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
