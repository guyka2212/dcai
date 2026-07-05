import os
import yaml
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir

APP_NAME = "dcai"

CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
PLUGINS_DIR = DATA_DIR / "plugins"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    CONFIG_FILE.chmod(0o600)


def get_config_path() -> Path:
    return CONFIG_FILE


def get_data_dir() -> Path:
    return DATA_DIR
