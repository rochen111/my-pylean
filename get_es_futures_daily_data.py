#!/usr/bin/env python3
"""Download full daily ES futures history from Stooq (HTML scraping) and save to CSV."""

from __future__ import annotations

from pathlib import Path
import re
import time
from html import unescape

import pandas as pd
import requests


TICKER = "es.f"
BASE_URL = "https://stooq.com/q/d/?s={ticker}&i=d&l={page}"
OUTPUT_CSV = "es_futures_daily_data.csv"
PARTIAL_OUTPUT_CSV = "es_futures_daily_data.partial.csv"
PAGE_DELAY_SECS = 3  # polite delay between paginated requests
CACHE_DIR = Path(".stooq_cache_es_f_daily")


def fetch_page_html(page: int) -> str:
    url = BASE_URL.format(ticker=TICKER, page=page)
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def extract_last_page(html: str) -> int:
    matches = re.findall(r"q/d/\?s=es\.f&i=d&l=(\d+)", html)
    return max([int(m) for m in matches], default=1)


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_history_table(html: str) -> pd.DataFrame:
    if "Exceeded the daily site hits limit" in html:
        raise RuntimeError(
            "Stooq is rate-limiting this IP (daily hit limit).\n"
            "Wait a few hours and retry:\n"
            "  python3 get_es_futures_daily_data.py"
        )

    match = re.search(
        r"<table[^>]*id\s*=\s*['\"]?fth1['\"]?[^>]*>(.*?)</table>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError("Stooq history table not found on page")

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", match.group(1), flags=re.IGNORECASE | re.DOTALL)
    records = []
    for row in rows:
        cells_raw = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
        cells = [_strip_tags(c) for c in cells_raw]
        if len(cells) < 9:
            continue

        # Row shape: No., Date, Open, High, Low, Close, Change%, ChangeAbs, Volume, OpenInterest
        if cells[0].lower() == "no.":
            continue
        records.append(
            {
                "date": cells[1],
                "open": cells[2],
                "high": cells[3],
                "low": cells[4],
                "close": cells[5],
                "volume": cells[8],
            }
        )

    if not records:
        raise ValueError("No price rows found in Stooq history table")

    out = pd.DataFrame.from_records(records)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["date", "open", "high", "low", "close"])
    return out


def cache_file_for_page(page: int) -> Path:
    return CACHE_DIR / f"page_{page:04d}.csv"


def save_page_cache(page: int, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_file_for_page(page), index=False)


def load_cached_frames(last_page: int) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for page in range(1, last_page + 1):
        page_file = cache_file_for_page(page)
        if not page_file.exists():
            continue
        cached_df = pd.read_csv(page_file, parse_dates=["date"])
        frames.append(cached_df)
    return frames


def fetch_es_futures_daily_data() -> tuple[pd.DataFrame, bool, int, int]:
    first_html = fetch_page_html(page=1)
    last_page = extract_last_page(first_html)
    print(f"  Total pages: {last_page}")

    completed_pages = 0

    page1_cache = cache_file_for_page(1)
    if not page1_cache.exists():
        save_page_cache(1, parse_history_table(first_html))
    completed_pages += 1

    rate_limited = False
    for page in range(2, last_page + 1):
        page_cache = cache_file_for_page(page)
        if page_cache.exists():
            completed_pages += 1
            continue

        time.sleep(PAGE_DELAY_SECS)
        html = fetch_page_html(page=page)
        try:
            page_df = parse_history_table(html)
        except RuntimeError:
            rate_limited = True
            break

        save_page_cache(page, page_df)
        completed_pages += 1
        print(f"  page {page}/{last_page}")

    frames = load_cached_frames(last_page)
    if not frames:
        raise RuntimeError("No cached Stooq page data available.")

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["date"], keep="first")
    df = df.sort_values("date").reset_index(drop=True)
    complete = completed_pages == last_page and not rate_limited
    return df, complete, completed_pages, last_page


def main() -> None:
    print(f"Fetching {TICKER.upper()} daily history from Stooq...")
    try:
        df, complete, completed_pages, last_page = fetch_es_futures_daily_data()
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from None

    if complete:
        df.to_csv(OUTPUT_CSV, index=False)
        output_file = OUTPUT_CSV
    else:
        df.to_csv(PARTIAL_OUTPUT_CSV, index=False)
        output_file = PARTIAL_OUTPUT_CSV

    print(f"Ticker : {TICKER.upper()}")
    print(f"Saved  : {len(df):,} rows -> {output_file}")
    print(f"Range  : {df['date'].min().date()} -> {df['date'].max().date()}")
    print(df.tail(3).to_string(index=False))

    if not complete:
        print(f"Progress: {completed_pages}/{last_page} pages cached in {CACHE_DIR}")
        print("Rerun the same command to continue from cached pages.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
