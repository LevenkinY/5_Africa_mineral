"""Download USGS MCS PDFs for lithium and copper (2010-2026).

Usage:
    python scripts/download_usgs_mcs.py

Outputs:
    data/USGS/mcs{year}-{commodity}.pdf

USGS changed host/path conventions over time:
- 2020-2026 use pubs.usgs.gov/periodicals/mcsYYYY/mcsYYYY-{commodity}.pdf
- 2010-2019 data sheets use d9-wret S3 and short slugs: lithi/coppe
"""

from pathlib import Path
import time

import requests

USGS_DIR = Path("data/USGS")
USGS_DIR.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2010, 2027))

COMMODITIES = {
    "lithium": {
        "modern_slug": "lithium",
        "legacy_slug": "lithi",
    },
    "copper": {
        "modern_slug": "copper",
        "legacy_slug": "coppe",
    },
}

S3_HOSTS = [
    "https://d9-wret.s3.us-west-2.amazonaws.com",
    "https://d9-wret.s3-us-west-2.amazonaws.com",
]


def candidate_urls(year: int, commodity: str) -> list[str]:
    meta = COMMODITIES[commodity]
    modern_slug = meta["modern_slug"]
    legacy_slug = meta["legacy_slug"]
    urls = []

    if year >= 2020:
        urls.extend(
            [
                f"https://pubs.usgs.gov/periodicals/mcs{year}/mcs{year}-{modern_slug}.pdf",
                f"https://pubs.usgs.gov/periodicals/mcs{year}/mcs{year}.pdf",
            ]
        )
    else:
        for host in S3_HOSTS:
            urls.extend(
                [
                    f"{host}/assets/palladium/production/atoms/files/mcs-{year}-{legacy_slug}.pdf",
                    f"{host}/assets/palladium/production/s3fs-public/atoms/files/mcs-{year}-{legacy_slug}.pdf",
                    f"{host}/assets/palladium/production/s3fs-public/media/files/mcs-{year}-{legacy_slug}.pdf",
                ]
            )

        # 2019 links are currently exposed from USGS media pages in this form.
        if year == 2019:
            urls.extend(
                [
                    f"https://d9-wret.s3-us-west-2.amazonaws.com/assets/palladium/production/atoms/files/mcs-2019-{legacy_slug}.pdf",
                    f"https://d9-wret.s3-us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/mcs-2019-{legacy_slug}.pdf",
                ]
            )

    return list(dict.fromkeys(urls))


def is_pdf(content: bytes) -> bool:
    return content[:4] == b"%PDF"


def download_one(url: str, dest: Path) -> bool:
    try:
        response = requests.get(url, timeout=45)
    except requests.RequestException as exc:
        print(f"    fail: {type(exc).__name__}")
        return False

    if response.status_code != 200:
        print(f"    HTTP {response.status_code}")
        return False
    if len(response.content) < 10_000:
        print(f"    too small ({len(response.content)} bytes)")
        return False
    if not is_pdf(response.content):
        print("    not a PDF")
        return False

    dest.write_bytes(response.content)
    return True


def download_commodity(commodity: str) -> tuple[int, int, list[int]]:
    print(f"\n{'=' * 64}")
    print(f"Downloading USGS MCS PDFs: {commodity}")
    print("=" * 64)

    success = 0
    skipped = 0
    failures = []

    for year in YEARS:
        dest = USGS_DIR / f"mcs{year}-{commodity}.pdf"
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"  {year}: exists -> {dest.name}")
            skipped += 1
            continue

        print(f"  {year}:")
        done = False
        for url in candidate_urls(year, commodity):
            print(f"    {url}")
            if download_one(url, dest):
                print(f"    saved -> {dest.name} ({dest.stat().st_size / 1024:.0f} KB)")
                success += 1
                done = True
                break
            time.sleep(0.2)

        if not done:
            failures.append(year)
            if dest.exists():
                dest.unlink()
            print("    no working URL")

    print(
        f"\n{commodity}: downloaded {success}, skipped {skipped}, failed {len(failures)}"
    )
    if failures:
        print(f"failed years: {failures}")
    return success, skipped, failures


def main():
    print("USGS MCS PDF downloader")
    print(f"Years: {min(YEARS)}-{max(YEARS)}")
    print(f"Output directory: {USGS_DIR.resolve()}")

    all_failures = {}
    for commodity in COMMODITIES:
        _, _, failures = download_commodity(commodity)
        if failures:
            all_failures[commodity] = failures

    print(f"\n{'=' * 64}")
    if all_failures:
        print("Download completed with failures:")
        for commodity, failures in all_failures.items():
            print(f"  {commodity}: {failures}")
    else:
        print("Download completed with no failures.")

    lithium_count = len(list(USGS_DIR.glob("mcs*-lithium.pdf")))
    copper_count = len(list(USGS_DIR.glob("mcs*-copper.pdf")))
    print(f"Inventory: lithium={lithium_count}, copper={copper_count}")


if __name__ == "__main__":
    main()
