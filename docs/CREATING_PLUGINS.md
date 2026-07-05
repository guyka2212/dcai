# Creating DCAI Plugins

A plugin is a small repository that extends DCAI with custom commands. This guide walks you through creating, testing, and publishing a plugin.

## Folder Structure

Every plugin is a directory (or git repo) with this minimal layout:

```
my-plugin/
├── plugin.yaml          # Required: manifest file
├── main.py              # Your entrypoint script (name must match plugin.yaml)
└── (any other files)
```

## The `plugin.yaml` Manifest

```yaml
name: my-plugin          # Required: unique plugin name
version: 1.0.0           # Required: semver
author: Your Name        # Optional but recommended
description: Short description of what my plugin does
entrypoint: main.py      # Required: script that DCAI executes
commands:                # Optional: list of commands this plugin registers
  - name: my-command
    description: What this command does
  - name: another-command
    description: Another command
```

### Required Fields

| Field        | Description |
|-------------|-------------|
| `name`      | Unique identifier for the plugin. Used for install/remove/update. |
| `version`   | Semantic version string (e.g. `1.0.0`). |
| `entrypoint` | Path relative to the plugin root to the main script. Can be `.py`, `.sh`, or any executable. |

### Optional Fields

| Field         | Description |
|--------------|-------------|
| `author`     | Your name or handle. |
| `description` | Short description (one line). |
| `commands`   | List of command objects with `name` and `description`. |

## How the Entrypoint is Invoked

DCAI runs the entrypoint script with:

```
python /path/to/plugin/main.py <command-name> [args...]
```

- The first argument is the command name being called.
- Any additional arguments from the user are passed through.

### Exit Code Contract

- **0**: Success
- **Non-zero**: Failure (DCAI reports the error to the user)

### Stdout / Stderr

Anything your script writes to stdout or stderr is shown directly to the user. Use this for output, errors, or prompts.

## Accessing DCAI's Shared Helpers

Your plugin can import DCAI's shared `run_in_terminal` function if placed in the same Python path during development, but for distribution it's better to call it directly from within your script if needed.

If your plugin is a shell script, `run_in_terminal` is available as a command:

```sh
# In your shell entrypoint, you can call
dcai run_in_terminal "your command"
```

Or, in a Python entrypoint, check if DCAI is available:

```python
import subprocess
import sys

def run_in_terminal(cmd):
    """Simple fallback — runs command inline or in new terminal."""
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == "my-command":
        run_in_terminal("echo Hello from my plugin!")
```

## Worked Example 1: Simple "open-spotify" Plugin

This plugin adds a single command to open Spotify.

### `plugin.yaml`

```yaml
name: open-spotify
version: 1.0.0
author: DCAI Community
description: Opens Spotify desktop app
entrypoint: main.sh
commands:
  - name: open-spotify
    description: Launch Spotify
```

### `main.sh`

```sh
#!/usr/bin/env bash
# Args: <command-name> [extra-args...]
# This plugin only has one command, so we just run it.

if command -v spotify &> /dev/null; then
    spotify
elif command -v flatpak &> /dev/null; then
    flatpak run com.spotify.Client
else
    echo "Spotify not found. Install it from https://spotify.com"
    exit 1
fi
```

Make sure to `chmod +x main.sh`.

## Worked Example 2: Web API Plugin

This plugin calls a weather API and prints formatted output.

### `plugin.yaml`

```yaml
name: weather
version: 1.0.0
author: DCAI Community
description: Get current weather for a city
entrypoint: main.py
commands:
  - name: weather
    description: Show weather for a city (usage: weather <city-name>)
```

### `main.py`

```python
#!/usr/bin/env python3
import sys
import urllib.request
import json

def get_weather(city: str):
    """Fetch and display weather for a city using wttr.in."""
    encoded = urllib.parse.quote(city)
    url = f"https://wttr.in/{encoded}?format=%C+%t+%w+%h"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode()
            print(f"Weather for {city}: {data}")
    except Exception as e:
        print(f"Failed to get weather: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == "weather":
        city = sys.argv[2] if len(sys.argv) > 2 else "London"
        get_weather(city)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
```

## Publishing Your Plugin

1. Create a **public GitHub repository** with your plugin files.
2. Add the topic tag **`dcai-plugin`** to your repo (Settings → Topics) so it's discoverable.
3. Optionally submit it to the community plugin list by opening an issue on the [dcai repo](https://github.com/your-org/dcai).

Users install it with:

```bash
dcai plugin install https://github.com/your-org/your-plugin
```

## Best Practices

- Keep plugins focused — one purpose per plugin.
- Test your plugin by running the entrypoint script directly first.
- Use `sys.exit(0)` for success, `sys.exit(1)` for failures.
- Print useful error messages to stderr (`print(msg, file=sys.stderr)`).
- Don't hardcode paths — use environment variables or config if needed.
