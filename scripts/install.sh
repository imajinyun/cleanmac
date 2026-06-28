#!/usr/bin/env bash
# cleanmac installer script
# Installs cleanmac via pip into an isolated virtual environment.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/imajinyun/cleanmac/main/scripts/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/imajinyun/cleanmac/main/scripts/install.sh | bash -s -- --version 0.1.0
#
set -euo pipefail

REPO="imajinyun/cleanmac"
BRANCH="main"
VERSION=""
INSTALL_DIR="${HOME}/.local/cleanmac"
BIN_DIR="${HOME}/.local/bin"
PYTHON=""
VERBOSE=0

# --- helpers ---

log() { printf '%s\n' "$*"; }
log_verbose() { [ "$VERBOSE" -eq 1 ] && printf '%s\n' "$*" || true; }
error() { printf 'Error: %s\n' "$*" >&2; exit 1; }

# --- parse args ---

while [ $# -gt 0 ]; do
    case "$1" in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --help|-h)
            cat <<EOF
cleanmac installer

Usage:
  install.sh [options]

Options:
  --version VERSION  Install a specific version (default: latest release)
  --branch BRANCH    Install from a git branch (default: main)
  --repo REPO        GitHub repo (default: imajinyun/cleanmac)
  --dir DIR          Install directory (default: ~/.local/cleanmac)
  --verbose, -v      Verbose output
  --help, -h         Show this help

The installer creates an isolated venv at ~/.local/cleanmac/venv/
and symlinks the cleanmac binary to ~/.local/bin/cleanmac.
EOF
            exit 0
            ;;
        *)
            error "Unknown argument: $1"
            ;;
    esac
done

# --- find python ---

find_python() {
    for cmd in python3 python3.12 python3.11 python3.10 python3.9; do
        if command -v "$cmd" >/dev/null 2>&1; then
            local ver
            ver=$("$cmd" -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))')
            local major minor
            major=${ver%%.*}
            minor=${ver#*.}
            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || error "Python 3.9+ is required. Please install Python first."
log_verbose "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

# --- check platform ---

case "$(uname -s)" in
    Darwin) ;;
    *) error "cleanmac requires macOS. Detected: $(uname -s)" ;;
esac

# --- install ---

log "Installing cleanmac..."
log_verbose "  Install dir: ${INSTALL_DIR}"
log_verbose "  Python:      ${PYTHON}"

mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"

VENV_DIR="${INSTALL_DIR}/venv"

if [ -d "${VENV_DIR}" ]; then
    log_verbose "  Updating existing venv..."
else
    log_verbose "  Creating venv..."
    "${PYTHON}" -m venv "${VENV_DIR}"
fi

PIP="${VENV_DIR}/bin/pip"

log_verbose "  Installing cleanmac..."

if [ -n "${VERSION}" ]; then
    "${PIP}" install --upgrade "cleanmac==${VERSION}" >/dev/null 2>&1 || {
        # If PyPI install fails, try installing from GitHub
        log_verbose "  PyPI install failed, trying GitHub..."
        "${PIP}" install --upgrade "git+https://github.com/${REPO}.git@${VERSION}" >/dev/null 2>&1 || \
            error "Failed to install cleanmac version ${VERSION}"
    }
else
    # Try latest from PyPI first, fall back to GitHub main branch
    "${PIP}" install --upgrade cleanmac >/dev/null 2>&1 || {
        log_verbose "  PyPI not available, installing from GitHub..."
        "${PIP}" install --upgrade "git+https://github.com/${REPO}.git@${BRANCH}" >/dev/null 2>&1 || \
            error "Failed to install cleanmac"
    }
fi

# --- link binary ---

CLEANMAC_BIN="${VENV_DIR}/bin/cleanmac"

if [ ! -x "${CLEANMAC_BIN}" ]; then
    error "cleanmac binary not found after installation"
fi

ln -sf "${CLEANMAC_BIN}" "${BIN_DIR}/cleanmac"

# --- add to PATH if needed ---

case ":${PATH}:" in
    *:"${BIN_DIR}":*)
        ;;
    *)
        SHELL_RC=""
        case "${SHELL:-}" in
            */zsh)  SHELL_RC="${HOME}/.zshrc" ;;
            */bash) SHELL_RC="${HOME}/.bashrc" ;;
            */fish) SHELL_RC="${HOME}/.config/fish/config.fish" ;;
        esac
        if [ -n "${SHELL_RC}" ]; then
            if ! grep -q "${BIN_DIR}" "${SHELL_RC}" 2>/dev/null; then
                log_verbose "  Adding ${BIN_DIR} to PATH in ${SHELL_RC}"
                printf '\n# cleanmac\nexport PATH="%s:$PATH"\n' "${BIN_DIR}" >> "${SHELL_RC}"
            fi
        fi
        ;;
esac

# --- verify ---

INSTALLED_VERSION=$("${BIN_DIR}/cleanmac" --version 2>&1 || true)

log ""
log "✓ cleanmac installed successfully!"
log "  Version: ${INSTALLED_VERSION:-unknown}"
log "  Binary:  ${BIN_DIR}/cleanmac"
log "  Venv:    ${VENV_DIR}"
log ""
log "To uninstall: rm -rf ${INSTALL_DIR} ${BIN_DIR}/cleanmac"
log "To update:    cleanmac update"
log ""
log "Quick start:"
log "  cleanmac --json capabilities"
log "  cleanmac clean --profile developer --dry-run"
log ""
