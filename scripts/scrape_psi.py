from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, normalize_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://www.psi.ch/en/sinq/call-for-proposals"


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "SINQ - call for proposals"
    title_match = re.search(r"SINQ\s*-\s*call\s+for\s+proposals", text, re.IGNORECASE)
    block = text[title_match.start() : title_match.start() + 1800] if title_match else text[:2200]

    deadline_match = re.search(
        r"(?:submission deadline|deadline|next deadline)\s*:?\s*(?P<deadline>[^.]{10,180})",
        block,
        re.IGNORECASE,
    )
    if not deadline_match:
        deadline_match = re.search(
            r"(?P<deadline>\d{1,2}\s+[A-Z][a-z]+\.?\s+\d{4}[^.]{0,100})",
            block,
            re.IGNORECASE,
        )
    if not deadline_match:
        raise ValueError(f"Could not find deadline for {title}.")

    deadline_text = normalize_text(deadline_match.group("deadline")).strip(" :;-")
    deadline_text = re.split(r"\s+The Digital User Office\b", deadline_text, maxsplit=1)[0].strip()
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="PSI SINQ",
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
    parser = argparse.ArgumentParser(description="Scrape PSI SINQ call deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="PSI SINQ call page URL.")
    parser.add_argument(
        "--output",
        default="data/psi_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        call = extract_call(text, args.url)
        write_payload("psi", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
