"""Audit and recompute derived metrics from existing raw CSV files.

This script does not call external APIs. It fixes the Comtrade mirror-gap
aggregation by using reporter exports to World when available, and falling
back to summed partner-detail exports only when World is absent.

Outputs:
- data/interim/comtrade_*_mirror_gap.csv
- outputs/tables/comtrade_mirror_audit.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from config import CIF_TO_FOB_FACTOR, DATA_INTERIM, DATA_RAW, OUTPUT_TABLES


DATASETS = {
    "cobalt_drc": {
        "exports": "comtrade_cobalt_drc_exports.csv",
        "imports": "comtrade_cobalt_partner_imports.csv",
        "output": "comtrade_cobalt_mirror_gap.csv",
        "export_col": "drc_export_fob",
    },
    "lithium_zimbabwe": {
        "exports": "comtrade_lithium_zimbabwe_exports.csv",
        "imports": "comtrade_lithium_partner_imports.csv",
        "output": "comtrade_lithium_mirror_gap.csv",
        "export_col": "zwe_export_fob",
    },
    "copper_zambia": {
        "exports": "comtrade_copper_zambia_exports.csv",
        "imports": "comtrade_copper_partner_imports_from_zambia.csv",
        "output": "comtrade_copper_mirror_gap_zambia.csv",
        "export_col": "Zambia_export_fob",
    },
    "copper_drc": {
        "exports": "comtrade_copper_drc_exports.csv",
        "imports": "comtrade_copper_partner_imports_from_drc.csv",
        "output": "comtrade_copper_mirror_gap_drc.csv",
        "export_col": "DRC_export_fob",
    },
}


def _load_trade_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["cmdCode"] = df["cmdCode"].astype(str).str.zfill(6)
    return df


def corrected_export_aggregate(exports: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exports without double-counting World and partner detail."""
    world = (
        exports[exports["partnerCode"] == 0]
        .groupby(["period", "cmdCode"])["primaryValue"]
        .sum()
        .rename("world_export_fob")
    )
    detail = (
        exports[exports["partnerCode"] != 0]
        .groupby(["period", "cmdCode"])["primaryValue"]
        .sum()
        .rename("partner_detail_export_fob")
    )
    out = pd.concat([world, detail], axis=1)
    use_world = out["world_export_fob"].notna() & (out["world_export_fob"] != 0)
    out["export_fob"] = np.where(
        use_world,
        out["world_export_fob"],
        out["partner_detail_export_fob"].fillna(0),
    )
    out["export_source"] = np.where(use_world, "world", "partner_detail_sum")
    out["detail_to_world_ratio"] = (
        out["partner_detail_export_fob"] / out["world_export_fob"].replace(0, np.nan)
    )
    return out


def recompute_mirror_gap(name: str, meta: dict) -> pd.DataFrame:
    exports = _load_trade_csv(DATA_RAW / meta["exports"])
    imports = _load_trade_csv(DATA_RAW / meta["imports"])

    export_agg = corrected_export_aggregate(exports)
    import_agg = (
        imports.groupby(["period", "cmdCode"])["primaryValue"]
        .sum()
        .rename("partner_import_cif")
    )

    gap = pd.concat([export_agg, import_agg], axis=1).fillna(
        {"export_fob": 0, "partner_import_cif": 0}
    )
    gap["export_source"] = gap["export_source"].fillna("no_export_record")
    gap["partner_import_fob_est"] = gap["partner_import_cif"] * CIF_TO_FOB_FACTOR
    gap["mirror_gap"] = gap["partner_import_fob_est"] - gap["export_fob"]
    gap["gap_pct"] = (
        gap["mirror_gap"] / gap["partner_import_fob_est"].replace(0, np.nan) * 100
    )

    gap = gap.reset_index()
    gap = gap.rename(columns={"export_fob": meta["export_col"]})

    ordered_cols = [
        "period",
        "cmdCode",
        meta["export_col"],
        "partner_import_cif",
        "partner_import_fob_est",
        "mirror_gap",
        "gap_pct",
        "export_source",
        "world_export_fob",
        "partner_detail_export_fob",
        "detail_to_world_ratio",
    ]
    gap = gap[[c for c in ordered_cols if c in gap.columns]]
    gap.to_csv(DATA_INTERIM / meta["output"], index=False)
    print(f"{name}: wrote {DATA_INTERIM / meta['output']} ({len(gap)} rows)")
    return gap


def build_audit_summary(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, gap in results.items():
        for code, sub in gap.groupby("cmdCode"):
            rows.append(
                {
                    "dataset": name,
                    "cmdCode": code,
                    "rows": len(sub),
                    "world_rows": int((sub["export_source"] == "world").sum()),
                    "fallback_rows": int((sub["export_source"] != "world").sum()),
                    "median_gap_pct": sub["gap_pct"].median(),
                    "mean_gap_pct": sub["gap_pct"].mean(),
                    "median_detail_to_world_ratio": sub[
                        "detail_to_world_ratio"
                    ].median(),
                }
            )
    audit = pd.DataFrame(rows)
    audit.to_csv(OUTPUT_TABLES / "comtrade_mirror_audit.csv", index=False)
    return audit


def main():
    print("=" * 72)
    print("Comtrade mirror-gap audit and recomputation")
    print("=" * 72)
    results = {}
    for name, meta in DATASETS.items():
        results[name] = recompute_mirror_gap(name, meta)

    audit = build_audit_summary(results)
    print("\nAudit summary:")
    print(audit.round(2).to_string(index=False))
    print(f"\nAudit table -> {OUTPUT_TABLES / 'comtrade_mirror_audit.csv'}")


if __name__ == "__main__":
    main()
