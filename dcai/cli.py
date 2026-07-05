import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import questionary

from dcai.config import load_config, save_config, ensure_dirs
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

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Basic Mode",
                "AI Mode",
                "Plugins",
                "Settings / Backup",
                "Exit",
            ],
        ).ask()

        if choice == "Basic Mode":
            basic_mode_menu()
        elif choice == "AI Mode":
            ai_mode_menu()
        elif choice == "Plugins":
            plugins_menu()
        elif choice == "Settings / Backup":
            settings_menu()
        elif choice == "Exit":
            console.print("Goodbye!")
            raise typer.Exit()


def basic_mode_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Basic Mode[/bold cyan]\n")
        commands = get_commands()
        items = list(commands.items())

        choices = [f"{name} — {entry['description']}" for name, entry in items]
        choices.append("Back to main menu")

        choice = questionary.select("Select a command", choices=choices).ask()

        if choice == "Back to main menu":
            break

        name = choice.split(" — ")[0]
        console.print(f"Running: {name}")
        run_command(name)
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()


def ai_mode_menu():
    if not ai_mode.is_configured():
        console.print("AI Mode is not configured. Starting setup...")
        ai_mode.first_run_wizard()
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        return

    prompt = questionary.text("Enter your request (or leave empty to go back)").ask()
    if not prompt:
        return
    ai_mode.process_request(prompt)
    questionary.press_any_key_to_continue("\nPress any key to continue...").ask()


def plugins_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Plugin Manager[/bold cyan]\n")

        choice = questionary.select(
            "Select an option",
            choices=[
                "List installed plugins",
                "Install plugin from URL",
                "Remove plugin",
                "Update plugin",
                "Back to main menu",
            ],
        ).ask()

        if choice == "List installed plugins":
            plugin_mod.list_plugins()
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Install plugin from URL":
            url = questionary.text("GitHub URL").ask()
            if url:
                plugin_mod.install_plugin(url)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Remove plugin":
            name = questionary.text("Plugin name to remove").ask()
            if name:
                plugin_mod.remove_plugin(name)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Update plugin":
            name = questionary.text("Plugin name to update").ask()
            if name:
                plugin_mod.update_plugin(name)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Back to main menu":
            break


def settings_menu():
    while True:
        console.clear()
        console.print("[bold cyan]Settings / Backup[/bold cyan]\n")

        choice = questionary.select(
            "Select an option",
            choices=[
                "View current config",
                "Reset AI Mode configuration",
                "Backup config to GitHub",
                "Restore config from GitHub",
                "Back to main menu",
            ],
        ).ask()

        if choice == "View current config":
            config = load_config()
            console.print(config)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Reset AI Mode configuration":
            confirm = questionary.confirm(
                "Reset AI Mode config? This cannot be undone",
                default=False,
            ).ask()
            if confirm:
                config = load_config()
                config.pop("ai", None)
                save_config(config)
                console.print("[green]AI configuration reset.[/green]")
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Backup config to GitHub":
            url = questionary.text(
                "GitHub repo URL (or leave empty to use DCAI_BACKUP_REPO env var)"
            ).ask()
            backup_mod.backup_push(url if url else None)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Restore config from GitHub":
            url = questionary.text(
                "GitHub repo URL (or leave empty to use DCAI_BACKUP_REPO env var)"
            ).ask()
            backup_mod.backup_pull(url if url else None)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        elif choice == "Back to main menu":
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
