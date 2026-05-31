"""Project-wide configuration. Load API keys from environment or .env file."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_FIGURES = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_TABLES = PROJECT_ROOT / "outputs" / "tables"

for d in [DATA_RAW, DATA_INTERIM, DATA_PROCESSED, OUTPUT_FIGURES, OUTPUT_TABLES]:
    d.mkdir(parents=True, exist_ok=True)


def _load_dotenv():
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


_load_dotenv()

COMTRADE_API_KEY = os.environ.get("COMTRADE_API_KEY", "")

# ── 研究常量（来自工作流文档）──────────────────────────────────────────

# 国家码
COUNTRY = {
    "DRC": 180,
    "China": 156,
    "Zambia": 894,
    "South Africa": 710,
    "Finland": 246,
    "Belgium": 56,
    "Zimbabwe": 716,
    "World": 0,  # Comtrade only
}

# HS6 产品码
HS_CODES = {
    "cobalt": {
        "矿石及精矿": "260500",
        "氧化物与氢氧化物": "282200",
        "未锻轧钴及冶金中间品": "810520",
    },
    "lithium": {
        "原料(含锂辉石精矿)": "253090",
        "锂氧化物与氢氧化物": "282520",
        "碳酸锂": "283691",
    },
    "copper": {
        "矿石及精矿": "260300",
        "粗铜": "740200",
        "精炼铜阴极": "740311",
    },
    "battery": {
        "锂离子蓄电池": "850760",
    },
}

# CIF→FOB 折算系数
CIF_TO_FOB_FACTOR = 0.9

# 钴含量转换系数 (DRC 实际商品品位, 基于 USITC 方法论和行业报告)
# 注意: DRC 粗制氢氧化物品位低于纯化合物, 且各批次差异大
CO_CONTENT = {
    "260500": 0.08,   # heterogenite 精矿, ~8% Co (范围 4-15%)
    "282200": 0.30,   # 粗制钴氢氧化物, ~30% Co (范围 25-40%)
    "810520": 0.99,   # 未锻轧钴金属, ~99% Co
}
