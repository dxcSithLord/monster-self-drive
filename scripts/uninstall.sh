#!/bin/bash
# MonsterBorg Uninstall Script
# Removes systemd service and optionally the virtual environment
#
# Usage: ./scripts/uninstall.sh [--all]
#   --all: Also remove virtual environment and config

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_DIR}/venv"
CONFIG_FILE="${PROJECT_DIR}/config/config.json"
SERVICE_NAME="monsterborg"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

REMOVE_ALL=false
if [[ "$1" == "--all" ]]; then
    REMOVE_ALL=true
fi

echo "========================================"
echo " MonsterBorg Uninstaller"
echo "========================================"
echo ""

# Stop and disable service
if systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
    info "Stopping ${SERVICE_NAME} service..."
    sudo systemctl stop "${SERVICE_NAME}.service"
    success "Service stopped"
fi

if [[ -f "$SERVICE_FILE" ]]; then
    info "Removing systemd service..."
    sudo systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    success "Service removed"
else
    info "Service file not found (already removed?)"
fi

if $REMOVE_ALL; then
    # Remove virtual environment
    if [[ -d "$VENV_DIR" ]]; then
        info "Removing virtual environment..."
        rm -rf "$VENV_DIR"
        success "Virtual environment removed"
    fi

    # Backup and remove config
    if [[ -f "$CONFIG_FILE" ]]; then
        BACKUP="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        info "Backing up config to ${BACKUP}..."
        cp "$CONFIG_FILE" "$BACKUP"
        rm -f "$CONFIG_FILE"
        success "Config backed up and removed"
    fi
fi

echo ""
success "Uninstall complete"

if ! $REMOVE_ALL; then
    echo ""
    info "Virtual environment and config preserved."
    info "Run with --all to remove everything."
fi
