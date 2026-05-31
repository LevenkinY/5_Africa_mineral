"""Comtrade 数据获取: 铜/赞比亚+刚果金铜带 镜像差额分析

输出:
- data/raw/comtrade_copper_zambia_exports.csv
- data/raw/comtrade_copper_drc_exports.csv
- data/raw/comtrade_copper_partner_imports.csv
- data/interim/comtrade_copper_mirror_gap_zambia.csv
- data/interim/comtrade_copper_mirror_gap_drc.csv
"""

import time
import pandas as pd
from config import COMTRADE_API_KEY, DATA_RAW, DATA_INTERIM, CIF_TO_FOB_FACTOR

if not COMTRADE_API_KEY:
    raise RuntimeError("COMTRADE_API_KEY 未设置")

import comtradeapicall as ct

COPPER_CODES = ["260300", "740200", "740311"]
ZAMBIA = 894
DRC = 180
CHINA = 156

KEY_PARTNERS = [
    156,   # China
    757,   # Switzerland (commodity trading hub)
    710,   # South Africa
    699,   # India
    702,   # Singapore
    276,   # Germany
]

YEARS = list(range(2018, 2024))
YRS_STR = ",".join(str(y) for y in YEARS)
DEFAULT_PARAMS = dict(partner2Code="0", customsCode="C00", motCode="0")


def fetch_with_retry(fn, desc, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = fn()
            print(f"  OK {desc} ({len(result)} 条)")
            return result
        except Exception as e:
            print(f"  !! {desc} 第{attempt+1}次失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  XX {desc} 最终失败")
                return pd.DataFrame()


def fetch_trade(flow, reporter, partner, cmd_code, desc):
    p = partner if isinstance(partner, int) else 0
    def _call():
        return ct.getFinalData(
            subscription_key=COMTRADE_API_KEY,
            typeCode="C", freqCode="A", clCode="HS",
            period=YRS_STR,
            reporterCode=reporter, partnerCode=p if flow == "X" else partner,
            cmdCode=cmd_code, flowCode=flow,
            **DEFAULT_PARAMS,
        )
    return fetch_with_retry(_call, desc)


def fetch_exporter(exporter_code, label):
    """获取单个出口国的自报出口数据。"""
    print(f"\n{'='*60}")
    print(f"A 面: {label} 自报出口")
    print("=" * 60)
    exports = []
    for code in COPPER_CODES:
        df = fetch_trade("X", exporter_code, "all", code,
                         f"{label} 出口 {code} -> World")
        if not df.empty:
            exports.append(df)
        time.sleep(0.6)
        for partner in KEY_PARTNERS:
            df_p = fetch_trade("X", exporter_code, partner, code,
                               f"{label} 出口 {code} -> {partner}")
            if not df_p.empty:
                exports.append(df_p)
            time.sleep(0.6)
    if exports:
        df_out = pd.concat(exports, ignore_index=True)
        return df_out
    print(f"  [!] {label} 出口数据缺失")
    return pd.DataFrame()


def fetch_imports_from(partner_codes, source_code, source_label):
    """伙伴国报告的从来源国进口。"""
    print(f"\n{'='*60}")
    print(f"B 面: 伙伴报从 {source_label} 进口")
    print("=" * 60)
    imports = []
    for partner in partner_codes:
        for code in COPPER_CODES:
            df = fetch_trade("M", partner, source_code, code,
                             f"Reporter={partner} 从 {source_label} 进口 {code}")
            if not df.empty:
                imports.append(df)
            time.sleep(0.6)
    if imports:
        return pd.concat(imports, ignore_index=True)
    print(f"  [!] 伙伴进口数据缺失")
    return pd.DataFrame()


def aggregate_exports_without_double_counting(df, value_name):
    """优先使用 World 汇总；World 缺失时才使用伙伴明细求和。"""
    world = (
        df[df["partnerCode"] == 0]
        .groupby(["period", "cmdCode"])["primaryValue"]
        .sum()
        .rename("world_export_fob")
    )
    detail = (
        df[df["partnerCode"] != 0]
        .groupby(["period", "cmdCode"])["primaryValue"]
        .sum()
        .rename("partner_detail_export_fob")
    )
    out = pd.concat([world, detail], axis=1)
    use_world = out["world_export_fob"].notna() & (out["world_export_fob"] != 0)
    out[value_name] = out["world_export_fob"].where(
        use_world, out["partner_detail_export_fob"]
    ).fillna(0)
    out["export_source"] = "partner_detail_sum"
    out.loc[use_world, "export_source"] = "world"
    return out[[value_name, "export_source", "world_export_fob", "partner_detail_export_fob"]]


def compute_mirror_gap(df_exports, df_imports, label):
    """计算镜像差额。"""
    if df_exports.empty and df_imports.empty:
        print(f"\n  {label}: 数据不足")
        return

    if not df_exports.empty:
        exp_agg = aggregate_exports_without_double_counting(
            df_exports, f"{label}_export_fob"
        )
    else:
        exp_agg = pd.DataFrame(columns=[f"{label}_export_fob"])

    if not df_imports.empty:
        imp_agg = (df_imports.groupby(["period", "cmdCode"])["primaryValue"]
                   .sum().rename("partner_import_cif"))
    else:
        imp_agg = pd.Series(name="partner_import_cif")

    gap = (pd.merge(exp_agg, imp_agg, on=["period", "cmdCode"], how="outer")
           .fillna(0).reset_index())
    if "export_source" in gap.columns:
        gap["export_source"] = gap["export_source"].replace(0, "no_export_record")

    gap["partner_import_fob_est"] = gap["partner_import_cif"] * CIF_TO_FOB_FACTOR
    gap["mirror_gap"] = gap["partner_import_fob_est"] - gap[f"{label}_export_fob"]
    gap["gap_pct"] = (gap["mirror_gap"] / gap["partner_import_fob_est"].replace(0, float("nan"))) * 100

    print(f"\n  {label} 镜像差额 (千美元):")
    print(gap.to_string(index=False))
    return gap


# ── 主流程 ──────────────────────────────────────────────────────────────

# 1. 赞比亚出口
df_zambia_exp = fetch_exporter(ZAMBIA, "Zambia")
if not df_zambia_exp.empty:
    df_zambia_exp.to_csv(DATA_RAW / "comtrade_copper_zambia_exports.csv", index=False)
    print(f"\n赞比亚出口: {len(df_zambia_exp)} 条, 已保存")

# 2. DRC 出口
df_drc_exp = fetch_exporter(DRC, "DRC")
if not df_drc_exp.empty:
    df_drc_exp.to_csv(DATA_RAW / "comtrade_copper_drc_exports.csv", index=False)
    print(f"\nDRC 出口: {len(df_drc_exp)} 条, 已保存")

# 3. 伙伴从赞比亚进口
df_partner_zmb = fetch_imports_from(KEY_PARTNERS, ZAMBIA, "Zambia")
if not df_partner_zmb.empty:
    df_partner_zmb.to_csv(DATA_RAW / "comtrade_copper_partner_imports_from_zambia.csv", index=False)

# 4. 伙伴从 DRC 进口
df_partner_drc = fetch_imports_from(KEY_PARTNERS, DRC, "DRC")
if not df_partner_drc.empty:
    df_partner_drc.to_csv(DATA_RAW / "comtrade_copper_partner_imports_from_drc.csv", index=False)

# 5. 镜像差额
gap_zmb = compute_mirror_gap(df_zambia_exp, df_partner_zmb, "Zambia")
if gap_zmb is not None:
    gap_zmb.to_csv(DATA_INTERIM / "comtrade_copper_mirror_gap_zambia.csv", index=False)

gap_drc = compute_mirror_gap(df_drc_exp, df_partner_drc, "DRC")
if gap_drc is not None:
    gap_drc.to_csv(DATA_INTERIM / "comtrade_copper_mirror_gap_drc.csv", index=False)

print("\nPhase 3.1 铜 Comtrade 完成")
