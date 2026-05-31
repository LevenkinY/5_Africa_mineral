# Materials Index

This index maps migrated project materials to their canonical locations inside the repository.

| Category | Canonical location | Source folders migrated | Public in Git? | Notes |
|---|---|---|---|---|
| Research proposals and figure design | `docs/proposals/` | `ResearchProposal/`, `Figures/` | Yes | Proposal drafts, JIMF PDFs, and figure design notes. |
| Interview metadata | `docs/interviews/` | `专家访谈结果/`, prior `docs/260523_Worash_Getaneh访谈结果.docx` | Metadata only | Interview originals stay in `_private/interviews/`. |
| Literature review outputs | `literature/review/` | `outputs/`, `literatures/` | Yes | Review workbook, extracted context JSON, and reproducibility notes. |
| Source literature | `literature/sources/` | `literatures/`, `HuBin/` | Yes | PDFs and DOCX background sources; check rights before public release. |
| Price and trade files | `data/external/price_trade/` | `Price/` | Yes | WITS, EITI, policy price lists, company reports, and methodology PDFs. |
| Project inventory | `data/external/project_inventory/` | root project workbook, `Property/` metadata | Mixed | Public inventory workbook is committed; commercial S&P export is private only. |
| Literature review scripts | `scripts/literature_review/` | `outputs/spreadsheet_work/`, `tools/` | Yes | Scripts retained only when useful for reproduction. |

Do not commit Office temporary files, macOS metadata files, API keys, commercial database exports, or undeidentified interview originals.
