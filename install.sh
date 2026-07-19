#!/bin/bash
set -euo pipefail

REPO_URL="git@github.com:DorianBourcet/volumio-controller.git"
INSTALL_DIR="/home/volumio/volumio-controller"
VENV_DIR="${INSTALL_DIR}/venv"
SERVICE_NAME="volumio-controller"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ ! -e /dev/i2c-1 ]; then
  echo "WARNING: /dev/i2c-1 not found - I2C bus may not be enabled."
  echo "         Run 'sudo raspi-config' → Interface Options → I2C → Enable."
fi

echo "==> Installing python3-full..."
sudo apt update -qq
sudo apt install -y python3-full

echo "==> Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
  echo "    target $INSTALL_DIR already exists, pulling instead"
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "==> Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "==> Installing Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "==> Installing systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Volumio Controller Service
After=multi-user.target

[Service]
User=volumio
Type=simple
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
TimeoutStartSec=30
Environment=VC_LOG_LEVEL=INFO
WorkingDirectory=${INSTALL_DIR}
ExecStart=${VENV_DIR}/bin/python3 __main__.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "==> Done. Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager
