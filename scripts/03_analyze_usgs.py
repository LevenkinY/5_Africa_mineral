"""USGS 产量锚 + 物理对账: 钴/DRC 走私与非正规缺口估算 (工作流文档 6.4 节)

前置: 运行 extract_usgs_mcs.py 和 01_fetch_comtrade.py

USGS 数据来源: Mineral Commodity Summaries (MCS) 2011-2025, 由 extract_usgs_mcs.py 提取

输出:
- data/interim/usgs_cobalt_physical_gap.csv  产量 vs 报关出口的实物缺口
- outputs/figures/usgs_cobalt_physical_gap.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_RAW, DATA_INTERIM, OUTPUT_FIGURES, CO_CONTENT

# USGS 提取数据路径
USGS_EXTRACTED = DATA_RAW / "usgs_cobalt_production_extracted.csv"


def load_production_data():
    """加载 USGS MCS 提取的产量数据。"""
    if not USGS_EXTRACTED.exists():
        raise FileNotFoundError(
            f"未找到 {USGS_EXTRACTED}，请先运行 scripts/extract_usgs_mcs.py"
        )
    df = pd.read_csv(USGS_EXTRACTED)
    print(f"USGS MCS 产量数据 ({len(df)} 个年份, 来源: MCS 官方 PDF):")
    return df


def load_comtrade_trade_volumes():
    """从 Comtrade 数据中提取报关出口实物量，仅用 World 汇总 (避免重复)。"""
    exports_path = DATA_RAW / "comtrade_cobalt_drc_exports.csv"

    if not exports_path.exists():
        print("[!] 未找到 Comtrade 数据, 跳过物理对账。请先运行 01_fetch_comtrade.py")
        return None

    df = pd.read_csv(exports_path)
    # 只用 World 汇总 (partnerCode=0)
    df = df[df["partnerCode"] == 0].copy()
    print(f"  DRC 出口 World 汇总: {len(df)} 条")

    df["cmdCode"] = df["cmdCode"].astype(str).str.zfill(6)
    # qty 单位为 kg, 转换为吨
    df["qty_tonnes"] = df["qty"] / 1000

    vol = (
        df.groupby(["period", "cmdCode"])["qty_tonnes"]
        .sum()
        .unstack("cmdCode")
    )
    vol.index.name = "year"
    vol.columns.name = None

    # 只保留钴相关的 HS 码
    cobalt_codes = list(CO_CONTENT.keys())
    vol = vol[[c for c in cobalt_codes if c in vol.columns]]
    return vol


def compute_physical_gap(production, trade_vol):
    """计算产量 vs 报关出口的实物缺口 (均换算为钴金属含量吨)。"""
    if trade_vol is None or trade_vol.empty:
        return None

    # 将贸易量换算为钴含量吨
    trade_co = pd.DataFrame(index=trade_vol.index)
    for code, co_pct in CO_CONTENT.items():
        if code in trade_vol.columns:
            trade_co[code] = trade_vol[code] * co_pct
            print(f"  {code}: Co含量系数 {co_pct*100:.0f}%, 折算后 {trade_co[code].sum():,.0f} 吨 Co")

    trade_co["total_export_co_t"] = trade_co.sum(axis=1)

    # 合并
    gap = (
        production.merge(trade_co, left_on="year", right_index=True, how="outer")
        .sort_values("year")
    )

    gap["physical_gap_t"] = gap["drc_mine_production_t"] - gap["total_export_co_t"]
    gap["gap_pct_of_production"] = (
        gap["physical_gap_t"] / gap["drc_mine_production_t"] * 100
    )

    # 负缺口 = 出口 > 产量 = 可能原因:
    # (1) 产量低估 (手工采矿未纳入 USGS)
    # (2) 含量系数偏高
    # (3) 贸易量含转口/重复申报
    # (4) qty 字段质量问题
    gap.to_csv(DATA_INTERIM / "usgs_cobalt_physical_gap.csv", index=False)
    return gap


def plot_physical_gap(gap):
    """绘制产量 vs 报关出口对照图。"""
    if gap is None or gap.empty:
        print("[!] 无数据, 跳过绘图")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 左: 产量 vs 报关出口 (钴含量吨)
    ax = axes[0]
    ax.fill_between(
        gap["year"], gap["drc_mine_production_t"],
        alpha=0.3, label="USGS Mine Production (Co content)"
    )
    ax.fill_between(
        gap["year"], gap["total_export_co_t"],
        alpha=0.3, label="Declared Exports (Co-equiv from trade qty)"
    )
    ax.plot(gap["year"], gap["drc_mine_production_t"], marker="o", color="#2c3e50", linewidth=2)
    ax.plot(gap["year"], gap["total_export_co_t"], marker="s", color="#c0392b", linewidth=1.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Tonnes (Co metal content)")
    ax.set_title("DRC Cobalt: USGS Mine Production vs Declared Exports")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # 右: 缺口 (产量 - 出口) → 负值 = 出口超产量
    ax = axes[1]
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in gap["physical_gap_t"].fillna(0)]
    ax.bar(gap["year"], gap["physical_gap_t"], color=colors)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap (tonnes Co content)")
    ax.set_title("Physical Gap: Production - Declared Exports\n(negative = exports exceed production)")
    ax.grid(True, alpha=0.3, axis="y")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # 标注解释
    ax.text(
        0.5, -0.15,
        "Negative gap may indicate: (1) artisanal mining undercount, "
        "(2) Co content factor inaccuracy, (3) trade qty issues",
        transform=ax.transAxes, fontsize=8, ha="center", style="italic"
    )

    fig.suptitle("DRC Cobalt: Physical Reconciliation (USGS MCS + Comtrade)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "usgs_cobalt_physical_gap.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  实物缺口图 → {out_path}")
    return fig


def main():
    print("=" * 60)
    print("Phase 1.3: USGS 产量锚 + 物理对账")
    print("=" * 60)

    # ── 产量数据 ──
    print("\n[USGS] DRC 钴矿产量 (来自 MCS 官方 PDF):")
    production = load_production_data()
    print(production.to_string(index=False))

    # ── 贸易量 ──
    print("\n[对账] 报关出口实物量 (吨):")
    trade_vol = load_comtrade_trade_volumes()
    if trade_vol is not None:
        print(trade_vol.to_string())

    # ── 缺口计算 ──
    print("\n[缺口分析]:")
    gap = compute_physical_gap(production, trade_vol)
    if gap is not None:
        cols = [
            "year", "drc_mine_production_t", "total_export_co_t",
            "physical_gap_t", "gap_pct_of_production"
        ]
        valid = gap[cols].dropna(subset=["drc_mine_production_t", "total_export_co_t"])
        print(valid.to_string(index=False))
        plot_physical_gap(gap)

        # 诊断
        above = (valid["physical_gap_t"] < 0).sum()
        total = len(valid)
        if above > 0:
            print(
                f"\n[诊断] {above}/{total} 个年份的报关出口量超过 USGS 矿山产量。\n"
                "  可能原因: (1) USGS 产量仅计正规矿山, 手工采矿 (ASM) 未完全纳入;\n"
                "          (2) 钴含量转换系数需按实际商品品位调整;\n"
                "          (3) Comtrade qty 可能存在单位或申报偏差。\n"
                "  这在方法层面可被视为 '产量黑洞' 的量化信号。"
            )

    print("\nPhase 1.3 USGS 分析完成")


if __name__ == "__main__":
    main()
