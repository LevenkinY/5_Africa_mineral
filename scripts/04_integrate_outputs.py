"""整合产出: 三张核心图表 + 研究摘要 (工作流文档 6.5 节)

前置: 运行 01_fetch_comtrade.py 和 02_analyze_baci.py

产出:
- outputs/figures/01_ladder_combined.png   加价阶梯 (DRC vs 中国)
- outputs/figures/02_flows_sankey.png      价值流向
- outputs/figures/03_gap_dashboard.png     缺口仪表盘 (镜像差额 + 实物缺口)
- outputs/tables/research_summary.csv      核心数据汇总表
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_INTERIM, DATA_RAW, OUTPUT_FIGURES, OUTPUT_TABLES, HS_CODES

COBALT_LABELS = {
    "260500": "Ore/Concentrate\n(260500)",
    "282200": "Oxide/Hydroxide\n(282200)",
    "810520": "Refined Cobalt\n(810520)",
}

# 尝试配置中文字体, 若无则回退英文
try:
    plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "Heiti SC", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


def load_all_data():
    """加载所有中间数据。"""
    data = {}

    # BACI 加价阶梯
    for key, fname in [("ladder_drc", "baci_cobalt_ladder_drc.csv"),
                        ("ladder_cn", "baci_cobalt_ladder_china.csv"),
                        ("flows_drc", "baci_cobalt_flows_drc.csv")]:
        p = DATA_INTERIM / fname
        if p.exists():
            data[key] = pd.read_csv(p, index_col=0)
        else:
            data[key] = None

    # Comtrade 镜像差额
    p = DATA_INTERIM / "comtrade_cobalt_mirror_gap.csv"
    if p.exists():
        data["mirror_gap"] = pd.read_csv(p)
    else:
        data["mirror_gap"] = None

    return data


def plot_combined_ladder(data):
    """图 1: 加价阶梯 (DRC vs 中国 对照, 含加价倍数标注)。"""
    ladder_drc = data.get("ladder_drc")
    ladder_cn = data.get("ladder_cn")

    if ladder_drc is None:
        print("[!] 缺少 BACI 加价阶梯数据")
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    codes = ["260500", "282200", "810520"]
    colors = {"DRC": "#c0392b", "China": "#2980b9"}

    for ax, code in zip(axes, codes):
        if code not in ladder_drc.columns:
            continue

        ax.plot(ladder_drc.index, ladder_drc[code],
                marker="o", color=colors["DRC"], linewidth=2, label="DRC")
        if ladder_cn is not None and code in ladder_cn.columns:
            ax.plot(ladder_cn.index, ladder_cn[code],
                    marker="s", color=colors["China"], linewidth=1.5, linestyle="--", label="China")

        # 标注中位单价比, 与 outputs/tables/*.csv 统一口径
        if ladder_cn is not None and code in ladder_cn.columns:
            ratio = ladder_cn[code].median() / ladder_drc[code].median()
            ax.text(0.02, 0.95, f"Median UV ratio: {ratio:.1f}x",
                    transform=ax.transAxes, fontsize=10,
                    verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        ax.set_title(COBALT_LABELS.get(code, code), fontsize=12)
        ax.set_xlabel("Year")
        ax.set_ylabel("Unit Value\n(thousand USD / tonne)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    fig.suptitle("Cobalt Value Chain: Unit Value Ladder — DRC vs China",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "01_ladder_combined.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  [1/3] 加价阶梯图 → {out_path}")


def plot_mirror_gap(data):
    """图 2: 镜像差额仪表盘。"""
    gap = data.get("mirror_gap")
    if gap is None:
        print("[!] 缺少 Comtrade 镜像差额数据")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 左: 各 HS 码 镜像差额值 (伙伴进口估算FOB - DRC出口FOB)
    ax = axes[0]
    # cmdCode 可能为 int 或 string, 统一转换为 6 位字符串
    gap["cmdCode_str"] = gap["cmdCode"].astype(str).str.zfill(6)
    gap_pivot = gap.pivot_table(values="mirror_gap", index="period", columns="cmdCode_str", aggfunc="sum")

    bar_width = 0.25
    codes_in_data = [c for c in ["260500", "282200", "810520"] if c in gap_pivot.columns]
    x = np.arange(len(gap_pivot))
    for i, code in enumerate(codes_in_data):
        offset = (i - len(codes_in_data) / 2 + 0.5) * bar_width
        ax.bar(x + offset, gap_pivot[code] / 1e6, bar_width,
               label=COBALT_LABELS.get(code, code))

    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in gap_pivot.index])
    ax.set_xlabel("Year")
    ax.set_ylabel("Mirror Gap (million USD)")
    ax.set_title("Trade Mirror Gap by HS Code\n(Partner Import FOB_est - DRC Export FOB)")
    ax.legend(fontsize=8)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")

    # 右: 各 HS 码 差额百分比
    ax = axes[1]
    gap_pct = gap.pivot_table(values="gap_pct", index="period", columns="cmdCode_str", aggfunc="mean")
    for i, code in enumerate(codes_in_data):
        if code in gap_pct.columns:
            offset = (i - len(codes_in_data) / 2 + 0.5) * bar_width
            ax.bar(x + offset, gap_pct[code], bar_width,
                   label=COBALT_LABELS.get(code, code))

    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in gap_pct.index])
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap (% of partner import)")
    ax.set_title("Mirror Gap Ratio by HS Code")
    ax.legend(fontsize=8)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle("DRC Cobalt Trade: Mirror Gap Analysis (Comtrade)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "02_mirror_gap_dashboard.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  [2/3] 镜像差额图 → {out_path}")


def generate_summary_table(data):
    """输出核心数据汇总表。"""
    rows = []

    # 从 BACI 加价阶梯提取关键指标
    ladder_drc = data.get("ladder_drc")
    ladder_cn = data.get("ladder_cn")

    if ladder_drc is not None:
        for code in ["260500", "282200", "810520"]:
            if code not in ladder_drc.columns:
                continue
            drc_median = ladder_drc[code].median()
            cn_median = ladder_cn[code].median() if (ladder_cn is not None and code in ladder_cn.columns) else np.nan
            ratio = cn_median / drc_median if drc_median > 0 else np.nan

            rows.append({
                "指标": f"DRC {code} 出口单价中位数 (千$/吨)",
                "值": f"{drc_median:.1f}",
                "来源": "BACI",
            })
            rows.append({
                "指标": f"中国 {code} 出口单价中位数 (千$/吨)",
                "值": f"{cn_median:.1f}",
                "来源": "BACI",
            })
            rows.append({
                "指标": f"中国/DRC {code} 单价倍数",
                "值": f"{ratio:.1f}x",
                "来源": "BACI",
            })

    # 从 Comtrade 镜像差额提取
    gap = data.get("mirror_gap")
    if gap is not None:
        gap["cmdCode_str"] = gap["cmdCode"].astype(str).str.zfill(6)
        for code in ["260500", "282200", "810520"]:
            sub = gap[gap["cmdCode_str"] == code]
            if not sub.empty:
                avg_gap_pct = sub["gap_pct"].mean()
                rows.append({
                    "指标": f"{code} 镜像差额均值 (%)",
                    "值": f"{avg_gap_pct:.1f}%",
                    "来源": "Comtrade",
                })

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_TABLES / "research_summary.csv", index=False)
    print(f"  [汇总] 核心数据表 → {OUTPUT_TABLES / 'research_summary.csv'}")
    print("\n" + "=" * 60)
    print("核心研究数据汇总")
    print("=" * 60)
    print(summary.to_string(index=False))


def main():
    print("=" * 60)
    print("Phase 1.4: 整合三张核心产出图")
    print("=" * 60)

    data = load_all_data()

    if data.get("ladder_drc") is not None:
        plot_combined_ladder(data)
    else:
        print("[!] 请先运行 02_analyze_baci.py")

    if data.get("mirror_gap") is not None:
        plot_mirror_gap(data)
    else:
        print("[!] 请先运行 01_fetch_comtrade.py")

    generate_summary_table(data)

    print("\nPhase 1.4 整合完成")
    print("\n三张核心图:")
    print("  1. outputs/figures/01_ladder_combined.png  — 加价阶梯")
    print("  2. outputs/figures/02_mirror_gap_dashboard.png — 镜像差额")
    print("  3. outputs/figures/baci_cobalt_flows.png   — 价值流向 (来自 02_analyze_baci.py)")


if __name__ == "__main__":
    main()
