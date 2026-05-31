"""BACI 数据分析: 钴/DRC 加价阶梯 + 价值流向 (工作流文档 6.2 节)

前置: 从 CEPII 下载 BACI HS17 CSV, 放入 data/BACI_HS17_V202601/

输出:
- data/interim/baci_cobalt_ladder_drc.csv    加价阶梯表 (DRC)
- data/interim/baci_cobalt_ladder_china.csv  加价阶梯表 (中国, 对照)
- data/interim/baci_cobalt_flows_drc.csv     价值流向表
- outputs/figures/baci_cobalt_ladder.png     加价阶梯图
- outputs/figures/baci_cobalt_flows.png      价值流向图
"""

import glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_INTERIM, OUTPUT_FIGURES, PROJECT_ROOT

# ── 参数 ────────────────────────────────────────────────────────────────
BACI_DIR = PROJECT_ROOT / "data" / "BACI_HS17_V202601"
COBALT_CODES = ["260500", "282200", "810520"]  # 钴矿石→中间品→精炼
HS_LABELS = {
    "260500": "Ores & Concentrates\n(260500)",
    "282200": "Oxides & Hydroxides\n(282200)",
    "810520": "Unwrought Cobalt\n(810520)",
}
DRC = 180
CHINA = 156

# 主要伙伴国 {code: name}
PARTNER_NAMES = {
    156: "China",
    894: "Zambia",
    710: "South Africa",
    246: "Finland",
    56: "Belgium",
    0: "World",
}


def load_country_codes():
    """加载 BACI 国家码映射。"""
    f = BACI_DIR / "country_codes_V202601.csv"
    if f.exists():
        df = pd.read_csv(f)
        return dict(zip(df["country_code"], df["country_name"]))
    return {}


def load_baci(baci_dir=None):
    """加载 BACI 数据, 只保留钴 + DRC/中国 相关记录以节省内存。"""
    if baci_dir is None:
        baci_dir = BACI_DIR

    csv_files = sorted(glob.glob(str(baci_dir / "BACI_HS17_Y20*.csv")))
    if not csv_files:
        raise FileNotFoundError(
            f"未在 {baci_dir} 找到 BACI CSV 文件。\n"
            "请从 CEPII 下载 BACI HS17 数据并放入该目录。"
        )

    print(f"加载 {len(csv_files)} 个 BACI 文件...")
    frames = []
    for f in csv_files:
        df = pd.read_csv(f, dtype={"k": str})  # k=HS6, 保持字符串
        # 筛选钴相关 HS 码 + DRC/中国为出口国或伙伴国
        mask = (
            (df["k"].isin(COBALT_CODES))
            & (df["i"].isin([DRC, CHINA]) | df["j"].isin([DRC, CHINA]))
        )
        df = df[mask]
        if len(df):
            frames.append(df)
        import os; print(f"  {os.path.basename(f)}: {len(df)} 条")

    if not frames:
        raise ValueError("BACI 数据中未找到钴相关记录")
    baci = pd.concat(frames, ignore_index=True)
    print(f"  共 {len(baci)} 条钴相关记录\n")
    return baci


def compute_ladder(baci, exporter=DRC):
    """计算加价阶梯: 各级 HS 码出口的加权单位价值 (千美元/吨)。"""
    co = baci[(baci.i == exporter) & (baci.k.isin(COBALT_CODES))].copy()

    # 加权单位价值 = sum(v) / sum(q) 每年每码
    ladder = (
        co.groupby(["t", "k"])
        .apply(lambda d: d.v.sum() / d.q.sum() if d.q.sum() > 0 else np.nan)
        .unstack("k")
    )
    ladder.columns.name = None
    return ladder


def compute_flows(baci, exporter=DRC):
    """计算价值流向: 各 HS 码出口的买家份额 (全时段汇总)。"""
    co = baci[(baci.i == exporter) & (baci.k.isin(COBALT_CODES))].copy()
    country_names = load_country_codes()

    flows = {}
    for code in COBALT_CODES:
        sub = co[co.k == code]
        if sub.empty:
            continue
        total = sub.v.sum()
        share = sub.groupby("j").v.sum().sort_values(ascending=False)
        share = (share / total * 100) if total > 0 else share * 0
        # 映射国家名
        share_named = pd.Series(
            {country_names.get(k, f"Code_{k}"): v for k, v in share.items()}
        )
        flows[code] = share_named
    return flows


def plot_ladder(ladder_drc, ladder_cn=None):
    """绘制加价阶梯图, 可叠加中国对照。"""
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = {"260500": "#d62728", "282200": "#ff7f0e", "810520": "#1f77b4"}
    markers = {"260500": "o", "282200": "s", "810520": "D"}

    for col in ladder_drc.columns:
        label = list(HS_LABELS.keys())[list(HS_LABELS.values()).index(
            next(v for k, v in HS_LABELS.items() if col in k)
        )] if col in HS_LABELS else col
        ax.plot(
            ladder_drc.index, ladder_drc[col],
            marker=markers.get(col, "o"), color=colors.get(col, "C0"),
            linewidth=2, label=f"DRC: {HS_LABELS.get(col, col)}"
        )

    if ladder_cn is not None and not ladder_cn.empty:
        for col in ladder_cn.columns:
            if col in HS_LABELS:
                ax.plot(
                    ladder_cn.index, ladder_cn[col],
                    marker=markers.get(col, "o"), color=colors.get(col, "C0"),
                    linewidth=1.5, linestyle="--", alpha=0.7,
                    label=f"China: {HS_LABELS.get(col, col)}"
                )

    ax.set_xlabel("Year")
    ax.set_ylabel("Unit Value (thousand USD / tonne)")
    ax.set_title("Cobalt Value Chain Ladder: DRC vs China Export Unit Values", fontsize=13)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_cobalt_ladder.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  加价阶梯图已保存至 {out_path}")
    return fig


def plot_flows(flows, exporter_label="DRC"):
    """绘制价值流向图 (水平柱状图, Top 5 买家)。"""
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
        ax.set_title(HS_LABELS.get(code, code), fontsize=11)
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3, axis="x")
        for bar, val in zip(bars, top5.values):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}%", va="center", fontsize=8)

    fig.suptitle(f"Cobalt Value Flows: {exporter_label} Exports by Destination", fontsize=14)
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "baci_cobalt_flows.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  价值流向图已保存至 {out_path}")
    return fig


def main():
    print("=" * 60)
    print("Phase 1.2: BACI 加价阶梯 + 价值流向分析")
    print("=" * 60)

    baci = load_baci()

    # ── 命题 1: DRC 加价阶梯 ──
    print("\n[命题 1] DRC 钴加价阶梯 (单位价值, 千美元/吨):")
    ladder_drc = compute_ladder(baci, exporter=DRC)
    print(ladder_drc.round(1).to_string())
    ladder_drc.to_csv(DATA_INTERIM / "baci_cobalt_ladder_drc.csv")

    # 加价倍数 (精炼 vs 矿石)
    if "260500" in ladder_drc.columns and "810520" in ladder_drc.columns:
        ratio = ladder_drc["810520"] / ladder_drc["260500"]
        print(f"\n  精炼/矿石 加价倍数 (中位数): {ratio.median():.1f}x")
        print(f"  精炼/矿石 加价倍数 (范围): {ratio.min():.1f}x - {ratio.max():.1f}x")

    # ── 中国加价阶梯 (对照) ──
    print("\n[对照] 中国钴出口加价阶梯:")
    ladder_cn = compute_ladder(baci, exporter=CHINA)
    print(ladder_cn.round(1).to_string())
    ladder_cn.to_csv(DATA_INTERIM / "baci_cobalt_ladder_china.csv")

    # DRC vs 中国单位价值比
    print("\n  中国/DRC 单位价值比:")
    for col in ladder_drc.columns.intersection(ladder_cn.columns):
        ratio = ladder_cn[col].median() / ladder_drc[col].median()
        print(f"    {col}: {ratio:.1f}x (中位单价比)")

    plot_ladder(ladder_drc, ladder_cn)

    # ── 命题 2: 价值流向 ──
    print("\n[命题 2] DRC 钴出口流向 (Top 5 买家, 全时段份额 %):")
    flows_drc = compute_flows(baci, exporter=DRC)
    for code, share in flows_drc.items():
        print(f"\n  {code} ({HS_LABELS.get(code, code)}):")
        for partner, pct in share.head(5).items():
            print(f"    {partner}: {pct:.1f}%")
    flows_df = pd.DataFrame({k: v for k, v in flows_drc.items()})
    flows_df.to_csv(DATA_INTERIM / "baci_cobalt_flows_drc.csv")
    plot_flows(flows_drc, "DRC")

    # ── 命题 2 补充: 中国出口流向 ──
    print("\n[补充] 中国钴出口流向 (Top 5):")
    flows_cn = compute_flows(baci, exporter=CHINA)
    for code, share in flows_cn.items():
        print(f"\n  {code}:")
        for partner, pct in share.head(5).items():
            print(f"    {partner}: {pct:.1f}%")

    print("\nPhase 1.2 BACI 分析完成")


if __name__ == "__main__":
    main()
