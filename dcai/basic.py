import os
import shutil
import subprocess
import yaml
from typing import Optional

from dcai.terminal import run_in_terminal
from dcai.config import CONFIG_DIR


def load_registry() -> dict:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "registry.yaml")
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_commands() -> dict:
    registry = load_registry()
    return registry.get("commands", {})


def get_desktop_env():
    return os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def run_command(name: str, args: Optional[str] = None) -> int:
    commands = get_commands()
    if name not in commands:
        print(f"Unknown command: {name}")
        return 1

    entry = commands[name]
    action = entry["action"]

    if action == "sysinfo_custom":
        return sysinfo()
    elif action == "update_system_custom":
        return update_system()
    elif action == "lock_screen_custom":
        return lock_screen()
    elif action == "screenshot_custom":
        return screenshot()
    elif action == "wifi_toggle_custom":
        return wifi_toggle()
    elif action == "bluetooth_toggle_custom":
        return bluetooth_toggle()
    elif action.startswith("pkill"):
        if not args:
            print("Usage: dcai run kill-process <name>")
            return 1
        return run_in_terminal(f"pkill -f {args}")
    elif action == "open_project_custom":
        if not args:
            print("Usage: dcai run open-project <path>")
            return 1
        return open_project(args)
    else:
        return run_in_terminal(action)


def sysinfo() -> int:
    info = []

    try:
        import os
        cpu_info = os.popen("lscpu 2>/dev/null | grep 'Model name' | head -1").read().strip()
        if not cpu_info:
            cpu_info = os.popen("cat /proc/cpuinfo 2>/dev/null | grep 'model name' | head -1").read().strip()
        info.append(f"CPU: {cpu_info.split(':')[-1].strip() if cpu_info else 'N/A'}")
    except Exception:
        info.append("CPU: N/A")

    try:
        mem = os.popen("free -h 2>/dev/null | grep Mem").read().strip()
        if mem:
            parts = mem.split()
            info.append(f"RAM: {parts[1]} total, {parts[2]} used, {parts[3]} free")
    except Exception:
        info.append("RAM: N/A")

    try:
        import shutil
        disk = shutil.disk_usage("/")
        info.append(f"Disk: {disk.used // (2**30)}G used / {disk.total // (2**30)}G total")
    except Exception:
        info.append("Disk: N/A")

    try:
        gpu = os.popen("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || glxinfo 2>/dev/null | grep 'OpenGL renderer' | head -1 || lspci 2>/dev/null | grep -i 'vga' | head -1").read().strip()
        if gpu:
            info.append(f"GPU: {gpu}")
        else:
            info.append("GPU: N/A (no discrete GPU detected)")
    except Exception:
        info.append("GPU: N/A")

    print("\n".join(info))
    return 0


def detect_package_manager() -> str:
    for pm in ["apt", "dnf", "pacman", "zypper", "brew"]:
        if shutil.which(pm):
            return pm
    return "unknown"


def update_system() -> int:
    pm = detect_package_manager()
    cmds = {
        "apt": "sudo apt update && sudo apt upgrade -y",
        "dnf": "sudo dnf upgrade -y",
        "pacman": "sudo pacman -Syu",
        "zypper": "sudo zypper update",
        "brew": "brew update && brew upgrade",
    }
    cmd = cmds.get(pm)
    if not cmd:
        print(f"No known update command for package manager: {pm}")
        return 1
    print(f"Using {pm} — running system update...")
    return run_in_terminal(cmd)


def lock_screen() -> int:
    de = get_desktop_env()
    if "gnome" in de:
        return subprocess.run(["gnome-screensaver-command", "--lock"]).returncode
    elif "kde" in de or "plasma" in de:
        return subprocess.run(["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"]).returncode
    elif "xfce" in de:
        return subprocess.run(["xflock4"]).returncode
    else:
        for cmd in ["xdg-screensaver lock", "dm-tool lock", "i3lock", "slock"]:
            if shutil.which(cmd.split()[0]):
                return subprocess.run(cmd, shell=True).returncode
        print("No known screen locker found")
        return 1


def screenshot() -> int:
    de = get_desktop_env()
    if "gnome" in de:
        return subprocess.run(["gnome-screenshot", "-i"]).returncode
    elif "kde" in de:
        return subprocess.run(["spectacle", "-b"]).returncode
    elif "xfce" in de:
        return subprocess.run(["xfce4-screenshooter"]).returncode
    else:
        for cmd in ["scrot", "maim", "import"]:
            if shutil.which(cmd):
                return subprocess.run([cmd, f"{os.path.expanduser('~')}/screenshot_$(date +%s).png"], shell=True).returncode
        print("No screenshot tool found")
        return 1


def open_project(path: str) -> int:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vim"
    return run_in_terminal(f"cd {path} && {editor} .")


def wifi_toggle() -> int:
    if shutil.which("nmcli"):
        result = subprocess.run(["nmcli", "radio", "wifi"], capture_output=True, text=True)
        is_on = result.stdout.strip() == "enabled"
        new_state = "off" if is_on else "on"
        return subprocess.run(["nmcli", "radio", "wifi", new_state]).returncode
    elif shutil.which("rfkill"):
        result = subprocess.run(["rfkill", "list", "wifi"], capture_output=True, text=True)
        return subprocess.run(["rfkill", "toggle", "wifi"]).returncode
    else:
        print("No Wi-Fi control tool found (try nmcli or rfkill)")
        return 1


def bluetooth_toggle() -> int:
    if shutil.which("bluetoothctl"):
        result = subprocess.run(["bluetoothctl", "show"], capture_output=True, text=True)
        is_on = "Powered: yes" in result.stdout
        cmd = "power on" if not is_on else "power off"
        return subprocess.run(["bluetoothctl", cmd]).returncode
    elif shutil.which("rfkill"):
        return subprocess.run(["rfkill", "toggle", "bluetooth"]).returncode
    else:
        print("No Bluetooth control tool found (try bluetoothctl or rfkill)")
        return 1
