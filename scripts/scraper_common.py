from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan\\.?|Feb\\.?|Mar\\.?|Apr\\.?|May|Jun\\.?|Jul\\.?|Aug\\.?|Sep\\.?|Sept\\.?|Oct\\.?|Nov\\.?|Dec\\.?"
)


@dataclass
class ProposalCall:
    facility: str
    call_type: str
    title: str
    status: str
    deadline_text: str | None
    deadline_date: str | None
    deadline_time: str | None
    timezone: str | None
    source_url: str
    fetched_at: str


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "td", "th"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "td", "th"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        text = unescape(" ".join(self.parts)).replace("\xa0", " ")
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        return re.sub(r"\s+", " ", text).strip()


class LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = urljoin(self.base_url, href)
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href:
            text = normalize_text(" ".join(self._current_text))
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; proposal-deadline-scraper/0.2)"},
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def html_to_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    return parser.text()


def html_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = LinkParser(base_url)
    parser.feed(html)
    return parser.links


def normalize_text(text: str) -> str:
    text = unescape(text).replace("\xa0", " ")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def write_payload(source: str, calls: list[ProposalCall], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    updated_at = calls[0].fetched_at if calls else utc_now()
    payload = {
        "source": source,
        "updated_at": updated_at,
        "proposal_calls": [asdict(call) for call in calls],
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_deadline(deadline_text: str) -> tuple[str | None, str | None, str | None]:
    text = normalize_text(deadline_text)
    parsed_date = parse_date(text)
    parsed_time = parse_time(text)
    tz = parse_timezone(text)
    return parsed_date.isoformat() if parsed_date else None, parsed_time, tz


def parse_date(text: str) -> date | None:
    range_end = re.search(
        rf"\b(?:from\s+)?(?P<start_month>{MONTHS})\s+\d{{1,2}}\s*-\s*"
        rf"(?P<month>{MONTHS})\s+(?P<day>\d{{1,2}}),?\s+(?P<year>\d{{4}})\b",
        text,
        re.IGNORECASE,
    )
    if range_end:
        return parse_date_parts(range_end.group("year"), range_end.group("month"), range_end.group("day"))

    month_first = re.search(
        rf"\b(?P<month>{MONTHS})\s+(?P<day>\d{{1,2}}),?\s+(?P<year>\d{{4}})\b",
        text,
        re.IGNORECASE,
    )
    if month_first:
        return parse_date_parts(
            month_first.group("year"), month_first.group("month"), month_first.group("day")
        )

    day_first = re.search(
        rf"\b(?P<day>\d{{1,2}})\s+(?P<month>{MONTHS})\s+(?P<year>\d{{4}})\b",
        text,
        re.IGNORECASE,
    )
    if day_first:
        return parse_date_parts(day_first.group("year"), day_first.group("month"), day_first.group("day"))

    return None


def parse_date_parts(year: str, month: str, day: str) -> date:
    month_key = month.lower().rstrip(".")
    month_number = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }[month_key]
    return date(int(year), month_number, int(day))


def parse_time(text: str) -> str | None:
    time_24h = re.search(r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})\b", text)
    if time_24h:
        return f"{int(time_24h.group('hour')):02d}:{int(time_24h.group('minute')):02d}"

    time_ampm = re.search(r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>a\.?m\.?|p\.?m\.?|am|pm)\b", text, re.IGNORECASE)
    if time_ampm:
        hour = int(time_ampm.group("hour"))
        minute = int(time_ampm.group("minute") or 0)
        ampm = time_ampm.group("ampm").lower().replace(".", "")
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    return None


def parse_timezone(text: str) -> str | None:
    timezone_match = re.search(
        r"\b(Japan Time|UTC\+09:00|AEST|AEDT|Chicago time|Central time|CT|Eastern time|ET|EST|EDT|CET|CEST|BST|GMT)\b",
        text,
        re.IGNORECASE,
    )
    return timezone_match.group(1) if timezone_match else None


def is_future_or_today(deadline_date: str | None) -> bool:
    if not deadline_date:
        return False
    return date.fromisoformat(deadline_date) >= today_utc()
