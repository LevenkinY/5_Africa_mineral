"""跨矿种对比整合: 钴/DRC + 锂/津巴布韦 + 铜/赞比亚

产出:
- outputs/figures/cross_ladder_ratio.png    加价倍数对比 (中国/非洲)
- outputs/figures/cross_flow_concentration.png 流向集中度对比
- outputs/figures/cross_mirror_gap.png     镜像差额对比
- outputs/tables/cross_mineral_summary.csv  论文核心数据汇总表
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from config import DATA_INTERIM, OUTPUT_FIGURES, OUTPUT_TABLES

# ── 矿种元数据 ──────────────────────────────────────────────────────────
MINERALS = {
    "Cobalt\n(DRC)": {
        "ladder_africa": "baci_cobalt_ladder_drc.csv",
        "ladder_china": "baci_cobalt_ladder_china.csv",
        "flows": "baci_cobalt_flows_drc.csv",
        "mirror": "comtrade_cobalt_mirror_gap.csv",
        "codes": ["260500", "282200", "810520"],
        "code_labels": {
            "260500": "Ore/Concentrate",
            "282200": "Oxide/Hydroxide",
            "810520": "Refined Metal",
        },
        "color": "#c0392b",
    },
    "Lithium\n(Zimbabwe)": {
        "ladder_africa": "baci_lithium_ladder_zwe.csv",
        "ladder_china": "baci_lithium_ladder_china.csv",
        "flows": "baci_lithium_flows_zwe.csv",
        "mirror": "comtrade_lithium_mirror_gap.csv",
        "codes": ["253090", "282520", "283691"],
        "code_labels": {
            "253090": "Raw Mineral\n(incl. Spodumene)",
            "282520": "Li Oxide/Hydroxide",
            "283691": "Li Carbonate",
        },
        "color": "#2980b9",
    },
    "Copper\n(Zambia)": {
        "ladder_africa": "baci_copper_ladder_zambia.csv",
        "ladder_china": "baci_copper_ladder_china.csv",
        "flows": "baci_copper_flows_zambia.csv",
        "mirror": "comtrade_copper_mirror_gap_zambia.csv",
        "codes": ["260300", "740200", "740311"],
        "code_labels": {
            "260300": "Ore/Concentrate",
            "740200": "Blister/Anode",
            "740311": "Refined Cathode",
        },
        "color": "#27ae60",
    },
}


def load_data():
    """加载所有中间数据。"""
    data = {}
    for name, meta in MINERALS.items():
        d = {}
        for key, fname in [("ladder_africa", meta["ladder_africa"]),
                            ("ladder_china", meta["ladder_china"]),
                            ("flows", meta["flows"]),
                            ("mirror", meta["mirror"])]:
            p = DATA_INTERIM / fname
            if p.exists():
                d[key] = pd.read_csv(p, index_col=0 if "ladder" in key or "flows" in key else None)
            else:
                d[key] = None
        data[name] = d
    return data


def compute_ratios(data):
    """计算每种矿的 中国/非洲 加价倍数。

    统一口径: 中国出口单位价值中位数 / 非洲出口单位价值中位数。
    这样表中展示的两个中位单价与倍数可直接互相校验。
    """
    ratios = {}
    for name, d in data.items():
        la = d.get("ladder_africa")
        lc = d.get("ladder_china")
        if la is None or lc is None:
            continue
        r = {}
        for code in MINERALS[name]["codes"]:
            if code in la.columns and code in lc.columns:
                africa_uv = la[code].median()
                china_uv = lc[code].median()
                r[code] = china_uv / africa_uv if africa_uv > 0 else np.nan
        ratios[name] = r
    return ratios


def compute_flow_concentration(data):
    """计算每种矿对中国出口的份额 (Top1 集中度)。"""
    concentration = {}
    for name, d in data.items():
        flows = d.get("flows")
        if flows is None:
            continue
        conc = {}
        for code in MINERALS[name]["codes"]:
            if code in flows.columns:
                share = flows[code].dropna()
                # 找 China 的份额
                cn_share = 0
                for idx in share.index:
                    if "china" in str(idx).lower():
                        cn_share = share[idx]
                        break
                # 若未找到 China, 取 Top1
                if cn_share == 0 and len(share) > 0:
                    cn_share = share.iloc[0]
                conc[code] = cn_share
        concentration[name] = conc
    return concentration


def plot_ladder_ratios(ratios):
    """图 1: 跨矿种加价倍数对比 (中国/非洲)。"""
    fig, ax = plt.subplots(figsize=(12, 6))

    all_codes = []
    all_vals = []
    all_colors = []
    all_labels = []

    for name, r in ratios.items():
        meta = MINERALS[name]
        for code, val in r.items():
            label = meta["code_labels"].get(code, code)
            all_codes.append(f"{name}\n{label}")
            all_vals.append(val)
            all_colors.append(meta["color"])
            all_labels.append(name)

    x = range(len(all_codes))
    bars = ax.bar(x, all_vals, color=all_colors, edgecolor="white", linewidth=0.5)

    # 标注数值
    for bar, val in zip(bars, all_vals):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f"{val:.1f}x", ha="center", fontsize=10, fontweight="bold")

    ax.axhline(y=1.0, color="black", linewidth=1, linestyle="--", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(all_codes, fontsize=9)
    ax.set_ylabel("Median China Unit Value / Median Africa Unit Value", fontsize=12)
    ax.set_title("Cross-Mineral Value Ladder Comparison: China/Africa Unit Value Ratio",
                 fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # 图例: 标注区域
    ax.text(0.02, 0.95, "Ratio > 1.0 = China captures more value",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))
    ax.text(0.02, 0.88, "Ratio ≈ 1.0 = Global pricing (LME)",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8))

    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "cross_ladder_ratio.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  [1/3] 跨矿种加价倍数图 → {out_path}")


def plot_flow_concentration(concentration):
    """图 2: 流向集中度对比 (中国在 Top1 买家中的份额)。"""
    fig, ax = plt.subplots(figsize=(12, 6))

    all_codes = []
    all_vals = []
    all_colors = []

    for name, conc in concentration.items():
        meta = MINERALS[name]
        for code, val in conc.items():
            label = meta["code_labels"].get(code, code)
            all_codes.append(f"{name}\n{label}")
            all_vals.append(val)
            all_colors.append(meta["color"])

    x = range(len(all_codes))
    bars = ax.bar(x, all_vals, color=all_colors, edgecolor="white", linewidth=0.5)

    for bar, val in zip(bars, all_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val:.0f}%", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(all_codes, fontsize=9)
    ax.set_ylabel("Share of Export Value (%)", fontsize=12)
    ax.set_title("Cross-Mineral Export Flow Concentration: China's Share as Top Buyer",
                 fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_ylim(0, 110)

    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "cross_flow_concentration.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  [2/3] 流向集中度图 → {out_path}")


def plot_mirror_gap(data):
    """图 3: 跨矿种镜像差额对比。"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax, (name, d) in zip(axes, data.items()):
        meta = MINERALS[name]
        gap = d.get("mirror")
        if gap is None:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_title(name)
            continue

        gap["cmdCode_str"] = gap["cmdCode"].astype(str).str.zfill(6)
        codes = meta["codes"]
        gap_pivot = gap.pivot_table(
            values="mirror_gap", index="period", columns="cmdCode_str", aggfunc="sum"
        )

        bar_width = 0.2
        codes_in_data = [c for c in codes if c in gap_pivot.columns]
        x = np.arange(len(gap_pivot))

        for i, code in enumerate(codes_in_data):
            offset = (i - len(codes_in_data) / 2 + 0.5) * bar_width
            vals = gap_pivot[code] / 1e6  # 百万美元
            ax.bar(x + offset, vals, bar_width,
                   label=meta["code_labels"].get(code, code), alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels([str(int(y)) for y in gap_pivot.index], fontsize=8)
        ax.set_xlabel("Year")
        ax.set_ylabel("Mirror Gap (million USD)")
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.legend(fontsize=7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle("Cross-Mineral Mirror Gap Comparison: Partner Import (FOB est.) - Africa Export (FOB)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "cross_mirror_gap.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  [3/3] 镜像差额对比图 → {out_path}")


def generate_summary_table(data, ratios, concentration):
    """生成论文核心数据汇总表。"""
    rows = []

    for name, d in data.items():
        meta = MINERALS[name]
        r = ratios.get(name, {})
        conc = concentration.get(name, {})

        for code in meta["codes"]:
            la = d.get("ladder_africa")
            lc = d.get("ladder_china")

            africa_uv = la[code].median() if la is not None and code in la.columns else np.nan
            china_uv = lc[code].median() if lc is not None and code in lc.columns else np.nan
            ratio = r.get(code, np.nan)
            cn_share = conc.get(code, np.nan)

            rows.append({
                "矿种": name.replace("\n", " "),
                "HS 码": code,
                "产品": meta["code_labels"].get(code, code),
                "非洲出口单价中位数 (千$/吨)": f"{africa_uv:.1f}" if not np.isnan(africa_uv) else "N/A",
                "中国出口单价中位数 (千$/吨)": f"{china_uv:.1f}" if not np.isnan(china_uv) else "N/A",
                "中国/非洲加价倍数 (中位单价比)": f"{ratio:.1f}x" if not np.isnan(ratio) else "N/A",
                "中国占非洲出口份额 (%)": f"{cn_share:.1f}%" if not np.isnan(cn_share) else "N/A",
            })

    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_TABLES / "cross_mineral_summary.csv", index=False)

    print("\n" + "=" * 80)
    print("论文核心数据汇总表")
    print("=" * 80)
    print(summary.to_string(index=False))
    print(f"\n数据已保存至 {OUTPUT_TABLES / 'cross_mineral_summary.csv'}")


def main():
    print("=" * 60)
    print("跨矿种对比整合: 钴 + 锂 + 铜")
    print("=" * 60)

    data = load_data()

    # 加价倍数
    ratios = compute_ratios(data)
    print("\n[加价倍数] 中国/非洲 单位价值比:")
    for name, r in ratios.items():
        print(f"  {name}:")
        for code, val in r.items():
            print(f"    {code}: {val:.1f}x")

    # 流向集中度
    concentration = compute_flow_concentration(data)
    print("\n[流向集中度] 中国占非洲出口份额:")
    for name, conc in concentration.items():
        print(f"  {name}:")
        for code, val in conc.items():
            print(f"    {code}: {val:.0f}%")

    # 三张图
    plot_ladder_ratios(ratios)
    plot_flow_concentration(concentration)
    plot_mirror_gap(data)

    # 汇总表
    generate_summary_table(data, ratios, concentration)

    print("\n跨矿种整合完成")


if __name__ == "__main__":
    main()
