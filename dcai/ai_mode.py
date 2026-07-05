import os
import subprocess
import shutil
import json
from typing import Optional

from dcai.config import load_config, save_config
from dcai.terminal import run_in_terminal


SPEC_TABLE = {
    "large": {
        "label": "Large (≥70B-class)",
        "model": "llama3.1:70b",
        "require_gpu_vram_gb": 16,
        "require_ram_gb": 32,
    },
    "medium": {
        "label": "Medium (~7-8B class)",
        "model": "llama3.1:8b",
        "require_gpu_vram_gb": 6,
        "require_ram_gb": 16,
    },
    "small": {
        "label": "Small (~2-3B class)",
        "model": "phi3:mini",
        "require_ram_gb": 8,
    },
}


def detect_specs() -> dict:
    specs = {}

    try:
        mem_info = os.popen("grep MemTotal /proc/meminfo 2>/dev/null").read().strip()
        if mem_info:
            kb = int(mem_info.split()[1])
            specs["ram_gb"] = kb // (1024 * 1024)
        else:
            specs["ram_gb"] = 0
    except Exception:
        specs["ram_gb"] = 0

    try:
        import shutil
        _, _, free = shutil.disk_usage("/")
        specs["free_disk_gb"] = free // (2**30)
    except Exception:
        specs["free_disk_gb"] = 0

    try:
        cpu_count = os.cpu_count() or 0
        specs["cpu_cores"] = cpu_count
    except Exception:
        specs["cpu_cores"] = 0

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                specs["gpu"] = parts[0].strip()
                vram_mb = int(parts[1].strip().split()[0])
                specs["gpu_vram_gb"] = vram_mb // 1024
            else:
                specs["gpu"] = None
                specs["gpu_vram_gb"] = 0
        except Exception:
            specs["gpu"] = None
            specs["gpu_vram_gb"] = 0
    else:
        specs["gpu"] = None
        specs["gpu_vram_gb"] = 0

    return specs


def recommend_model(specs: dict) -> str:
    gpu_vram = specs.get("gpu_vram_gb", 0)
    ram = specs.get("ram_gb", 0)

    if gpu_vram >= SPEC_TABLE["large"]["require_gpu_vram_gb"] and ram >= SPEC_TABLE["large"]["require_ram_gb"]:
        return SPEC_TABLE["large"]["model"]
    elif gpu_vram >= SPEC_TABLE["medium"]["require_gpu_vram_gb"] or ram >= SPEC_TABLE["medium"]["require_ram_gb"]:
        return SPEC_TABLE["medium"]["model"]
    else:
        return SPEC_TABLE["small"]["model"]


def check_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def check_ollama_running() -> bool:
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def install_ollama() -> bool:
    print("Installing Ollama...")
    curl_available = shutil.which("curl")
    if not curl_available:
        print("curl is required to install Ollama. Please install curl first.")
        return False
    result = subprocess.run(
        ["curl", "-fsSL", "https://ollama.com/install.sh", "-o", "/tmp/ollama-install.sh"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("Failed to download Ollama install script")
        return False
    result = subprocess.run(["sh", "/tmp/ollama-install.sh"])
    return result.returncode == 0


def pull_model(model: str) -> bool:
    if not check_ollama_running():
        print("Ollama is not running. Please start it with 'ollama serve'")
        return False
    print(f"Pulling model: {model} (this may take a while)...")
    result = subprocess.run(["ollama", "pull", model])
    return result.returncode == 0


def is_configured() -> bool:
    config = load_config()
    return config.get("ai", {}).get("configured", False)


def first_run_wizard():
    import questionary

    print("=== DCAI AI Mode — First-time Setup ===\n")

    config = load_config()
    ai_config = config.get("ai", {})

    choice = questionary.select(
        "How would you like to use AI?",
        choices=[
            "I already have an Ollama server running",
            "I want to use an API key (OpenAI, Anthropic, etc.)",
            "Install Ollama locally",
        ],
    ).ask()

    if choice == "I already have an Ollama server running":
        host = questionary.text(
            "Ollama host", default="http://localhost:11434"
        ).ask()
        ai_config["provider"] = "ollama"
        ai_config["host"] = host
        ai_config["configured"] = True
        print("Ollama server configured.")

    elif choice == "I want to use an API key (OpenAI, Anthropic, etc.)":
        provider = questionary.select(
            "Provider",
            choices=["openai", "anthropic", "other"],
        ).ask()
        key = questionary.password("API key").ask()
        ai_config["provider"] = provider
        ai_config["api_key"] = key
        ai_config["configured"] = True
        print(f"{provider.upper()} API key configured.")

    elif choice == "Install Ollama locally":
        print("Checking specs for model recommendation...")
        specs = detect_specs()
        model = recommend_model(specs)
        print(f"Detected: {specs.get('ram_gb', '?')}GB RAM, {specs.get('gpu_vram_gb', 'N/A')}GB GPU VRAM")
        print(f"Recommended model: {model}")

        if not check_ollama_installed():
            ok = questionary.confirm(
                "Ollama is not installed. Install now?", default=True
            ).ask()
            if ok:
                if install_ollama():
                    print("Ollama installed successfully.")
                else:
                    print("Ollama installation failed.")
                    return

        if check_ollama_installed():
            if not check_ollama_running():
                print("Starting Ollama...")
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time
                time.sleep(3)

            pull = questionary.confirm(
                f"Pull model '{model}' now?", default=True
            ).ask()
            if pull:
                pull_model(model)

        ai_config["provider"] = "ollama"
        ai_config["host"] = "http://localhost:11434"
        ai_config["model"] = model
        ai_config["configured"] = True

    config["ai"] = ai_config
    save_config(config)
    print("\nAI Mode is now configured. Run 'dcai ai \"your request\"' to get started.")


def query_ollama(prompt: str, host: str, model: str) -> Optional[str]:
    import requests
    try:
        resp = requests.post(
            f"{host.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        print(f"Ollama query failed: {e}")
        return None


def query_api(prompt: str, provider: str, api_key: str) -> Optional[str]:
    import requests
    try:
        if provider == "openai":
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        elif provider == "anthropic":
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        else:
            print(f"Unknown provider: {provider}")
            return None
    except Exception as e:
        print(f"API query failed: {e}")
        return None


def process_request(prompt: str):
    config = load_config()
    ai_config = config.get("ai", {})

    if not ai_config.get("configured"):
        print("AI Mode is not configured. Run 'dcai ai' without arguments to start setup.")
        return

    print(f"Processing: {prompt}")
    print()

    system_prompt = (
        "You are DCAI, a Desktop Control AI assistant. "
        "You can answer questions directly OR suggest a shell command to accomplish the task. "
        "If a shell command is appropriate, output it on a line starting with 'CMD: ' followed by the command. "
        "Otherwise, just answer the question conversationally. "
        "Never execute anything without confirmation."
    )

    full_prompt = f"{system_prompt}\n\nUser request: {prompt}"

    response = None
    provider = ai_config.get("provider")

    if provider == "ollama":
        host = ai_config.get("host", "http://localhost:11434")
        model = ai_config.get("model", "llama3.1:8b")
        response = query_ollama(full_prompt, host, model)
    elif provider in ("openai", "anthropic"):
        api_key = ai_config.get("api_key")
        if not api_key:
            print("API key not found in config. Run setup again.")
            return
        response = query_api(full_prompt, provider, api_key)
    else:
        print(f"Unknown provider: {provider}")
        return

    if not response:
        print("No response from AI.")
        return

    print(response)

    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("CMD:"):
            cmd = line[4:].strip()
            print(f"\nProposed command: {cmd}")
            confirm = input("Execute this command? [y/N]: ").strip().lower()
            if confirm == "y":
                run_in_terminal(cmd)
            else:
                print("Command skipped.")
            break
