from pathlib import Path
import yaml
from app.utils.logger import log

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "PeopleFlowMonitor.db"
MODEL_PATH = BASE_DIR / "yolov8n.pt"
ZONES_PATH = BASE_DIR / "app" / "config" / "zones.yaml"


def load_zones_config() -> dict:
    """Loads counting zone configuration with safe fallback."""
    default_config = {
        "counting_line": {
            "y_ratio": 0.5,
            "offset": 0.05,
            "class_name": "person"
        }
    }

    try:
        if not ZONES_PATH.exists():
            raise FileNotFoundError(f"{ZONES_PATH} not found")

        with ZONES_PATH.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            raise ValueError("zones.yaml is empty")

        return config

    except Exception as e:
        log.warning(f"Failed to load zones.yaml: {e}. Using default configuration.")
        return default_config
