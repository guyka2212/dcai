import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
import questionary

from dcai.config import load_config, save_config, ensure_dirs
from dcai.basic import get_commands, run_command, show_help
from dcai import ai_mode
from dcai import plugins as plugin_mod
from dcai import backup as backup_mod

app = typer.Typer(
    name="dcai",
    help="Desktop Control AI — terminal-based control assistant",
    add_completion=False,
)
console = Console()


class Back(Exception):
    pass


def handle_slash(inp: str | None) -> str | None:
    if not inp:
        return None
    val = inp.strip().lower()
    if val in ("/exit", "/quit"):
        console.print("Goodbye!")
        raise typer.Exit()
    if val == "/back":
        raise Back()
    if val == "/clear":
        console.clear()
    return inp


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        interactive_menu()


def interactive_menu():
    ensure_dirs()
    while True:
        try:
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
                    "Exit (/exit)",
                ],
            ).ask()

            if choice is None:
                continue
            if choice == "Exit (/exit)":
                console.print("Goodbye!")
                raise typer.Exit()
            elif choice == "Basic Mode":
                basic_mode_menu()
            elif choice == "AI Mode":
                ai_mode_menu()
            elif choice == "Plugins":
                plugins_menu()
            elif choice == "Settings / Backup":
                settings_menu()
        except Back:
            continue


def run_command_from_menu(commands: dict):
    while True:
        raw = questionary.text("Enter command (or /help for list)").ask()
        if raw is None:
            raise typer.Exit()
        try:
            inp = handle_slash(raw)
        except Back:
            raise
        if inp is None:
            raise Back()

        parts = inp.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd in ("/help", "help"):
            if arg:
                show_help(arg)
            else:
                show_help()
            console.print()
            continue

        if cmd not in commands:
            console.print(f"[red]Unknown command: {cmd}. Type '/help' to see all commands.[/red]")
            continue

        entry = commands[cmd]
        if entry.get("usage") and not arg:
            arg = questionary.text(f"Argument for '{cmd}'").ask()
            try:
                handle_slash(arg)
            except Back:
                continue

        console.print(f"Running: {cmd}")
        run_command(cmd, arg)
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()


def basic_mode_menu():
    try:
        console.clear()
        console.print("[bold cyan]Basic Mode[/bold cyan]\n")
        commands = get_commands()
        run_command_from_menu(commands)
    except Back:
        pass


def ai_mode_menu():
    if not ai_mode.is_configured():
        console.print("AI Mode is not configured. Starting setup...")
        ai_mode.first_run_wizard()
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        return

    try:
        prompt = questionary.text("Your request (or /back to go back)").ask()
        handle_slash(prompt)
    except Back:
        return
    ai_mode.process_request(prompt)
    questionary.press_any_key_to_continue("\nPress any key to continue...").ask()


def plugins_menu():
    try:
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
                    "Back to main menu (/back)",
                ],
            ).ask()

            if choice is None:
                break
            if choice == "Back to main menu (/back)":
                break
            elif choice == "List installed plugins":
                plugin_mod.list_plugins()
            elif choice == "Install plugin from URL":
                url = questionary.text("GitHub URL").ask()
                try:
                    handle_slash(url)
                except Back:
                    continue
                if url:
                    plugin_mod.install_plugin(url)
            elif choice == "Remove plugin":
                name = questionary.text("Plugin name to remove").ask()
                try:
                    handle_slash(name)
                except Back:
                    continue
                if name:
                    plugin_mod.remove_plugin(name)
            elif choice == "Update plugin":
                name = questionary.text("Plugin name to update").ask()
                try:
                    handle_slash(name)
                except Back:
                    continue
                if name:
                    plugin_mod.update_plugin(name)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
    except Back:
        pass


def settings_menu():
    try:
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
                    "Back to main menu (/back)",
                ],
            ).ask()

            if choice is None:
                break
            if choice == "Back to main menu (/back)":
                break
            elif choice == "View current config":
                config = load_config()
                console.print(config)
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
            elif choice == "Backup config to GitHub":
                url = questionary.text(
                    "GitHub repo URL (or leave empty to use DCAI_BACKUP_REPO env var)"
                ).ask()
                try:
                    handle_slash(url)
                except Back:
                    continue
                backup_mod.backup_push(url if url else None)
            elif choice == "Restore config from GitHub":
                url = questionary.text(
                    "GitHub repo URL (or leave empty to use DCAI_BACKUP_REPO env var)"
                ).ask()
                try:
                    handle_slash(url)
                except Back:
                    continue
                backup_mod.backup_pull(url if url else None)
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
    except Back:
        pass


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
