"""从 USGS MCS PDF 中批量提取 DRC 钴矿产量数据。

用法: python scripts/extract_usgs_mcs.py
输入: data/USGS/mcs*.pdf
输出: data/raw/usgs_cobalt_production_extracted.csv
"""

import re
import pdfplumber
from pathlib import Path
import pandas as pd

USGS_DIR = Path("data/USGS")
OUTPUT = Path("data/raw/usgs_cobalt_production_extracted.csv")

# MCS 出版年份 → 数据年份映射 (MCS published in year X, contains data up to year X-1)
# 每个 MCS 的表格通常显示最近 2 年, 取第一个(非估计值)作为该年数据


def extract_mcs_year_from_filename(filename):
    """从文件名推断 MCS 出版年份和数据年份。"""
    # 文件名如: mcs-2015-cobal.pdf, mcs2024-cobalt.pdf
    match = re.search(r"20(\d{2})", filename)
    if match:
        mcs_year = 2000 + int(match.group(1))
        return mcs_year
    return None


def extract_production_table(pdf_path):
    """从单个 MCS PDF 中提取 World Mine Production 表格。"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # 找到 "World Mine Production and Reserves" 表格段落后, 找 DRC 行
    # 注意: 必须用完整标题, 因为正文中也会出现 "mine production"
    sections = full_text.split("World Mine Production and Reserves")
    if len(sections) < 2:
        return None

    # 在表格段落中搜索 DRC
    post = sections[1]
    # 限制在下一个大标题之前 (如 "World Resources")
    for cutoff in ["World Resources", "Events, Trends", "Substitutes"]:
        if cutoff in post:
            post = post.split(cutoff)[0]

    # 匹配 Congo (Kinshasa) 数据行 (注意: 注释中也含此字串, 须匹配带产量的行)
    # 格式: "Congo (Kinshasa)   e119,000   130,000   4,000,000"
    # 或:    "Congo (Kinshasa)   144,000    170,000   6,000,000"
    drc_matches = list(re.finditer(
        r"Congo\s*\(Kinshasa\)\s+(e?[\d,]+)\s+([\d,]+)",
        post
    ))
    if not drc_matches:
        return None

    # 取最后一个匹配 (注释中的匹配在前, 数据行在后)
    drc_line = drc_matches[-1].group(0)
    # 从整个数据行提取数字, 而不是仅从 regex group
    # 数据行可能还有第三个数字(储量)

    # 提取所有数字 (含逗号格式)
    numbers = re.findall(r"([\d,]+)", drc_line)
    vals = []
    for n in numbers:
        n_clean = n.replace(",", "").strip()
        if not n_clean:
            continue
        try:
            v = int(n_clean)
        except ValueError:
            continue
        # 产量值通常在 1,000–500,000 范围; 储量在百万级
        # 取前几个在合理产量范围的值
        if 1000 < v < 500000:
            vals.append(v)

    if len(vals) >= 1:
        return vals
    return None


def extract_column_years(pdf_path):
    """从 PDF 中提取 World Mine Production 表的列年份。"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # 查找 "World Mine Production" 附近的年份行
    # 模式: "Mine productione Reserves9" 下面一行是年份, 如 "2022 2023"
    # 更通用: 找 "Mine production" 后紧跟的数字年份
    section = full_text.split("World Mine Production and Reserves")
    if len(section) < 2:
        return None

    post_section = section[1][:500]

    # 查找 20XX 年份模式
    years = re.findall(r"\b(20[1-2]\d)\b", post_section)
    return [int(y) for y in years]


def batch_extract():
    """批量提取所有年份数据。"""
    pdf_files = sorted(USGS_DIR.glob("mcs*cobalt*.pdf")) + sorted(USGS_DIR.glob("mcs*cobal*.pdf"))
    # 去重
    pdf_files = list(dict.fromkeys(pdf_files))

    print(f"找到 {len(pdf_files)} 个 MCS PDF 文件")

    records = {}  # data_year → production_tons

    for pdf_path in pdf_files:
        fname = pdf_path.name
        mcs_year = extract_mcs_year_from_filename(fname)
        if mcs_year is None:
            print(f"  ? {fname}: 无法推断 MCS 年份")
            continue

        values = extract_production_table(pdf_path)
        years = extract_column_years(pdf_path)

        if values is None:
            print(f"  ✗ {fname} (MCS {mcs_year}): 未找到 DRC 数据")
            continue

        if years is None:
            # 默认: MCS 年份包含 data_year = mcs_year-1 为主列第一列 = mcs_year-2
            years = [mcs_year - 2, mcs_year - 1]

        print(f"  ✓ {fname} (MCS {mcs_year}): {dict(zip(years[:len(values)], values))}")

        for i, val in enumerate(values):
            if i < len(years):
                data_year = years[i]
                # 对于每个数据年份, 取最新的 MCS 报告值 (后来的 MCS 可能修正)
                if data_year not in records or data_year >= mcs_year - 2:
                    records[data_year] = val

    # 整理输出
    df = pd.DataFrame(
        sorted(records.items()),
        columns=["year", "drc_mine_production_t"]
    )
    df = df[df["year"] >= 2005].sort_values("year")  # 过滤不合理年份
    df.to_csv(OUTPUT, index=False)

    print(f"\n提取结果 ({len(df)} 个年份):")
    for _, row in df.iterrows():
        print(f"  {int(row['year'])}: {int(row['drc_mine_production_t']):,} tonnes")

    print(f"\n数据已保存至 {OUTPUT}")
    return df


if __name__ == "__main__":
    batch_extract()
