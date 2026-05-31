"""Comtrade 数据获取: 锂/津巴布韦 镜像差额分析 (工作流文档 4.2/6.5 节)

输出:
- data/raw/comtrade_lithium_zimbabwe_exports.csv
- data/raw/comtrade_lithium_partner_imports.csv
- data/interim/comtrade_lithium_mirror_gap.csv
"""

import time
import pandas as pd
from config import COMTRADE_API_KEY, DATA_RAW, DATA_INTERIM, CIF_TO_FOB_FACTOR

if not COMTRADE_API_KEY:
    raise RuntimeError("COMTRADE_API_KEY 未设置")

import comtradeapicall as ct

# ── 参数 ────────────────────────────────────────────────────────────────
LITHIUM_CODES = ["253090", "282520", "283691"]
ZIMBABWE = 716
CHINA = 156

KEY_PARTNERS = [
    156,   # China (最大买家)
    710,   # South Africa (转口/走私枢纽)
    784,   # UAE (转口/走私信号)
    508,   # Mozambique (邻国转口)
    56,    # Belgium
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


# ── A 面: 津巴布韦自报出口 ──────────────────────────────────────────────
print("=" * 60)
print("A 面: 津巴布韦自报出口数据")
print("=" * 60)

zwe_exports = []
for code in LITHIUM_CODES:
    df = fetch_trade("X", ZIMBABWE, "all", code,
                     f"ZWE 出口 {code} -> World")
    if not df.empty:
        zwe_exports.append(df)
    time.sleep(0.6)

    for partner in KEY_PARTNERS:
        df_p = fetch_trade("X", ZIMBABWE, partner, code,
                           f"ZWE 出口 {code} -> {partner}")
        if not df_p.empty:
            zwe_exports.append(df_p)
        time.sleep(0.6)

if zwe_exports:
    df_zwe = pd.concat(zwe_exports, ignore_index=True)
    df_zwe.to_csv(DATA_RAW / "comtrade_lithium_zimbabwe_exports.csv", index=False)
    print(f"\n津巴布韦出口数据共 {len(df_zwe)} 条, 已保存")
else:
    print("\n[!] 津巴布韦出口数据缺失, 以伙伴进口为代理")
    df_zwe = pd.DataFrame()


# ── B 面: 伙伴国报告的从津巴布韦进口 ────────────────────────────────────
print("\n" + "=" * 60)
print("B 面: 伙伴国报告的从津巴布韦进口数据")
print("=" * 60)

partner_imports = []
for partner in KEY_PARTNERS:
    for code in LITHIUM_CODES:
        df = fetch_trade("M", partner, ZIMBABWE, code,
                         f"Reporter={partner} 从 ZWE 进口 {code}")
        if not df.empty:
            partner_imports.append(df)
        time.sleep(0.6)

if partner_imports:
    df_partner = pd.concat(partner_imports, ignore_index=True)
    df_partner.to_csv(DATA_RAW / "comtrade_lithium_partner_imports.csv", index=False)
    print(f"\n伙伴进口数据共 {len(df_partner)} 条, 已保存")
else:
    print("\n[!] 伙伴国进口数据也缺失")
    df_partner = pd.DataFrame()


# ── 镜像差额计算 ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("镜像差额计算")
print("=" * 60)

if not df_zwe.empty and not df_partner.empty:
    zwe_agg = aggregate_exports_without_double_counting(df_zwe, "zwe_export_fob")
    partner_agg = (df_partner.groupby(["period", "cmdCode"])["primaryValue"]
                   .sum().rename("partner_import_cif"))

    gap = (pd.merge(zwe_agg, partner_agg, on=["period", "cmdCode"], how="outer")
           .fillna(0).reset_index())
    gap["export_source"] = gap["export_source"].replace(0, "no_export_record")

    gap["partner_import_fob_est"] = gap["partner_import_cif"] * CIF_TO_FOB_FACTOR
    gap["mirror_gap"] = gap["partner_import_fob_est"] - gap["zwe_export_fob"]
    gap["gap_pct"] = (gap["mirror_gap"] / gap["partner_import_fob_est"].replace(0, float("nan"))) * 100

    gap.to_csv(DATA_INTERIM / "comtrade_lithium_mirror_gap.csv", index=False)
    print("\n镜像差额汇总 (千美元): ")
    print(gap.to_string(index=False))
elif df_zwe.empty and not df_partner.empty:
    print("\n津巴布韦无申报, 以伙伴进口汇总为代理")
    partner_summary = (df_partner.groupby(["period", "cmdCode"])["primaryValue"]
                       .sum().reset_index())
    partner_summary.to_csv(DATA_INTERIM / "comtrade_lithium_partner_proxy.csv", index=False)
    print(partner_summary.to_string(index=False))
else:
    print("\n数据不足")

print("\nPhase 2.1 锂/津巴布韦 Comtrade 完成")
