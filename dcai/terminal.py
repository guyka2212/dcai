import os
import subprocess
import shutil
import logging

logger = logging.getLogger(__name__)


def is_ssh_session() -> bool:
    return bool(os.environ.get("SSH_TTY") or os.environ.get("SSH_CONNECTION"))


def detect_terminal_emulator() -> str | None:
    candidates = [
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "lxterminal",
        "tilix",
        "alacritty",
        "kitty",
        "foot",
        "xterm",
    ]
    for term in candidates:
        if shutil.which(term):
            return term
    return None


def run_in_terminal(cmd: str) -> int:
    if is_ssh_session():
        logger.info("SSH session detected — running inline")
        result = subprocess.run(cmd, shell=True)
        return result.returncode

    term = detect_terminal_emulator()
    if not term:
        logger.warning("No terminal emulator found — falling back to inline execution")
        result = subprocess.run(cmd, shell=True)
        return result.returncode

    if term == "gnome-terminal":
        full_cmd = [term, "--", "bash", "-c", f"{cmd}; exec bash"]
    elif term == "konsole":
        full_cmd = [term, "--hold", "-e", "bash", "-c", cmd]
    elif term == "xfce4-terminal":
        full_cmd = [term, "--hold", "--command", f"bash -c '{cmd}'"]
    elif term == "lxterminal":
        full_cmd = [term, "--command", f"bash -c '{cmd}; exec bash'"]
    elif term == "tilix":
        full_cmd = [term, "--command", f"bash -c '{cmd}; exec bash'"]
    elif term == "alacritty":
        full_cmd = [term, "-e", "bash", "-c", f"{cmd}; exec bash"]
    elif term == "kitty":
        full_cmd = [term, "bash", "-c", f"{cmd}; exec bash"]
    elif term == "foot":
        full_cmd = [term, "bash", "-c", f"{cmd}; exec bash"]
    else:
        full_cmd = [term, "-e", f"bash -c '{cmd}; exec bash'"]

    logger.info(f"Opening terminal: {term}")
    subprocess.Popen(full_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0
