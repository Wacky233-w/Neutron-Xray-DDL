from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import ProposalCall, fetch_html, html_to_text, parse_deadline, utc_now, write_payload


SOURCE_URL = "https://neutrons.ornl.gov/users/proposal-calls"


def extract_latest_general_user_call(text: str, source_url: str) -> ProposalCall:
    title_pattern = re.compile(r"(?P<title>\d{4}-[A-Z]\s+General\s+User\s+Proposal\s+Call)")
    matches = list(title_pattern.finditer(text))
    if not matches:
        raise ValueError("Could not find any General User Proposal Call title.")

    latest = None
    block = ""
    deadline_match = None
    for index, candidate in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        candidate_block = text[candidate.start() : next_start]
        candidate_deadline = re.search(
            r"deadline for proposal submissions is (?P<deadline>[^.]+)",
            candidate_block,
            re.IGNORECASE,
        )
        if candidate_deadline:
            latest = candidate
            block = candidate_block
            deadline_match = candidate_deadline
            break

    if not latest or not deadline_match:
        raise ValueError("Could not find a General User Proposal Call with a deadline sentence.")

    title = re.sub(r"\s+", " ", latest.group("title"))
    status = "open" if re.search(r"\bopen\b", block, re.IGNORECASE) else "closed"

    deadline_text = deadline_match.group("deadline").strip()
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="ORNL Neutron Sciences",
        call_type="General User Proposal Call",
        title=title,
        status=status,
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        timezone=timezone_label,
        source_url=source_url,
        fetched_at=utc_now(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape ORNL General User Proposal Call deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="ORNL proposal calls page URL.")
    parser.add_argument(
        "--output",
        default="data/ornl_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        html = fetch_html(args.url)
        text = html_to_text(html)
        call = extract_latest_general_user_call(text, args.url)
        write_payload("ornl", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
