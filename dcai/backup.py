import os
import subprocess
import shutil
from pathlib import Path
from dcai.config import CONFIG_DIR, DATA_DIR, get_config_path


def backup_push(repo_url: str = None):
    if not repo_url:
        repo_url = os.environ.get("DCAI_BACKUP_REPO")
    if not repo_url:
        print("No backup repo configured. Provide a URL or set DCAI_BACKUP_REPO.")
        print("Usage: dcai backup push <git-url>")
        return False

    backup_dir = Path("/tmp/dcai-backup-tmp")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    config = load_config_for_backup()
    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, str(backup_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        backup_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=backup_dir, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", repo_url],
            cwd=backup_dir, capture_output=True,
        )

    config_dir = backup_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    for item in CONFIG_DIR.iterdir():
        if item.name == "config.yaml":
            continue
        if item.is_file():
            shutil.copy2(item, config_dir / item.name)

    data_dir = backup_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for item in DATA_DIR.iterdir():
        if item.name == "plugins":
            continue
        shutil.copytree(item, data_dir / item.name, dirs_exist_ok=True)

    result = subprocess.run(
        ["git", "add", "-A"], cwd=backup_dir, capture_output=True
    )
    result = subprocess.run(
        ["git", "commit", "-m", "dcai config backup"], cwd=backup_dir, capture_output=True
    )
    result = subprocess.run(
        ["git", "push", "origin", "HEAD"], cwd=backup_dir, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Backup push failed: {result.stderr}")
        return False

    shutil.rmtree(backup_dir)
    print("Backup pushed successfully.")
    return True


def backup_pull(repo_url: str = None):
    if not repo_url:
        repo_url = os.environ.get("DCAI_BACKUP_REPO")
    if not repo_url:
        print("No backup repo configured.")
        return False

    backup_dir = Path("/tmp/dcai-restore-tmp")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, str(backup_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Failed to clone backup repo: {result.stderr}")
        return False

    config_dir = backup_dir / "config"
    if config_dir.exists():
        for item in config_dir.iterdir():
            dest = CONFIG_DIR / item.name
            shutil.copy2(item, dest)

    data_dir = backup_dir / "data"
    if data_dir.exists():
        for item in data_dir.iterdir():
            dest = DATA_DIR / item.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)

    shutil.rmtree(backup_dir)
    print("Backup restored successfully.")
    print("Note: API keys in config.yaml were NOT backed up. You may need to re-enter them.")
    return True


def load_config_for_backup() -> dict:
    config_path = get_config_path()
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}
