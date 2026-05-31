"""BACI 数据分析: 锂/津巴布韦 加价阶梯 + 价值流向 (工作流文档 4.2/6.5 节)

输出:
- data/interim/baci_lithium_ladder_zwe.csv
- data/interim/baci_lithium_ladder_china.csv
- data/interim/baci_lithium_flows_zwe.csv
- outputs/figures/baci_lithium_ladder.png
- outputs/figures/baci_lithium_flows.png
"""

import os, glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_INTERIM, OUTPUT_FIGURES, PROJECT_ROOT

BACI_DIR = PROJECT_ROOT / "data" / "BACI_HS17_V202601"
LITHIUM_CODES = ["253090", "282520", "283691"]
HS_LABELS = {
    "253090": "Raw Minerals\n(incl. Spodumene, 253090)",
    "282520": "Lithium Oxide/Hydroxide\n(282520)",
    "283691": "Lithium Carbonate\n(283691)",
}
ZIMBABWE = 716
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
        raise FileNotFoundError(f"未在 {BACI_DIR} 找到 BACI CSV 文件")

    print(f"加载 {len(csv_files)} 个 BACI 文件...")
    frames = []
    for f in csv_files:
        df = pd.read_csv(f, dtype={"k": str})
        mask = (
            df["k"].isin(LITHIUM_CODES)
            & (df["i"].isin([ZIMBABWE, CHINA]) | df["j"].isin([ZIMBABWE, CHINA]))
        )
        df = df[mask]
        if len(df):
            frames.append(df)
        print(f"  {os.path.basename(f)}: {len(df)} 条")

    if not frames:
        raise ValueError("BACI 数据中未找到锂相关记录")
    baci = pd.concat(frames, ignore_index=True)
    print(f"  共 {len(baci)} 条锂相关记录\n")
    return baci


def compute_ladder(baci, exporter):
    co = baci[(baci.i == exporter) & (baci.k.isin(LITHIUM_CODES))].copy()
    ladder = (
        co.groupby(["t", "k"])
        .apply(lambda d: d.v.sum() / d.q.sum() if d.q.sum() > 0 else np.nan)
        .unstack("k")
    )
    ladder.columns.name = None
    return ladder


def compute_flows(baci, exporter):
    co = baci[(baci.i == exporter) & (baci.k.isin(LITHIUM_CODES))].copy()
    country_names = load_country_codes()
    flows = {}
    for code in LITHIUM_CODES:
        sub = co[co.k == code]
        if sub.empty:
            continue
        total = sub.v.sum()
        share = sub.groupby("j").v.sum().sort_values(ascending=False)
        share = (share / total * 100) if total > 0 else share * 0
        share_named = pd.Series({country_names.get(k, f"Code_{k}"): v for k, v in share.items()})
        flows[code] = share_named
    return flows


def plot_ladder(ladder_zwe, ladder_cn=None):
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"253090": "#d62728", "282520": "#ff7f0e", "283691": "#1f77b4"}

    for col in ladder_zwe.columns:
        ax.plot(ladder_zwe.index, ladder_zwe[col], marker="o",
                color=colors.get(col, "gray"), linewidth=2,
                label=f"ZWE: {HS_LABELS.get(col, col)}")

    if ladder_cn is not None and not ladder_cn.empty:
        for col in ladder_cn.columns:
            if col in HS_LABELS:
                ax.plot(ladder_cn.index, ladder_cn[col], marker="s",
                        color=colors.get(col, "gray"), linewidth=1.5,
                        linestyle="--", alpha=0.7,
                        label=f"China: {HS_LABELS.get(col, col)}")

    ax.set_xlabel("Year")
    ax.set_ylabel("Unit Value (thousand USD / tonne)")
    ax.set_title("Lithium Value Chain Ladder: Zimbabwe vs China Export Unit Values", fontsize=13)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_lithium_ladder.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  加价阶梯图 → {out_path}")
    return fig


def plot_flows(flows, exporter_label="Zimbabwe"):
    n = len(flows)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
    if n == 1:
        axes = [axes]

    for ax, (code, share) in zip(axes, flows.items()):
        top5 = share.head(5)
        bars = ax.barh(range(len(top5)), top5.values, color="#2c3e50")
        ax.set_yticks(range(len(top5)))
        ax.set_yticklabels(top5.index)
        ax.set_xlabel("Share of Export Value (%)")
        ax.set_title(HS_LABELS.get(code, code), fontsize=10)
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3, axis="x")
        for bar, val in zip(bars, top5.values):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}%", va="center", fontsize=8)

    fig.suptitle(f"Lithium Value Flows: {exporter_label} Exports by Destination", fontsize=14)
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_lithium_flows.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  价值流向图 → {out_path}")
    return fig


def main():
    print("=" * 60)
    print("Phase 2.2: BACI 锂/津巴布韦 加价阶梯 + 价值流向")
    print("=" * 60)

    baci = load_baci()

    # ── 津巴布韦加价阶梯 ──
    print("\n[命题 1] 津巴布韦锂加价阶梯 (单位价值, 千美元/吨):")
    ladder_zwe = compute_ladder(baci, exporter=ZIMBABWE)
    print(ladder_zwe.round(1).to_string())
    ladder_zwe.to_csv(DATA_INTERIM / "baci_lithium_ladder_zwe.csv")

    # 加价倍数
    if "253090" in ladder_zwe.columns and "283691" in ladder_zwe.columns:
        ratio = ladder_zwe["283691"] / ladder_zwe["253090"]
        print(f"\n  碳酸锂/原料 加价倍数 (中位数): {ratio.median():.1f}x")

    # ── 中国加价阶梯 (对照) ──
    print("\n[对照] 中国锂出口加价阶梯:")
    ladder_cn = compute_ladder(baci, exporter=CHINA)
    print(ladder_cn.round(1).to_string())
    ladder_cn.to_csv(DATA_INTERIM / "baci_lithium_ladder_china.csv")

    print("\n  中国/津巴布韦 单位价值比:")
    for col in ladder_zwe.columns.intersection(ladder_cn.columns):
        ratio = ladder_cn[col].median() / ladder_zwe[col].median()
        print(f"    {col}: {ratio:.1f}x (中位单价比)")

    plot_ladder(ladder_zwe, ladder_cn)

    # ── 价值流向 ──
    print("\n[命题 2] 津巴布韦锂出口流向 (Top 5):")
    flows_zwe = compute_flows(baci, exporter=ZIMBABWE)
    for code, share in flows_zwe.items():
        print(f"\n  {code} ({HS_LABELS.get(code, code)}):")
        for partner, pct in share.head(5).items():
            print(f"    {partner}: {pct:.1f}%")
    flows_df = pd.DataFrame({k: v for k, v in flows_zwe.items()})
    flows_df.to_csv(DATA_INTERIM / "baci_lithium_flows_zwe.csv")
    plot_flows(flows_zwe, "Zimbabwe")

    # ── 中国锂流向 ──
    print("\n[补充] 中国锂出口流向 (Top 5):")
    flows_cn = compute_flows(baci, exporter=CHINA)
    for code, share in flows_cn.items():
        print(f"\n  {code}:")
        for partner, pct in share.head(5).items():
            print(f"    {partner}: {pct:.1f}%")

    print("\nPhase 2.2 锂 BACI 分析完成")


if __name__ == "__main__":
    main()
