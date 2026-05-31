"""Extract lithium and copper mine production from USGS MCS PDFs.

Inputs:
- data/USGS/mcs*-lithi*.pdf / mcs*-lithium.pdf
- data/USGS/mcs*-coppe*.pdf / mcs*-copper.pdf

Outputs:
- data/raw/usgs_lithium_production_extracted.csv
- data/raw/usgs_copper_production_extracted.csv

USGS MCS publication year X normally reports mine production for X-2 and X-1.
When later MCS reports revise prior-year estimates, this script keeps the
latest available value by iterating files in publication-year order.
"""

import re
from pathlib import Path

import pandas as pd
import pdfplumber


USGS_DIR = Path("data/USGS")
DATA_RAW = Path("data/raw")


COMMODITIES = {
    "lithium": {
        "patterns": ["mcs*lithi*.pdf", "mcs*lithium*.pdf"],
        "countries": {
            "Zimbabwe": "zimbabwe_mine_production_li_t",
        },
        "output": DATA_RAW / "usgs_lithium_production_extracted.csv",
        "unit_multiplier": 1,
    },
    "copper": {
        "patterns": ["mcs*coppe*.pdf", "mcs*copper*.pdf"],
        "countries": {
            "Zambia": "zambia_mine_production_cu_t",
            "Congo (Kinshasa)": "drc_mine_production_cu_t",
        },
        "output": DATA_RAW / "usgs_copper_production_extracted.csv",
        # Copper MCS tables are "Data in thousand metric tons, copper content".
        "unit_multiplier": 1000,
    },
}


def extract_mcs_year(filename: str) -> int | None:
    match = re.search(r"20\d{2}", filename)
    return int(match.group(0)) if match else None


def pdf_text(pdf_path: Path) -> str:
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_world_table_text(text: str) -> str | None:
    markers = [
        "World Mine Production and Reserves",
        "World Mine and Refinery Production and Reserves",
    ]
    starts = [text.find(marker) for marker in markers if text.find(marker) >= 0]
    if not starts:
        return None
    section = text[min(starts):]
    for cutoff in ["World Resources", "Substitutes", "Events, Trends"]:
        idx = section.find(cutoff)
        if idx > 0:
            section = section[:idx]
            break
    return section


def extract_column_years(section: str, mcs_year: int) -> list[int]:
    years = [int(y) for y in re.findall(r"\b(20[0-2]\d)e?\b", section[:600])]
    # Keep years near the MCS publication year and preserve first occurrence.
    out = []
    for year in years:
        if mcs_year - 4 <= year <= mcs_year and year not in out:
            out.append(year)
    if len(out) >= 2:
        return out[:2]
    return [mcs_year - 2, mcs_year - 1]


def parse_numeric_token(token: str) -> int | None:
    token = token.strip().replace(",", "")
    token = token.replace("e", "").replace("E", "")
    token = token.replace("W", "").replace("—", "").replace("-", "")
    if not token:
        return None
    if not re.fullmatch(r"\d+", token):
        return None
    return int(token)


def find_country_values(section: str, country: str) -> list[int] | None:
    pattern = re.compile(rf"^{re.escape(country)}\s+(.+)$", re.MULTILINE)
    for match in pattern.finditer(section):
        row = match.group(1)
        tokens = re.findall(r"[eE]?\d[\d,]*|W|—|-", row)
        values = []
        for token in tokens:
            value = parse_numeric_token(token)
            if value is not None:
                values.append(value)
        if len(values) >= 2:
            return values[:2]
    return None


def pdf_files_for(commodity: str) -> list[Path]:
    files = []
    for pattern in COMMODITIES[commodity]["patterns"]:
        files.extend(sorted(USGS_DIR.glob(pattern)))
    unique = {p.name: p for p in files}
    return sorted(unique.values(), key=lambda p: (extract_mcs_year(p.name) or 0, p.name))


def extract_commodity(commodity: str) -> pd.DataFrame:
    meta = COMMODITIES[commodity]
    records: dict[int, dict[str, int | str]] = {}
    files = pdf_files_for(commodity)

    print(f"\n{commodity}: found {len(files)} PDFs")
    for pdf_path in files:
        mcs_year = extract_mcs_year(pdf_path.name)
        if mcs_year is None:
            print(f"  ? {pdf_path.name}: cannot infer MCS year")
            continue

        text = pdf_text(pdf_path)
        section = extract_world_table_text(text)
        if section is None:
            print(f"  x {pdf_path.name}: world production table not found")
            continue

        years = extract_column_years(section, mcs_year)
        found = {}
        for country, col in meta["countries"].items():
            values = find_country_values(section, country)
            if values is None:
                continue
            for year, value in zip(years, values):
                records.setdefault(year, {"year": year})
                records[year][col] = value * meta["unit_multiplier"]
                records[year][f"{col}_source_mcs_year"] = mcs_year
                records[year][f"{col}_source_file"] = pdf_path.name
            found[country] = dict(zip(years[: len(values)], values))

        print(f"  ok {pdf_path.name} (MCS {mcs_year}): {found}")

    df = pd.DataFrame(sorted(records.values(), key=lambda d: d["year"]))
    df = df[df["year"] >= 2005].sort_values("year")
    df.to_csv(meta["output"], index=False)
    print(f"\n{commodity}: wrote {meta['output']} ({len(df)} years)")
    print(df.to_string(index=False))
    return df


def main():
    for commodity in ["lithium", "copper"]:
        extract_commodity(commodity)


if __name__ == "__main__":
    main()
