# DCAI — Desktop Control AI

A terminal-based control assistant with three modes: **Basic**, **AI**, and **Plugins**.

```bash
curl -fsSL https://raw.githubusercontent.com/<you>/dcai/main/install-dcai.sh | bash
```

## Features

### ⚡ Basic Mode
Named commands for daily desktop actions:
- `dcai run open-firefox` — open apps
- `dcai run sysinfo` — system summary
- `dcai run screenshot` — capture screen
- `dcai run volume-up` — control audio
- `dcai run wifi-toggle` — toggle networking
- `dcai run update-system` — package manager update

Commands automatically detect whether you're in a local desktop session (opens a new terminal window) or over SSH (runs inline).

### 🧠 AI Mode
Natural language control with Ollama (local) or OpenAI/Anthropic (cloud):
- `dcai ai "what's using all my RAM?"`
- `dcai ai "open my project folder"`
- Auto spec-check to recommend the best local model
- **Never auto-executes** system-changing commands without your confirmation

### 🔌 Plugins
Extend DCAI with community plugins:
- `dcai plugin install https://github.com/<user>/<repo>`
- Transparent — see the manifest before installing
- Simple `plugin.yaml` manifest format
- Python and shell script entrypoints

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/<you>/dcai/main/install-dcai.sh | bash

# Launch interactive menu
dcai

# Or use subcommands directly
dcai run sysinfo
dcai ai "summarize my downloads folder"
dcai plugin list
```

## Installation

See [install-dcai.sh](install-dcai.sh) — the single-command installer handles:
- OS detection (Linux/macOS) and package manager
- Python 3.11+ check and install
- Git check and install  
- Clone repo to `~/.local/share/dcai`
- Create symlink at `~/.local/bin/dcai`
- First-time setup wizard

## Configuration

- Config: `~/.config/dcai/config.yaml`
- Data: `~/.local/share/dcai/`
- Plugins: `~/.local/share/dcai/plugins/`
- API keys stored with `600` permissions, never logged

## Backup

```bash
dcai backup push https://github.com/<you>/your-backup-repo
dcai backup pull https://github.com/<you>/your-backup-repo
```

Pushes/restores config and data (excluding secrets) to a private GitHub repo.

## Documentation

- [Creating Plugins](docs/CREATING_PLUGINS.md)
- [Installing Plugins](docs/INSTALLING_PLUGINS.md)

## License

MIT
