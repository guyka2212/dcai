# Installing DCAI Plugins

## What is a Plugin?

A DCAI plugin is a small script or program that adds new commands to DCAI. Plugins can run **any code on your machine** — treat them like browser extensions or any third-party software.

**Always review the source before installing a plugin.**

## Install a Plugin

```bash
dcai plugin install https://github.com/<user>/<repo>
```

This will:

1. Clone the repository to a temporary directory.
2. Validate that `plugin.yaml` exists and is well-formed.
3. **Show you the plugin manifest** (name, author, description, commands).
4. Ask for your explicit confirmation before copying the files.

Nothing is installed until you type `y`.

## List Installed Plugins

```bash
dcai plugin list
```

Shows every installed plugin, its version, and the commands it provides.

## Update a Plugin

```bash
dcai plugin update <plugin-name>
```

Runs `git pull` inside the plugin's directory to fetch the latest version.

## Remove a Plugin

```bash
dcai plugin remove <plugin-name>
```

Deletes the plugin's directory and removes it from the registry.

## Where Plugins Are Stored

Plugins live in `~/.local/share/dcai/plugins/<name>/`.

You can browse them directly:

```bash
ls ~/.local/share/dcai/plugins/
```

## Trust Model

- DCAI does **not** sandbox plugin execution. A plugin runs with the same permissions as DCAI itself (your user account).
- Before installing, always check what commands the plugin registers and review the source code.
- Uninstall any plugin you no longer trust or use.
