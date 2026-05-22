from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://www.ansto.gov.au/facilities/australian-centre-for-neutron-scattering/call-for-proposals"


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "ACNS & NDF Merit Access Proposal"
    title_match = re.search(r"ACNS\s*&\s*NDF\s*Merit\s*Access\s*Proposal", text, re.IGNORECASE)
    if not title_match:
        raise ValueError("Could not find ACNS & NDF Merit Access Proposal.")

    block = text[title_match.start() : title_match.start() + 1200]
    deadline_match = re.search(
        r"(?:Deadline|Closing date|Closes?)\s*:?\s*(?P<deadline>[^.]{10,160})",
        block,
        re.IGNORECASE,
    )
    if not deadline_match:
        deadline_match = re.search(
            r"(?P<deadline>\d{1,2}\s+[A-Z][a-z]+\.?\s+\d{4}[^.]{0,80})",
            block,
            re.IGNORECASE,
        )
    if not deadline_match:
        raise ValueError(f"Could not find deadline for {title}.")

    deadline_text = deadline_match.group("deadline").strip(" :;-")
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="ANSTO Australian Centre for Neutron Scattering",
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
    parser = argparse.ArgumentParser(description="Scrape ANSTO ACNS & NDF deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="ANSTO proposal calls page URL.")
    parser.add_argument(
        "--output",
        default="data/ansto_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        call = extract_call(text, args.url)
        write_payload("ansto", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
