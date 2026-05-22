from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, normalize_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://www.aps.anl.gov/Users-Information/About-Proposals/Apply-for-Time"


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "General User Proposal Call"
    title_match = re.search(r"General\s+User\s+Proposal\s+Call", text, re.IGNORECASE)
    if not title_match:
        raise ValueError("Could not find General User Proposal Call.")

    block = text[title_match.start() : title_match.start() + 2200]
    deadline_match = re.search(
        r"(?:deadline|closes?|due)\s*:?\s*"
        r"(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}[^<]{0,180}?(?:a\.m\.|p\.m\.|am|pm|Chicago time|Central time|CT))",
        block,
        re.IGNORECASE,
    )
    if not deadline_match:
        deadline_match = re.search(
            r"(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}[^.]{0,100}(?:Chicago time|Central time|CT)?)",
            block,
            re.IGNORECASE,
        )
    if not deadline_match:
        raise ValueError(f"Could not find deadline for {title}.")

    deadline_text = normalize_text(deadline_match.group("deadline")).strip(" :;-")
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="Advanced Photon Source",
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
    parser = argparse.ArgumentParser(description="Scrape APS General User Proposal Call deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="APS apply-for-time page URL.")
    parser.add_argument(
        "--output",
        default="data/aps_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        call = extract_call(text, args.url)
        write_payload("aps", [call], Path(args.output))
    except Exception as exc:
        if Path(args.output).exists():
            print(f"Warning: could not update APS data; keeping existing {args.output}.")
            return 0
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
