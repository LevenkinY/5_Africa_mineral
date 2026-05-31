"""BACI 数据分析: 铜/赞比亚+DRC 加价阶梯 + 价值流向

铜的特殊性: 赞比亚有部分本地冶炼/精炼 → 与钴/锂"纯原料外流"对照
HS 阶梯: 260300(矿石) → 740200(粗铜) → 740311(阴极铜)

输出:
- data/interim/baci_copper_ladder_zambia.csv
- data/interim/baci_copper_ladder_drc.csv
- data/interim/baci_copper_ladder_china.csv
- data/interim/baci_copper_flows_*.csv
- outputs/figures/baci_copper_ladder.png
- outputs/figures/baci_copper_flows.png
"""

import os, glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_INTERIM, OUTPUT_FIGURES, PROJECT_ROOT

BACI_DIR = PROJECT_ROOT / "data" / "BACI_HS17_V202601"
COPPER_CODES = ["260300", "740200", "740311"]
HS_LABELS = {
    "260300": "Ore/Concentrate\n(260300)",
    "740200": "Blister/Anode\n(740200)",
    "740311": "Refined Cathode\n(740311)",
}
ZAMBIA = 894
DRC = 180
CHINA = 156


def load_country_codes():
    f = BACI_DIR / "country_codes_V202601.csv"
    if f.exists():
        df = pd.read_csv(f)
        return dict(zip(df["country_code"], df["country_name"]))
    return {}


def load_baci():
    csv_files = sorted(glob.glob(str(BACI_DIR / "BACI_HS17_Y20*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"未在 {BACI_DIR} 找到 BACI CSV")

    print(f"加载 {len(csv_files)} 个 BACI 文件...")
    frames = []
    for f in csv_files:
        df = pd.read_csv(f, dtype={"k": str})
        mask = (
            df["k"].isin(COPPER_CODES)
            & (df["i"].isin([ZAMBIA, DRC, CHINA]) | df["j"].isin([ZAMBIA, DRC, CHINA]))
        )
        df = df[mask]
        if len(df):
            frames.append(df)
        print(f"  {os.path.basename(f)}: {len(df)} 条")

    if not frames:
        raise ValueError("BACI 中未找到铜相关记录")
    baci = pd.concat(frames, ignore_index=True)
    print(f"  共 {len(baci)} 条铜相关记录\n")
    return baci


def compute_ladder(baci, exporter):
    co = baci[(baci.i == exporter) & (baci.k.isin(COPPER_CODES))].copy()
    ladder = (
        co.groupby(["t", "k"])
        .apply(lambda d: d.v.sum() / d.q.sum() if d.q.sum() > 0 else np.nan)
        .unstack("k")
    )
    ladder.columns.name = None
    return ladder


def compute_flows(baci, exporter):
    co = baci[(baci.i == exporter) & (baci.k.isin(COPPER_CODES))].copy()
    country_names = load_country_codes()
    flows = {}
    for code in COPPER_CODES:
        sub = co[co.k == code]
        if sub.empty:
            continue
        total = sub.v.sum()
        share = sub.groupby("j").v.sum().sort_values(ascending=False)
        share = (share / total * 100) if total > 0 else share * 0
        share_named = pd.Series({country_names.get(k, f"Code_{k}"): v for k, v in share.items()})
        flows[code] = share_named
    return flows


def plot_ladder_three_way(ladder_zmb, ladder_drc, ladder_cn, title):
    """三路对比加价阶梯: 赞比亚 vs DRC vs 中国。"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    colors = {"260300": "#d62728", "740200": "#ff7f0e", "740311": "#1f77b4"}

    data_map = [
        (ladder_zmb, "Zambia"),
        (ladder_drc, "DRC"),
        (ladder_cn, "China"),
    ]

    for ax, (ladder, name) in zip(axes, data_map):
        if ladder is None or ladder.empty:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(name)
            continue
        for col in ladder.columns:
            if col in HS_LABELS:
                ax.plot(ladder.index, ladder[col], marker="o",
                        color=colors.get(col, "gray"), linewidth=2,
                        label=HS_LABELS[col])
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Unit Value\n(thousand USD / tonne)")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_copper_ladder.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  加价阶梯图 → {out_path}")
    return fig


def plot_flows_all(flows_zmb, flows_drc):
    """赞比亚 + DRC 流向并列图。"""
    codes = [c for c in COPPER_CODES if c in flows_zmb or c in flows_drc]
    if not codes:
        return

    fig, axes = plt.subplots(2, len(codes), figsize=(6 * len(codes), 10))

    for row, (flows, label) in enumerate([(flows_zmb, "Zambia"), (flows_drc, "DRC")]):
        for col, code in enumerate(codes):
            ax = axes[row, col] if len(codes) > 1 else axes[row]
            share = flows.get(code, pd.Series())
            if share.empty:
                ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes)
            else:
                top5 = share.head(5)
                bars = ax.barh(range(len(top5)), top5.values, color="#2c3e50")
                ax.set_yticks(range(len(top5)))
                ax.set_yticklabels(top5.index, fontsize=7)
                ax.invert_yaxis()
                ax.grid(True, alpha=0.3, axis="x")
                for bar, val in zip(bars, top5.values):
                    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                            f"{val:.1f}%", va="center", fontsize=7)
            ax.set_title(f"{label}: {HS_LABELS.get(code, code)}", fontsize=9)
            ax.set_xlabel("Share (%)")

    fig.suptitle("Copper Value Flows: Zambia vs DRC Exports by Destination", fontsize=14)
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_copper_flows.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  价值流向图 → {out_path}")
    return fig


def print_ladder_summary(ladder_zmb, ladder_drc, ladder_cn):
    """打印加价对比摘要。"""
    for code in COPPER_CODES:
        print(f"\n  [{code}] 中位数单位价值 (千$/吨):")
        for ladder, name in [(ladder_zmb, "Zambia"), (ladder_drc, "DRC"), (ladder_cn, "China")]:
            if ladder is not None and code in ladder.columns:
                print(f"    {name}: {ladder[code].median():.1f}")

        if ladder_zmb is not None and ladder_cn is not None:
            if code in ladder_zmb.columns and code in ladder_cn.columns:
                ratio = ladder_cn[code].median() / ladder_zmb[code].median()
                print(f"    中国/Zambia: {ratio:.1f}x (中位单价比)")
            if code in ladder_drc.columns and code in ladder_cn.columns:
                ratio = ladder_cn[code].median() / ladder_drc[code].median()
                print(f"    中国/DRC: {ratio:.1f}x (中位单价比)")


def main():
    print("=" * 60)
    print("Phase 3.2: BACI 铜/赞比亚+DRC 加价阶梯 + 流向")
    print("=" * 60)

    baci = load_baci()

    # ── 三条加价阶梯 ──
    print("\n[命题 1] 铜加价阶梯:")
    ladder_zmb = compute_ladder(baci, ZAMBIA)
    ladder_drc = compute_ladder(baci, DRC)
    ladder_cn = compute_ladder(baci, CHINA)

    print("\n赞比亚:")
    print(ladder_zmb.round(1).to_string())
    print("\nDRC:")
    print(ladder_drc.round(1).to_string())
    print("\n中国:")
    print(ladder_cn.round(1).to_string())

    print_ladder_summary(ladder_zmb, ladder_drc, ladder_cn)

    ladder_zmb.to_csv(DATA_INTERIM / "baci_copper_ladder_zambia.csv")
    ladder_drc.to_csv(DATA_INTERIM / "baci_copper_ladder_drc.csv")
    ladder_cn.to_csv(DATA_INTERIM / "baci_copper_ladder_china.csv")
    plot_ladder_three_way(ladder_zmb, ladder_drc, ladder_cn,
                          "Copper Value Chain Ladder: Zambia vs DRC vs China")

    # ── 价值流向 ──
    print("\n[命题 2] 铜出口流向:")
    flows_zmb = compute_flows(baci, ZAMBIA)
    flows_drc = compute_flows(baci, DRC)

    for label, flows in [("Zambia", flows_zmb), ("DRC", flows_drc)]:
        print(f"\n  {label}:")
        for code, share in flows.items():
            print(f"    {code}:")
            for partner, pct in share.head(5).items():
                print(f"      {partner}: {pct:.1f}%")

    flows_zmb_df = pd.DataFrame({k: v for k, v in flows_zmb.items()})
    flows_zmb_df.to_csv(DATA_INTERIM / "baci_copper_flows_zambia.csv")
    flows_drc_df = pd.DataFrame({k: v for k, v in flows_drc.items()})
    flows_drc_df.to_csv(DATA_INTERIM / "baci_copper_flows_drc.csv")
    plot_flows_all(flows_zmb, flows_drc)

    # ── 关键对照: 赞比亚本地加工比例 ──
    print("\n[对照] 赞比亚 vs DRC 加工深度:")
    for label, ladder in [("Zambia", ladder_zmb), ("DRC", ladder_drc)]:
        if ladder is not None:
            ore = ladder.get("260300", pd.Series())
            refined = ladder.get("740311", pd.Series())
            if not ore.empty and not refined.empty:
                total_uv = (ore.sum() + refined.sum())
                refined_share = refined.sum() / total_uv * 100 if total_uv > 0 else 0
                print(f"  {label}: 精炼铜出口占比 (按单位价值): {refined_share:.1f}%")

    print("\nPhase 3.2 铜 BACI 分析完成")


if __name__ == "__main__":
    main()
