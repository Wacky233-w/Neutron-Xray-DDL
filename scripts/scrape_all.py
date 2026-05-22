from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scraper_common import utc_now


SCRAPER_JOBS = [
    ("scripts/scrape_ornl.py", "data/ornl_proposal_calls.json"),
    ("scripts/scrape_spring8.py", "data/spring8_proposal_calls.json"),
    ("scripts/scrape_ansto.py", "data/ansto_proposal_calls.json"),
    ("scripts/scrape_jparc.py", "data/jparc_proposal_calls.json"),
    ("scripts/scrape_psi.py", "data/psi_proposal_calls.json"),
    ("scripts/scrape_aps.py", "data/aps_proposal_calls.json"),
    ("scripts/scrape_nsls2.py", "data/nsls2_proposal_calls.json"),
    ("scripts/scrape_desy.py", "data/desy_proposal_calls.json"),
    ("scripts/scrape_isis.py", "data/isis_proposal_calls.json"),
    ("scripts/scrape_chess.py", "data/chess_proposal_calls.json"),
]

DATA_FILES = [data_file for _scraper, data_file in SCRAPER_JOBS]


def run_scrapers() -> int:
    exit_code = 0
    for scraper, data_file in SCRAPER_JOBS:
        result = subprocess.run([sys.executable, scraper], check=False)
        if result.returncode:
            if Path(data_file).exists():
                print(
                    f"Warning: {scraper} failed with exit code {result.returncode}; "
                    f"keeping existing {data_file}.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Error: {scraper} failed and {data_file} does not exist.",
                    file=sys.stderr,
                )
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
