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


SOURCE_URL = "https://www.chess.cornell.edu/users/chess-deadlines"


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    call_type = "Proposal Deadline"
    run_matches = list(
        re.finditer(
            r"(?P<run>\d{4}\s+(?:Spring|Summer|Fall|Winter)\s+Run\s+\([^)]+\))",
            text,
            re.IGNORECASE,
        )
    )

    future_deadlines: list[tuple[str, str, str | None, str | None, str | None]] = []
    for index, run_match in enumerate(run_matches):
        next_start = run_matches[index + 1].start() if index + 1 < len(run_matches) else len(text)
        block = text[run_match.start() : next_start]
        deadline_match = re.search(
            r"Proposal Deadline\s+(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})",
            block,
            re.IGNORECASE,
        )
        if not deadline_match:
            continue

        run_title = normalize_text(run_match.group("run"))
        deadline_text = normalize_text(deadline_match.group("deadline")).strip(" :;-")
        deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)
        if is_future_or_today(deadline_date):
            future_deadlines.append((run_title, deadline_text, deadline_date, deadline_time, timezone_label))

    if not future_deadlines:
        return ProposalCall(
            facility="CHESS",
            call_type=call_type,
            title=f"{call_type}: no open call found",
            status="closed",
            deadline_text=None,
            deadline_date=None,
            deadline_time=None,
            timezone=None,
            source_url=source_url,
            fetched_at=fetched_at,
        )

    run_title, deadline_text, deadline_date, deadline_time, timezone_label = sorted(
        future_deadlines, key=lambda item: item[2] or "9999-12-31"
    )[0]

    return ProposalCall(
        facility="CHESS",
        call_type=call_type,
        title=f"{run_title} {call_type}",
        status="open",
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        timezone=timezone_label,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape CHESS proposal deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="CHESS deadlines page URL.")
    parser.add_argument(
        "--output",
        default="data/chess_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        text = html_to_text(fetch_html(args.url))
        call = extract_call(text, args.url)
        write_payload("chess", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
