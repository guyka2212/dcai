import os
import sys
import shutil
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from dcai.config import load_config, save_config, ensure_dirs
from dcai.terminal import run_in_terminal, is_ssh_session
from dcai.basic import get_commands, run_command
from dcai import ai_mode
from dcai import plugins as plugin_mod
from dcai import backup as backup_mod

app = typer.Typer(
    name="dcai",
    help="Desktop Control AI — terminal-based control assistant",
    add_completion=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        interactive_menu()


def interactive_menu():
    ensure_dirs()
    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]DCAI — Desktop Control AI[/bold cyan]\n"
            "[dim]Terminal-based control assistant[/dim]",
            border_style="cyan",
        ))
        console.print()
        console.print("1. Basic Mode")
        console.print("2. AI Mode")
        console.print("3. Plugins")
        console.print("4. Settings / Backup")
        console.print("5. Exit")
        console.print()

        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            basic_mode_menu()
        elif choice == "2":
            ai_mode_menu()
        elif choice == "3":
            plugins_menu()
        elif choice == "4":
            settings_menu()
        elif choice == "5":
            console.print("Goodbye!")
            raise typer.Exit()


def basic_mode_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Basic Mode[/bold cyan]\n")
        commands = get_commands()
        items = list(commands.items())
        for i, (name, entry) in enumerate(items, 1):
            console.print(f"{i}. {name} — {entry['description']}")
        console.print(f"{len(items) + 1}. Back to main menu")
        console.print()

        choice = Prompt.ask("Select a command", choices=[str(i) for i in range(1, len(items) + 2)])

        if int(choice) == len(items) + 1:
            break

        name = items[int(choice) - 1][0]
        console.print(f"Running: {name}")
        run_command(name)
        Prompt.ask("\nPress Enter to continue")


def ai_mode_menu():
    if not ai_mode.is_configured():
        console.print("AI Mode is not configured. Starting setup...")
        ai_mode.first_run_wizard()
        Prompt.ask("\nPress Enter to continue")
        return

    prompt = Prompt.ask("Enter your request (or 'exit' to go back)")
    if prompt.lower() in ("exit", "back", "quit"):
        return
    ai_mode.process_request(prompt)
    Prompt.ask("\nPress Enter to continue")


def plugins_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Plugin Manager[/bold cyan]\n")
        console.print("1. List installed plugins")
        console.print("2. Install plugin from URL")
        console.print("3. Remove plugin")
        console.print("4. Update plugin")
        console.print("5. Back to main menu")
        console.print()

        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            plugin_mod.list_plugins()
            Prompt.ask("\nPress Enter to continue")
        elif choice == "2":
            url = Prompt.ask("GitHub URL")
            plugin_mod.install_plugin(url)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "3":
            name = Prompt.ask("Plugin name to remove")
            plugin_mod.remove_plugin(name)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "4":
            name = Prompt.ask("Plugin name to update")
            plugin_mod.update_plugin(name)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "5":
            break


def settings_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Settings / Backup[/bold cyan]\n")
        console.print("1. View current config")
        console.print("2. Reset AI Mode configuration")
        console.print("3. Backup config to GitHub")
        console.print("4. Restore config from GitHub")
        console.print("5. Back to main menu")
        console.print()

        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"])

        if choice == "1":
            config = load_config()
            console.print(config)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "2":
            confirm = Prompt.ask("Reset AI Mode config? This cannot be undone [y/N]")
            if confirm.lower() == "y":
                config = load_config()
                config.pop("ai", None)
                save_config(config)
                console.print("AI configuration reset.")
            Prompt.ask("\nPress Enter to continue")
        elif choice == "3":
            url = Prompt.ask("GitHub repo URL (or press Enter to use DCAI_BACKUP_REPO env var)")
            backup_mod.backup_push(url if url else None)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "4":
            url = Prompt.ask("GitHub repo URL (or press Enter to use DCAI_BACKUP_REPO env var)")
            backup_mod.backup_pull(url if url else None)
            Prompt.ask("\nPress Enter to continue")
        elif choice == "5":
            break


# --- Subcommands for power users/scripts ---

@app.command()
def run(
    command: str,
    args: Optional[list[str]] = typer.Argument(None),
):
    """Run a Basic Mode command directly."""
    arg_str = " ".join(args) if args else None
    sys.exit(run_command(command, arg_str))


@app.command()
def ai(
    prompt: Optional[str] = typer.Argument(None, help="Natural language request"),
):
    """Use AI Mode with a natural language request."""
    if not ai_mode.is_configured():
        console.print("AI Mode is not configured. Starting setup...")
        ai_mode.first_run_wizard()
        return
    if not prompt:
        ai_mode_menu()
        return
    ai_mode.process_request(prompt)


@app.command()
def plugin(
    action: str = typer.Argument(..., help="install / list / remove / update"),
    arg: Optional[str] = typer.Argument(None, help="Plugin name or URL"),
):
    """Manage plugins."""
    if action == "install":
        if not arg:
            console.print("Usage: dcai plugin install <github-url>")
            raise typer.Exit(1)
        plugin_mod.install_plugin(arg)
    elif action == "list":
        plugin_mod.list_plugins()
    elif action == "remove":
        if not arg:
            console.print("Usage: dcai plugin remove <name>")
            raise typer.Exit(1)
        plugin_mod.remove_plugin(arg)
    elif action == "update":
        if not arg:
            console.print("Usage: dcai plugin update <name>")
            raise typer.Exit(1)
        plugin_mod.update_plugin(arg)
    else:
        console.print(f"Unknown action: {action}. Use: install, list, remove, update")


@app.command()
def backup(
    action: str = typer.Argument(..., help="push / pull"),
    repo_url: Optional[str] = typer.Argument(None, help="GitHub repo URL"),
):
    """Backup or restore DCAI configuration."""
    if action == "push":
        backup_mod.backup_push(repo_url)
    elif action == "pull":
        backup_mod.backup_pull(repo_url)
    else:
        console.print("Usage: dcai backup push|pull [repo-url]")


@app.command()
def update():
    """Update DCAI to the latest version (git pull)."""
    import subprocess
    install_dir = os.environ.get("DCAI_DIR") or os.path.expanduser("~/.local/share/dcai")
    if not os.path.isdir(install_dir):
        console.print("DCAI installation not found. Re-run the install script.")
        raise typer.Exit(1)
    result = subprocess.run(["git", "-C", install_dir, "pull"], capture_output=True, text=True)
    console.print(result.stdout)
    if result.returncode != 0:
        console.print(f"[red]Update failed: {result.stderr}[/red]")
    else:
        console.print("[green]DCAI updated successfully.[/green]")


if __name__ == "__main__":
    app()
