import os
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Optional

from dcai.config import PLUGINS_DIR, load_config, save_config


MANIFEST_FIELDS = ["name", "version", "entrypoint"]


def get_installed_plugins() -> list[dict]:
    plugins = []
    if not PLUGINS_DIR.exists():
        return plugins
    for d in PLUGINS_DIR.iterdir():
        if d.is_dir():
            manifest_file = d / "plugin.yaml"
            if manifest_file.exists():
                with open(manifest_file) as f:
                    manifest = yaml.safe_load(f) or {}
                manifest["_path"] = str(d)
                plugins.append(manifest)
    return plugins


def validate_manifest(manifest_path: Path) -> Optional[dict]:
    if not manifest_path.exists():
        return "plugin.yaml not found"
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f) or {}
    for field in MANIFEST_FIELDS:
        if field not in manifest:
            return f"Missing required field: {field}"
    entrypoint = Path(manifest_path.parent) / manifest["entrypoint"]
    if not entrypoint.exists():
        return f"Entrypoint not found: {manifest['entrypoint']}"
    return manifest


def install_plugin(url: str) -> bool:
    import tempfile

    print(f"Installing plugin from: {url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["git", "clone", url, tmpdir],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"Failed to clone repository: {result.stderr}")
            return False

        manifest_path = Path(tmpdir) / "plugin.yaml"
        manifest = validate_manifest(manifest_path)
        if isinstance(manifest, str):
            print(f"Invalid plugin: {manifest}")
            return False

        name = manifest["name"]
        dest = PLUGINS_DIR / name
        if dest.exists():
            overwrite = input(f"Plugin '{name}' is already installed. Overwrite? [y/N]: ").strip().lower()
            if overwrite != "y":
                print("Install cancelled.")
                return False
            shutil.rmtree(dest)

        print(f"\nPlugin: {manifest.get('name')}")
        print(f"Author: {manifest.get('author', 'unknown')}")
        print(f"Version: {manifest.get('version')}")
        print(f"Description: {manifest.get('description', 'N/A')}")
        commands = manifest.get("commands", [])
        if commands:
            print("Commands:")
            for cmd in commands:
                print(f"  - {cmd.get('name')}: {cmd.get('description', 'N/A')}")
        print()

        confirm = input("Install this plugin? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Install cancelled.")
            return False

        shutil.copytree(tmpdir, dest)
        print(f"Plugin '{name}' installed to {dest}.")

        register_plugin(manifest)
        return True


def register_plugin(manifest: dict):
    config = load_config()
    if "plugins" not in config:
        config["plugins"] = {}
    name = manifest["name"]
    config["plugins"][name] = {
        "name": name,
        "version": manifest["version"],
        "commands": [c["name"] for c in manifest.get("commands", [])],
    }
    save_config(config)


def remove_plugin(name: str) -> bool:
    dest = PLUGINS_DIR / name
    if not dest.exists():
        print(f"Plugin '{name}' is not installed.")
        return False
    shutil.rmtree(dest)
    config = load_config()
    config.get("plugins", {}).pop(name, None)
    save_config(config)
    print(f"Plugin '{name}' removed.")
    return True


def update_plugin(name: str) -> bool:
    dest = PLUGINS_DIR / name
    if not dest.exists():
        print(f"Plugin '{name}' is not installed.")
        return False
    result = subprocess.run(["git", "-C", str(dest), "pull"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Update failed: {result.stderr}")
        return False
    print(f"Plugin '{name}' updated:\n{result.stdout}")
    return True


def list_plugins():
    plugins = get_installed_plugins()
    if not plugins:
        print("No plugins installed.")
        return
    for p in plugins:
        print(f"{p.get('name')} v{p.get('version')} — {p.get('description', 'N/A')}")
        for cmd in p.get("commands", []):
            print(f"  └─ {cmd.get('name')}: {cmd.get('description', 'N/A')}")
