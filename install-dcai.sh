#!/usr/bin/env bash
set -euo pipefail

# ─── Color helpers ───────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok()   { echo -e " ${GREEN}✅${NC} $1"; }
fail() { echo -e " ${RED}❌${NC} $1"; }
info() { echo -e " ${CYAN}ℹ️${NC} $1"; }
warn() { echo -e " ${YELLOW}⚠️${NC} $1"; }

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/guyka2212/dcai"
REPO_BRANCH="main"
INSTALL_DIR="${DCAI_DIR:-"${XDG_DATA_HOME:-$HOME/.local/share}/dcai"}"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dcai"
DCAI_CMD="$BIN_DIR/dcai"
PYTHON=""

# ─── Step 1: Detect OS & package manager ──────────────────────────────────────
detect_os() {
    info "Detecting OS..."
    case "$(uname -s)" in
        Linux)
            OS="linux"
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS_NAME="$ID"
            elif command -v lsb_release &>/dev/null; then
                OS_NAME=$(lsb_release -si)
            else
                OS_NAME="unknown"
            fi
            ;;
        Darwin)
            OS="macos"
            OS_NAME="macos"
            ;;
        *)
            fail "Unsupported OS: $(uname -s)"
            exit 1
            ;;
    esac
    ok "Detected: $OS ($OS_NAME)"
}

detect_pm() {
    info "Detecting package manager..."
    if command -v apt &>/dev/null; then
        PM="apt"
    elif command -v dnf &>/dev/null; then
        PM="dnf"
    elif command -v pacman &>/dev/null; then
        PM="pacman"
    elif command -v brew &>/dev/null; then
        PM="brew"
    elif command -v zypper &>/dev/null; then
        PM="zypper"
    else
        PM="unknown"
    fi
    ok "Package manager: ${PM:-none detected}"
}

# ─── Step 2: Check / install Python ───────────────────────────────────────────
ensure_python() {
    info "Checking Python..."
    PYTHON=""

    # Try python3 first
    if command -v python3 &>/dev/null; then
        ver=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
        if [ "$(echo "$ver >= 3.11" | bc -l 2>/dev/null)" = "1" ] || [ "$ver" = "3.11" ] || [ "$ver" = "3.12" ] || [ "$ver" = "3.13" ] || [ "$ver" = "3.14" ]; then
            PYTHON="python3"
            ok "Python $ver found"
            return
        fi
    fi

    warn "Python 3.11+ is required but not found."
    echo -n "Install Python 3.11+ now? [y/N]: "
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        fail "Python 3.11+ is required. Install it manually, then re-run this script."
        exit 1
    fi

    case "$PM" in
        apt)
            sudo apt update && sudo apt install -y python3 python3-pip python3-venv
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip
            ;;
        pacman)
            sudo pacman -S --noconfirm python python-pip
            ;;
        brew)
            brew install python
            ;;
        zypper)
            sudo zypper install -y python3 python3-pip
            ;;
        *)
            fail "Don't know how to install Python on this system. Install Python 3.11+ manually."
            exit 1
            ;;
    esac

    if command -v python3 &>/dev/null; then
        ver=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
        PYTHON="python3"
        ok "Python $ver installed"
    else
        fail "Python installation failed."
        exit 1
    fi
}

# ─── Step 3: Check / install git ──────────────────────────────────────────────
ensure_git() {
    info "Checking git..."
    if command -v git &>/dev/null; then
        ok "git found"
        return
    fi
    warn "git is required but not found."
    echo -n "Install git now? [y/N]: "
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        fail "git is required."
        exit 1
    fi
    case "$PM" in
        apt) sudo apt install -y git ;;
        dnf) sudo dnf install -y git ;;
        pacman) sudo pacman -S --noconfirm git ;;
        brew) brew install git ;;
        zypper) sudo zypper install -y git ;;
        *) fail "Don't know how to install git. Install it manually."; exit 1 ;;
    esac
    ok "git installed"
}

# ─── Step 4: Clone / update the repo ──────────────────────────────────────────
ensure_repo() {
    info "Setting up DCAI in $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"

    if [ -d "$INSTALL_DIR/.git" ]; then
        warn "DCAI already installed — updating..."
        git -C "$INSTALL_DIR" pull --ff-only
        ok "DCAI updated"
    else
        if [ -d "$INSTALL_DIR" ] && [ "$(ls -A "$INSTALL_DIR")" ]; then
            warn "Install directory not empty — cloning into temp then merging..."
            tmpdir=$(mktemp -d)
            git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$tmpdir"
            cp -r "$tmpdir"/* "$INSTALL_DIR"/
            rm -rf "$tmpdir"
        else
            git clone --depth=1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
        fi
        ok "DCAI cloned"
    fi
}

# ─── Step 5: Install Python deps & create symlink ─────────────────────────────
install_deps_and_link() {
    info "Installing Python dependencies..."
    "$PYTHON" -m pip install --quiet -e "$INSTALL_DIR" 2>/dev/null || "$PYTHON" -m pip install --quiet --user -e "$INSTALL_DIR"
    ok "Dependencies installed"

    info "Creating symlink..."
    mkdir -p "$BIN_DIR"
    ln -sf "$INSTALL_DIR/install-dcai.sh" "$DCAI_CMD" 2>/dev/null || true

    # Try to find the actual dcai entrypoint
    if [ -f "$INSTALL_DIR/dcai/__main__.py" ]; then
        cat > "$DCAI_CMD" << 'SCRIPT'
#!/usr/bin/env bash
exec python3 -m dcai "$@"
SCRIPT
        chmod +x "$DCAI_CMD"
        ok "Symlink created at $DCAI_CMD"
    else
        warn "Could not create dcai command — expected structure not found"
    fi

    # Check PATH
    case ":$PATH:" in
        *:"$BIN_DIR":*) ;;
        *)
            warn "$BIN_DIR is not on your PATH."
            echo -n "Add it to ~/.bashrc / ~/.zshrc? [y/N]: "
            read -r response
            if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
                shellrc="$HOME/.bashrc"
                if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
                    shellrc="$HOME/.zshrc"
                fi
                echo "" >> "$shellrc"
                echo "# Added by dcai installer" >> "$shellrc"
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$shellrc"
                ok "Added $BIN_DIR to $shellrc"
                warn "Restart your shell or run: export PATH=\"\$PATH:$BIN_DIR\""
            fi
            ;;
    esac
}

# ─── First-time setup ────────────────────────────────────────────────────────
run_setup() {
    info "Running first-time setup..."
    if command -v dcai &>/dev/null || [ -x "$DCAI_CMD" ]; then
        dcai 2>/dev/null || "$PYTHON" -m dcai 2>/dev/null || true
        ok "Setup wizard launched"
    else
        warn "Run 'dcai' (or '$DCAI_CMD') after installation to complete setup."
    fi
}

# ─── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}      DCAI — Desktop Control AI Installer   ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    detect_os
    detect_pm
    ensure_python
    ensure_git
    ensure_repo
    install_deps_and_link
    run_setup

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}      ✅ Installation complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Run ${CYAN}dcai${NC} to get started."
    echo "  Run ${CYAN}dcai --help${NC} for all commands."
    echo ""
}

main
