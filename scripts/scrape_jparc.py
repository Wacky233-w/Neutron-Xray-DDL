from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scraper_common import (
    ProposalCall,
    fetch_html,
    html_links,
    html_to_text,
    normalize_text,
    parse_deadline,
    utc_now,
    write_payload,
)


SOURCE_URL = "https://mlfinfo.jp/en/user/proposals/"


def find_short_term_url(html: str, base_url: str) -> str:
    links = html_links(html, base_url)
    candidates: list[str] = []
    for href, label in links:
        target = f"{label} {href}"
        if re.search(r"short[-\s]?term", target, re.IGNORECASE):
            candidates.append(href)

    if not candidates:
        for href, _label in links:
            if re.search(r"/proposals/\d{4}[AB]/?$", href):
                candidates.append(href)

    if not candidates:
        raise ValueError("Could not find the current short-term proposal call URL.")

    return sorted(set(candidates), reverse=True)[0]


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title_match = re.search(r"(?P<title>\d{4}[AB]\s+Short[-\s]term\s+Proposal)", text, re.IGNORECASE)
    title = normalize_text(title_match.group("title")) if title_match else "Short-term Proposal"

    deadline_match = re.search(
        r"(?P<deadline>from\s+[A-Z][a-z]+\.?\s+\d{1,2}\s*-\s*[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}"
        r"\s+at\s+\d{1,2}:\d{2}\s+Japan Time\s+\(UTC\+09:00\))",
        text,
        re.IGNORECASE,
    )
    if not deadline_match:
        deadline_match = re.search(
            r"(?:deadline|due date).*?(?P<deadline>[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}[^.]{0,120})",
            text,
            re.IGNORECASE,
        )
    if not deadline_match:
        raise ValueError(f"Could not find deadline for {title}.")

    deadline_text = normalize_text(deadline_match.group("deadline")).strip(" :;-")
    deadline_date, deadline_time, timezone_label = parse_deadline(deadline_text)

    return ProposalCall(
        facility="J-PARC MLF",
        call_type="Short-term Proposal",
        title=title,
        status="closed" if re.search(r"\[Closed\]|\bclosed\b", text, re.IGNORECASE) else "open",
        deadline_text=deadline_text,
        deadline_date=deadline_date,
        deadline_time=deadline_time,
        timezone=timezone_label,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape J-PARC MLF short-term proposal deadline.")
    parser.add_argument("--url", default=SOURCE_URL, help="J-PARC proposals index URL.")
    parser.add_argument(
        "--output",
        default="data/jparc_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        index_html = fetch_html(args.url)
        call_url = find_short_term_url(index_html, args.url)
        text = html_to_text(fetch_html(call_url))
        call = extract_call(text, call_url)
        write_payload("jparc", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title} deadline {call.deadline_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
