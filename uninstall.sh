#!/bin/bash
set -e

INSTALL_DIR="/home/volumio/volumio-controller"
SERVICE_NAME="volumio-controller"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "==> Stopping service..."
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || echo "    (service not running)"

echo "==> Disabling service..."
sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || echo "    (service not enabled)"

echo "==> Removing systemd service file..."
if [ -f "$SERVICE_FILE" ]; then
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true
else
    echo "    (service file not found)"
fi

echo "==> Removing installation directory (including venv)..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
else
    echo "    ($INSTALL_DIR not found)"
fi

echo "==> Done. volumio-controller has been uninstalled."
