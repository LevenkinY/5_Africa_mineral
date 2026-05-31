"""USGS production anchors and physical reconciliation for lithium/copper.

Outputs:
- data/interim/usgs_lithium_physical_gap.csv
- data/interim/usgs_copper_physical_gap_zambia.csv
- data/interim/usgs_copper_physical_gap_drc.csv
- outputs/figures/usgs_lithium_physical_gap.png
- outputs/figures/usgs_copper_physical_gap.png
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from config import DATA_RAW, DATA_INTERIM, OUTPUT_FIGURES


# Central conversion assumptions. These are deliberately explicit because
# concentrate grades vary and should later be turned into low/high scenarios.
LI_CONTENT = {
    "253090": 0.03,   # spodumene/petalite raw minerals, central 3% Li content
    "282520": 0.165,  # lithium hydroxide monohydrate proxy
    "283691": 0.188,  # lithium carbonate Li content
}

CU_CONTENT = {
    "260300": 0.30,   # copper concentrate central grade
    "740200": 0.99,   # blister/anode copper
    "740311": 0.999,  # refined copper cathode
}


def load_export_quantities(path, codes):
    """Load export quantities as gross tonnes, avoiding World/detail double count."""
    df = pd.read_csv(path)
    df["cmdCode"] = df["cmdCode"].astype(str).str.zfill(6)
    df = df[df["cmdCode"].isin(codes)].copy()
    df = df[(df["qtyUnitCode"] == 8) & (df["qty"] > 0)].copy()
    df["qty_tonnes"] = df["qty"] / 1000

    world = (
        df[df["partnerCode"] == 0]
        .groupby(["period", "cmdCode"])["qty_tonnes"]
        .sum()
        .rename("world_qty_t")
    )
    detail = (
        df[df["partnerCode"] != 0]
        .groupby(["period", "cmdCode"])["qty_tonnes"]
        .sum()
        .rename("partner_detail_qty_t")
    )
    qty = pd.concat([world, detail], axis=1)
    use_world = qty["world_qty_t"].notna() & (qty["world_qty_t"] > 0)
    qty["qty_tonnes"] = qty["world_qty_t"].where(
        use_world, qty["partner_detail_qty_t"]
    ).fillna(0)
    qty["qty_source"] = np.where(use_world, "world", "partner_detail_sum")

    out = qty["qty_tonnes"].unstack("cmdCode")
    out.index.name = "year"
    return out


def convert_to_content_tonnes(trade_vol, factors, label):
    out = pd.DataFrame(index=trade_vol.index)
    for code, factor in factors.items():
        if code in trade_vol.columns:
            out[code] = trade_vol[code] * factor
            print(
                f"  {label} {code}: factor={factor:.3f}, "
                f"sum={out[code].sum():,.0f} tonnes content"
            )
    out[f"total_export_{label}_t"] = out.sum(axis=1)
    return out


def compute_gap(production, production_col, trade_content, export_col, output_path):
    gap = production.merge(trade_content, left_on="year", right_index=True, how="outer")
    gap = gap.sort_values("year")
    gap["physical_gap_t"] = gap[production_col] - gap[export_col]
    gap["gap_pct_of_production"] = gap["physical_gap_t"] / gap[production_col] * 100
    gap.to_csv(output_path, index=False)
    return gap


def plot_single_gap(gap, production_col, export_col, title, out_path):
    valid = gap.dropna(subset=[production_col, export_col])
    if valid.empty:
        print(f"[!] no valid rows for {title}")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    ax = axes[0]
    ax.plot(valid["year"], valid[production_col], marker="o", linewidth=2,
            label="USGS mine production")
    ax.plot(valid["year"], valid[export_col], marker="s", linewidth=1.5,
            label="Declared exports (content-equivalent)")
    ax.set_title(title)
    ax.set_xlabel("Year")
    ax.set_ylabel("Tonnes metal content")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    ax = axes[1]
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in valid["physical_gap_t"]]
    ax.bar(valid["year"], valid["physical_gap_t"], color=colors)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Production - declared exports")
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap (tonnes metal content)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  figure -> {out_path}")


def analyze_lithium():
    print("\n" + "=" * 64)
    print("Lithium / Zimbabwe physical reconciliation")
    print("=" * 64)
    production = pd.read_csv(DATA_RAW / "usgs_lithium_production_extracted.csv")
    trade_vol = load_export_quantities(
        DATA_RAW / "comtrade_lithium_zimbabwe_exports.csv",
        list(LI_CONTENT.keys()),
    )
    trade_li = convert_to_content_tonnes(trade_vol, LI_CONTENT, "li")
    gap = compute_gap(
        production[["year", "zimbabwe_mine_production_li_t"]],
        "zimbabwe_mine_production_li_t",
        trade_li,
        "total_export_li_t",
        DATA_INTERIM / "usgs_lithium_physical_gap.csv",
    )
    print(gap[["year", "zimbabwe_mine_production_li_t", "total_export_li_t",
               "physical_gap_t", "gap_pct_of_production"]].dropna(
                   subset=["zimbabwe_mine_production_li_t", "total_export_li_t"]
               ).to_string(index=False))
    plot_single_gap(
        gap,
        "zimbabwe_mine_production_li_t",
        "total_export_li_t",
        "Zimbabwe Lithium: USGS Mine Production vs Declared Exports",
        OUTPUT_FIGURES / "usgs_lithium_physical_gap.png",
    )


def analyze_copper():
    print("\n" + "=" * 64)
    print("Copper / Zambia + DRC physical reconciliation")
    print("=" * 64)
    production = pd.read_csv(DATA_RAW / "usgs_copper_production_extracted.csv")

    cases = [
        (
            "zambia",
            DATA_RAW / "comtrade_copper_zambia_exports.csv",
            "zambia_mine_production_cu_t",
            DATA_INTERIM / "usgs_copper_physical_gap_zambia.csv",
        ),
        (
            "drc",
            DATA_RAW / "comtrade_copper_drc_exports.csv",
            "drc_mine_production_cu_t",
            DATA_INTERIM / "usgs_copper_physical_gap_drc.csv",
        ),
    ]
    gaps = {}
    for label, exports_path, production_col, output_path in cases:
        print(f"\n[{label.upper()}]")
        trade_vol = load_export_quantities(exports_path, list(CU_CONTENT.keys()))
        trade_cu = convert_to_content_tonnes(trade_vol, CU_CONTENT, "cu")
        gap = compute_gap(
            production[["year", production_col]],
            production_col,
            trade_cu,
            "total_export_cu_t",
            output_path,
        )
        gaps[label] = (gap, production_col)
        print(gap[["year", production_col, "total_export_cu_t",
                   "physical_gap_t", "gap_pct_of_production"]].dropna(
                       subset=[production_col, "total_export_cu_t"]
                   ).to_string(index=False))

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for row, (label, (gap, production_col)) in enumerate(gaps.items()):
        valid = gap.dropna(subset=[production_col, "total_export_cu_t"])
        ax = axes[row, 0]
        ax.plot(valid["year"], valid[production_col], marker="o", linewidth=2,
                label="USGS mine production")
        ax.plot(valid["year"], valid["total_export_cu_t"], marker="s", linewidth=1.5,
                label="Declared exports")
        ax.set_title(f"{label.upper()}: production vs exports")
        ax.set_ylabel("Tonnes Cu content")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

        ax = axes[row, 1]
        colors = ["#27ae60" if v > 0 else "#c0392b" for v in valid["physical_gap_t"]]
        ax.bar(valid["year"], valid["physical_gap_t"], color=colors)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"{label.upper()}: production - exports")
        ax.set_ylabel("Gap (tonnes Cu content)")
        ax.grid(True, alpha=0.3, axis="y")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.suptitle("Copper: USGS Mine Production vs Declared Exports",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = OUTPUT_FIGURES / "usgs_copper_physical_gap.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  figure -> {out_path}")


def main():
    analyze_lithium()
    analyze_copper()


if __name__ == "__main__":
    main()
