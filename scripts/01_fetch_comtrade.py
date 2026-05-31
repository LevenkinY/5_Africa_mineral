"""Comtrade 数据获取: 钴/DRC 镜像差额分析 (工作流文档 6.3 节)

输出:
- data/raw/comtrade_cobalt_drc_exports.csv   DRC 自报出口
- data/raw/comtrade_cobalt_partner_imports.csv 伙伴国报告的从 DRC 进口
- data/interim/comtrade_cobalt_mirror_gap.csv  镜像差额汇总

注意: DRC 对 Comtrade 申报可能极不完整, 这本身就是信息黑箱的实证。
"""

import time
import pandas as pd
from config import (
    COMTRADE_API_KEY,
    DATA_RAW,
    DATA_INTERIM,
    COUNTRY,
    HS_CODES,
    CIF_TO_FOB_FACTOR,
)

if not COMTRADE_API_KEY:
    raise RuntimeError("COMTRADE_API_KEY 未设置, 请创建 .env 文件 (参考 .env.example)")

import comtradeapicall as ct

# ── 参数 ────────────────────────────────────────────────────────────────
COBALT_CODES = list(HS_CODES["cobalt"].values())  # ["260500","282200","810520"]
DRC = 180
CHINA = 156

# DRC 钴的主要贸易伙伴 (用于多边镜像)
KEY_PARTNERS = [156, 894, 710, 246, 56]  # China, Zambia, South Africa, Finland, Belgium

YEARS = list(range(2018, 2024))  # 2018-2023
YRS_STR = ",".join(str(y) for y in YEARS)

# API 默认参数 (comtradeapicall 新版必填)
DEFAULT_PARAMS = dict(
    partner2Code="0",
    customsCode="C00",
    motCode="0",
)


def fetch_with_retry(fn, desc, max_retries=3):
    """带重试的 API 调用, Comtrade 免费档有时限流。"""
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
                print(f"  XX {desc} 最终失败, 返回空 DataFrame")
                return pd.DataFrame()


def fetch_trade(flow, reporter, partner, cmd_code, desc):
    """抓取单条贸易流。partner 可以是国家码或 'all'。"""
    p = partner if isinstance(partner, int) else 0
    def _call():
        return ct.getFinalData(
            subscription_key=COMTRADE_API_KEY,
            typeCode="C",
            freqCode="A",
            clCode="HS",
            period=YRS_STR,
            reporterCode=reporter,
            partnerCode=p if flow == "X" else partner,
            cmdCode=cmd_code,
            flowCode=flow,
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


# ── A 面: DRC 自报出口 ──────────────────────────────────────────────────
print("=" * 60)
print("A 面: DRC 自报出口数据")
print("=" * 60)

drc_exports = []
for code in COBALT_CODES:
    # 对 World
    df = fetch_trade("X", DRC, "all", code,
                     f"DRC 出口 {code} -> World")
    if not df.empty:
        drc_exports.append(df)
    time.sleep(0.6)

    # 对主要伙伴
    for partner in KEY_PARTNERS:
        df_p = fetch_trade("X", DRC, partner, code,
                           f"DRC 出口 {code} -> {partner}")
        if not df_p.empty:
            drc_exports.append(df_p)
        time.sleep(0.6)

if drc_exports:
    df_drc = pd.concat(drc_exports, ignore_index=True)
    df_drc.to_csv(DATA_RAW / "comtrade_cobalt_drc_exports.csv", index=False)
    print(f"\nDRC 出口数据共 {len(df_drc)} 条, 已保存至 data/raw/")
else:
    print("\n[!] DRC 出口数据完全缺失 -- 这本身就是信息黑箱的直接证据!")
    print("    转而以伙伴国进口数据作为 DRC 出口的代理。")
    df_drc = pd.DataFrame()


# ── B 面: 伙伴国报告的从 DRC 进口 ────────────────────────────────────────
print("\n" + "=" * 60)
print("B 面: 伙伴国报告的从 DRC 进口数据")
print("=" * 60)

partner_imports = []
for partner in KEY_PARTNERS:
    for code in COBALT_CODES:
        df = fetch_trade("M", partner, DRC, code,
                         f"Reporter={partner} 从 DRC 进口 {code}")
        if not df.empty:
            partner_imports.append(df)
        time.sleep(0.6)

if partner_imports:
    df_partner = pd.concat(partner_imports, ignore_index=True)
    df_partner.to_csv(DATA_RAW / "comtrade_cobalt_partner_imports.csv", index=False)
    print(f"\n伙伴进口数据共 {len(df_partner)} 条, 已保存至 data/raw/")
else:
    print("\n[!] 伙伴国进口数据也缺失")
    df_partner = pd.DataFrame()


# ── 镜像差额计算 ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("镜像差额计算 (伙伴报进口 vs DRC 报出口)")
print("=" * 60)

if not df_drc.empty and not df_partner.empty:
    # 聚合到 年度 x HS码 粒度；避免 World 汇总与伙伴明细重复计算
    drc_agg = aggregate_exports_without_double_counting(df_drc, "drc_export_fob")

    partner_agg = (df_partner
                   .groupby(["period", "cmdCode"])["primaryValue"]
                   .sum()
                   .rename("partner_import_cif"))

    gap = (pd.merge(drc_agg, partner_agg, on=["period", "cmdCode"], how="outer")
           .fillna(0)
           .reset_index())
    gap["export_source"] = gap["export_source"].replace(0, "no_export_record")

    gap["partner_import_fob_est"] = gap["partner_import_cif"] * CIF_TO_FOB_FACTOR
    gap["mirror_gap"] = gap["partner_import_fob_est"] - gap["drc_export_fob"]
    gap["gap_pct"] = (gap["mirror_gap"] / gap["partner_import_fob_est"].replace(0, float("nan"))) * 100

    gap.to_csv(DATA_INTERIM / "comtrade_cobalt_mirror_gap.csv", index=False)

    print("\n镜像差额汇总 (千美元): ")
    print(gap.to_string(index=False))
    print(f"\n数据已保存至 data/interim/comtrade_cobalt_mirror_gap.csv")
elif df_drc.empty and not df_partner.empty:
    print("\nDRC 无申报数据, 无法计算镜像差额。")
    print("将以伙伴国进口汇总作为 DRC 出口的代理估计。")
    partner_summary = (df_partner
                       .groupby(["period", "cmdCode"])["primaryValue"]
                       .sum()
                       .reset_index())
    partner_summary.to_csv(DATA_INTERIM / "comtrade_cobalt_partner_proxy.csv", index=False)
    print(partner_summary.to_string(index=False))
else:
    print("\n数据不足, 无法进行镜像差额分析。")

print("\nPhase 1.1 Comtrade 数据获取完成")
