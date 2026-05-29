from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scraper_common import utc_now


SCRAPER_JOBS = [
    ("ORNL", "scripts/scrape_ornl.py", "data/ornl_proposal_calls.json"),
    ("SPring-8", "scripts/scrape_spring8.py", "data/spring8_proposal_calls.json"),
    ("ANSTO", "scripts/scrape_ansto.py", "data/ansto_proposal_calls.json"),
    ("J-PARC", "scripts/scrape_jparc.py", "data/jparc_proposal_calls.json"),
    ("PSI", "scripts/scrape_psi.py", "data/psi_proposal_calls.json"),
    ("APS", "scripts/scrape_aps.py", "data/aps_proposal_calls.json"),
    ("NSLS-II", "scripts/scrape_nsls2.py", "data/nsls2_proposal_calls.json"),
    ("DESY", "scripts/scrape_desy.py", "data/desy_proposal_calls.json"),
    ("ISIS", "scripts/scrape_isis.py", "data/isis_proposal_calls.json"),
    ("CHESS", "scripts/scrape_chess.py", "data/chess_proposal_calls.json"),
]

DATA_FILES = [data_file for _facility, _scraper, data_file in SCRAPER_JOBS]


def run_scrapers() -> tuple[int, list[dict[str, str | int | bool]]]:
    exit_code = 0
    warnings = []
    for facility, scraper, data_file in SCRAPER_JOBS:
        result = subprocess.run(
            [sys.executable, scraper],
            check=False,
            capture_output=True,
            errors="replace",
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode:
            message = last_output_line(result.stderr) or last_output_line(result.stdout) or "Unknown scraper error."
            warning = {
                "facility": facility,
                "script": scraper,
                "data_file": data_file,
                "exit_code": result.returncode,
                "used_existing_data": Path(data_file).exists(),
                "checked_at": utc_now(),
                "message": message,
            }
            warnings.append(warning)
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
    return exit_code, warnings


def last_output_line(output: str) -> str | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else None


def aggregate(output_path: Path, warnings: list[dict[str, str | int | bool]]) -> None:
    calls = []
    for file_name in DATA_FILES:
        path = Path(file_name)
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warnings.append(
                {
                    "facility": facility_name_for_data_file(file_name),
                    "script": "aggregate",
                    "data_file": file_name,
                    "exit_code": 1,
                    "used_existing_data": False,
                    "checked_at": utc_now(),
                    "message": f"Invalid JSON data file: {exc.msg}",
                }
            )
            continue
        calls.extend(payload.get("proposal_calls", []))

    calls.sort(key=lambda item: item.get("deadline_date") or "9999-12-31")
    payload = {
        "source": "all",
        "updated_at": utc_now(),
        "scrape_warnings": warnings,
        "proposal_calls": calls,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_browser_data(payload, output_path.with_name("deadline_data.js"))


def facility_name_for_data_file(file_name: str) -> str:
    for facility, _scraper, data_file in SCRAPER_JOBS:
        if data_file == file_name:
            return facility
    return file_name


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

    exit_code, warnings = run_scrapers()
    aggregate(Path(args.output), warnings)
    print(f"Wrote {args.output}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
