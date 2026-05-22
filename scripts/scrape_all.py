from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scraper_common import utc_now


SCRAPERS = [
    "scripts/scrape_ornl.py",
    "scripts/scrape_spring8.py",
    "scripts/scrape_ansto.py",
    "scripts/scrape_jparc.py",
    "scripts/scrape_psi.py",
    "scripts/scrape_aps.py",
    "scripts/scrape_nsls2.py",
    "scripts/scrape_desy.py",
    "scripts/scrape_isis.py",
    "scripts/scrape_chess.py",
]

DATA_FILES = [
    "data/ornl_proposal_calls.json",
    "data/spring8_proposal_calls.json",
    "data/ansto_proposal_calls.json",
    "data/jparc_proposal_calls.json",
    "data/psi_proposal_calls.json",
    "data/aps_proposal_calls.json",
    "data/nsls2_proposal_calls.json",
    "data/desy_proposal_calls.json",
    "data/isis_proposal_calls.json",
    "data/chess_proposal_calls.json",
]


def run_scrapers() -> int:
    exit_code = 0
    for scraper in SCRAPERS:
        result = subprocess.run([sys.executable, scraper], check=False)
        if result.returncode:
            exit_code = result.returncode
    return exit_code


def aggregate(output_path: Path) -> None:
    calls = []
    for file_name in DATA_FILES:
        path = Path(file_name)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        calls.extend(payload.get("proposal_calls", []))

    calls.sort(key=lambda item: item.get("deadline_date") or "9999-12-31")
    payload = {
        "source": "all",
        "updated_at": utc_now(),
        "proposal_calls": calls,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_browser_data(payload, output_path.with_name("deadline_data.js"))


def write_browser_data(payload: dict, output_path: Path) -> None:
    js = "window.PROPOSAL_DEADLINES = "
    js += json.dumps(payload, indent=2)
    js += ";\n"
    output_path.write_text(js, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all proposal deadline scrapers.")
    parser.add_argument(
        "--output",
        default="data/all_proposal_calls.json",
        help="Path to write the aggregated JSON file.",
    )
    args = parser.parse_args()

    exit_code = run_scrapers()
    aggregate(Path(args.output))
    print(f"Wrote {args.output}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
