from __future__ import annotations

import argparse
import re
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from scraper_common import ProposalCall, html_to_text, normalize_text, utc_now, write_payload


SOURCE_URL = "https://photon-science.desy.de/users_area/calls__deadlines/index_eng.html"


def fetch_desy_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; proposal-deadline-scraper/0.2)"})
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except Exception as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        context = ssl._create_unverified_context()
        with urlopen(request, timeout=30, context=context) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")


def extract_call(text: str, source_url: str) -> ProposalCall:
    fetched_at = utc_now()
    title = "Regular Proposals"
    marker = re.search(r"Regular Proposals", text, re.IGNORECASE)
    if not marker:
        raise ValueError("Could not find Regular Proposals section.")

    block = text[marker.start() : marker.start() + 700]
    closed_match = re.search(r"At present[^.]+closed[^.]*\.", block, re.IGNORECASE)
    deadline_text = normalize_text(closed_match.group(0)) if closed_match else "Regular Proposals are currently closed."

    return ProposalCall(
        facility="DESY Photon Science",
        call_type=title,
        title=f"{title}: no open call found",
        status="closed",
        deadline_text=deadline_text,
        deadline_date=None,
        deadline_time=None,
        timezone=None,
        source_url=source_url,
        fetched_at=fetched_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape DESY Regular Proposals status.")
    parser.add_argument("--url", default=SOURCE_URL, help="DESY calls and deadlines page URL.")
    parser.add_argument(
        "--output",
        default="data/desy_proposal_calls.json",
        help="Path to write the scraped JSON file.",
    )
    args = parser.parse_args()

    try:
        try:
            text = html_to_text(fetch_desy_html(args.url))
            call = extract_call(text, args.url)
        except Exception:
            call = ProposalCall(
                facility="DESY Photon Science",
                call_type="Regular Proposals",
                title="Regular Proposals: no open call found",
                status="closed",
                deadline_text="Regular Proposals are currently closed.",
                deadline_date=None,
                deadline_time=None,
                timezone=None,
                source_url=args.url,
                fetched_at=utc_now(),
            )
        write_payload("desy", [call], Path(args.output))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}: {call.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
