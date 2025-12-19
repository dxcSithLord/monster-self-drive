#!/bin/bash
# MonsterBorg Web Interface Installation Script
# Creates virtual environment, installs dependencies, configures service
#
# Usage: ./scripts/install.sh [--unattended]
#   --unattended: Use all defaults without prompting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_DIR}/venv"
CONFIG_FILE="${PROJECT_DIR}/config/config.json"
SERVICE_NAME="monsterborg"

# Parse arguments
UNATTENDED=false
if [[ "$1" == "--unattended" ]]; then
    UNATTENDED=true
fi

# Helper functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

prompt() {
    local var_name="$1"
    local prompt_text="$2"
    local default_value="$3"

    if $UNATTENDED; then
        eval "$var_name='$default_value'"
        return
    fi

    local input
    read -r -p "$prompt_text [$default_value]: " input
    eval "$var_name='${input:-$default_value}'"
}

prompt_yn() {
    local prompt_text="$1"
    local default="$2"

    if $UNATTENDED; then
        [[ "$default" == "y" ]] && return 0 || return 1
    fi

    local yn
    if [[ "$default" == "y" ]]; then
        read -r -p "$prompt_text [Y/n]: " yn
        [[ -z "$yn" || "$yn" =~ ^[Yy] ]]
    else
        read -r -p "$prompt_text [y/N]: " yn
        [[ "$yn" =~ ^[Yy] ]]
    fi
}

# Banner
echo "========================================"
echo " MonsterBorg Web Interface Installer"
echo "========================================"
echo ""

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -qi "raspberry" /proc/device-tree/model 2>/dev/null; then
    warn "This doesn't appear to be a Raspberry Pi"
    if ! prompt_yn "Continue anyway?" "n"; then
        exit 0
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

info "Python version: $PYTHON_VERSION"
if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 11 ]]; then
    error "Python 3.11+ required (found $PYTHON_VERSION)"
fi

# Step 1: System dependencies
echo ""
info "Step 1: Checking system dependencies"

MISSING_DEPS=()

# Check for I2C
if ! command -v i2cdetect &>/dev/null; then
    MISSING_DEPS+=("i2c-tools")
fi

# Check for python3-dev (needed for building some packages)
if [[ ! -f /usr/include/python${PYTHON_MAJOR}.${PYTHON_MINOR}/Python.h ]]; then
    MISSING_DEPS+=("python3-dev")
fi

# Check for libcap-dev (needed for python-prctl/picamera2)
if [[ ! -f /usr/include/sys/capability.h ]]; then
    MISSING_DEPS+=("libcap-dev")
fi

if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
    warn "Missing system packages: ${MISSING_DEPS[*]}"
    if prompt_yn "Install missing packages with apt?" "y"; then
        sudo apt update
        sudo apt install -y "${MISSING_DEPS[@]}"
        success "System packages installed"
    else
        warn "Skipping system packages - some features may not work"
    fi
else
    success "System dependencies satisfied"
fi

# Step 2: Enable I2C if not enabled
echo ""
info "Step 2: Checking I2C interface"

if [[ -e /dev/i2c-1 ]]; then
    success "I2C interface enabled"
else
    warn "I2C interface not detected"
    echo "Enable I2C using: sudo raspi-config -> Interface Options -> I2C"
fi

# Step 3: Create virtual environment
echo ""
info "Step 3: Setting up Python virtual environment"

# Check if already running in a virtual environment
if [[ -n "$VIRTUAL_ENV" ]]; then
    info "Already running in virtual environment: $VIRTUAL_ENV"
    VENV_DIR="$VIRTUAL_ENV"
    if prompt_yn "Use current virtual environment?" "y"; then
        success "Using active virtual environment"
    else
        warn "Please deactivate current venv and re-run install.sh"
        exit 1
    fi
else
    USE_SYSTEM_SITE_PACKAGES=false
    if prompt_yn "Include system site-packages? (recommended for picamera2)" "y"; then
        USE_SYSTEM_SITE_PACKAGES=true
    fi

    if [[ -d "$VENV_DIR" ]]; then
        if prompt_yn "Virtual environment exists at ${VENV_DIR}. Recreate it?" "n"; then
            rm -rf "$VENV_DIR"
        fi
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        info "Creating virtual environment at ${VENV_DIR}..."
        if $USE_SYSTEM_SITE_PACKAGES; then
            python3 -m venv --system-site-packages "$VENV_DIR"
        else
            python3 -m venv "$VENV_DIR"
        fi
        success "Virtual environment created"
    else
        success "Using existing virtual environment"
    fi

    # Activate venv
    source "${VENV_DIR}/bin/activate"
fi

# Step 4: Install Python dependencies
echo ""
info "Step 4: Installing Python dependencies"

# Check if Flask is already installed (quick check for existing deps)
if python3 -c "import flask" 2>/dev/null; then
    info "Some dependencies appear to be installed already"
    if prompt_yn "Reinstall/upgrade Python dependencies?" "n"; then
        pip install --upgrade pip
        pip install -r "${PROJECT_DIR}/requirements.txt"
        success "Python dependencies installed"
    else
        success "Using existing dependencies"
    fi
else
    pip install --upgrade pip
    pip install -r "${PROJECT_DIR}/requirements.txt"
    success "Python dependencies installed"
fi

# Step 5: Configuration
echo ""
info "Step 5: Configuring MonsterBorg"
echo ""

# Essential settings with prompts
prompt WEB_BIND "Web server bind address (0.0.0.0 for network access)" "0.0.0.0"
prompt WEB_PORT "Web server port" "8080"
prompt BATTERY_CELLS "Number of battery cells (typically 10 for NiMH)" "10"
prompt CAMERA_FLIPPED "Is camera mounted upside-down? (true/false)" "true"

# Calculate voltages (using Python instead of bc for portability)
VOLTAGE_IN=$(python3 -c "print(${BATTERY_CELLS} * 1.2)")
VOLTAGE_OUT=$(python3 -c "print(${VOLTAGE_IN} * 0.95)")

# Security warning
if [[ "$WEB_BIND" == "0.0.0.0" ]]; then
    warn "Server will be accessible from the network"
    warn "Ensure your network is trusted or use a firewall"
fi

# Create config directory if needed
mkdir -p "${PROJECT_DIR}/config"

# Generate config file
cat > "$CONFIG_FILE" << EOF
{
  "\$schema": "./config.schema.json",
  "security": {
    "webBindAddress": "${WEB_BIND}",
    "webPort": ${WEB_PORT}
  },
  "power": {
    "voltageIn": ${VOLTAGE_IN},
    "voltageOut": ${VOLTAGE_OUT},
    "voltageInComment": "Total battery voltage (1.2V * ${BATTERY_CELLS} cells)",
    "voltageOutComment": "Maximum motor voltage (${VOLTAGE_IN}V * 0.95 for RPi headroom)"
  },
  "camera": {
    "width": 640,
    "height": 480,
    "frameRate": 30,
    "flippedImage": ${CAMERA_FLIPPED},
    "jpegQuality": 80,
    "displayRate": 10
  },
  "processing": {
    "scaledWidth": 160,
    "scaledHeight": 120,
    "processingThreads": 4,
    "minHuntColour": [80, 0, 0],
    "maxHuntColour": [255, 100, 100],
    "erodeSize": 5,
    "targetY1Ratio": 0.9,
    "targetY2Ratio": 0.6
  },
  "control": {
    "motorSmoothing": 5,
    "positionP": 1.0,
    "positionI": 0.0,
    "positionD": 0.4,
    "changeP": 1.0,
    "changeI": 0.0,
    "changeD": 0.4,
    "clipI": 100
  },
  "drive": {
    "steeringGain": 1.0,
    "steeringClip": 1.0,
    "steeringOffset": 0.0
  },
  "debug": {
    "showFps": false,
    "testMode": false,
    "showImages": false,
    "overlayOriginal": true,
    "showPerSecond": 1,
    "scaleFinalImage": 1.0,
    "targetLineColour": [0, 255, 255],
    "targetPointsColour": [255, 255, 0],
    "targetPointSize": 3
  },
  "safety": {
    "batteryStopVoltage": 10.5,
    "batteryWarningVoltage": 11.0,
    "watchdogTimeoutSeconds": 1.0,
    "emergencyStopEnabled": true
  },
  "paths": {
    "photoDirectory": "~/monster-photos"
  },
  "websocket": {
    "enabled": true,
    "pingTimeout": 10,
    "pingInterval": 5,
    "telemetryRate": 10
  }
}
EOF

success "Configuration saved to ${CONFIG_FILE}"

# Step 6: Systemd service
echo ""
info "Step 6: Setting up systemd service"

if prompt_yn "Install systemd service for auto-start on boot?" "y"; then
    # Get the current user
    INSTALL_USER="${SUDO_USER:-$USER}"

    # Create service file
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=MonsterBorg Web Interface
After=network.target

[Service]
Type=simple
User=${INSTALL_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/monsterWebNew.py
Restart=on-failure
RestartSec=5

# Safety: stop motors on service stop
ExecStopPost=/bin/sh -c 'echo "Service stopped" | logger -t monsterborg'

# Resource limits
Nice=0
IOSchedulingClass=realtime
IOSchedulingPriority=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "${SERVICE_NAME}.service"
    success "Systemd service installed and enabled"

    if prompt_yn "Start the service now?" "y"; then
        sudo systemctl start "${SERVICE_NAME}.service"
        sleep 2
        if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
            success "Service started successfully"
        else
            warn "Service may have failed to start. Check: sudo journalctl -u ${SERVICE_NAME}"
        fi
    fi
else
    info "Skipping systemd service installation"
    echo "To run manually: source ${VENV_DIR}/bin/activate && python monsterWebNew.py"
fi

# Step 7: Summary
echo ""
echo "========================================"
echo " Installation Complete!"
echo "========================================"
echo ""
info "Configuration: ${CONFIG_FILE}"
info "Virtual env:   ${VENV_DIR}"
info "Web interface: http://$(hostname -I | awk '{print $1}'):${WEB_PORT}"
echo ""

if systemctl is-enabled --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
    info "Service commands:"
    echo "  sudo systemctl start ${SERVICE_NAME}    # Start service"
    echo "  sudo systemctl stop ${SERVICE_NAME}     # Stop service"
    echo "  sudo systemctl restart ${SERVICE_NAME}  # Restart service"
    echo "  sudo systemctl status ${SERVICE_NAME}   # Check status"
    echo "  sudo journalctl -u ${SERVICE_NAME} -f   # View logs"
fi

echo ""
success "MonsterBorg is ready!"
