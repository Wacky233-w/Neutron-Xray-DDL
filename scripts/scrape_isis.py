from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, normalize_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://www.isis.stfc.ac.uk/using-isis/academics/"
DETAIL_URL = "https://isis.stfc.ac.uk/using-isis/academics/how-to-apply/direct-access/"


def extract_call(index_text: str, detail_text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "Direct Access"
    index_marker = re.search(r"Direct Access", index_text, re.IGNORECASE)
    index_block = index_text[index_marker.start() : index_marker.start() + 1600] if index_marker else index_text
    direct_row = re.search(
        r"Direct Access\s+(?P<status>[A-Z ]+?)\s+(?P<opens>[A-Z][a-z]+\s+\d{4})\s+(?P<closes>[A-Z][a-z]+\s+\d{4})",
        index_text,
        re.IGNORECASE,
    )
    is_closed = bool(direct_row and "closed" in direct_row.group("status").lower())

    if is_closed and direct_row:
        deadline_text = f"Call closes {direct_row.group('closes')}"
        deadline_date = None
        deadline_time = None
        timezone_label = None
    else:
        deadline_match = re.search(
            r"(?P<deadline>\d{1,2}:\d{2}\s+(?:BST|GMT)\s+[A-Z][a-z]+day\s+\d{1,2}\s+[A-Z][a-z]+\s+\d{4})",
            detail_text,
            re.IGNORECASE,
        )

        if deadline_match:
            deadline_text = normalize_text(deadline_match.group("deadline"))
            deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)
        else:
            deadline_text = "Direct Access call is currently closed."
            deadline_date = None
            deadline_time = None
            timezone_label = None

    return ProposalCall(
        facility="ISIS Neutron and Muon Source",
        call_type=title,
        title=title,
        status="closed" if is_closed else "open",
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        timezone=timezone_label,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape ISIS Direct Access deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="ISIS academics page URL.")
    parser.add_argument("--detail-url", default=DETAIL_URL, help="ISIS Direct Access detail page URL.")
    parser.add_argument(
        "--output",
        default="data/isis_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        index_text = html_to_text(fetch_html(args.url))
        detail_text = html_to_text(fetch_html(args.detail_url))
        call = extract_call(index_text, detail_text, args.detail_url)
        write_payload("isis", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
