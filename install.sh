#!/bin/bash
set -e

REPO_URL="git@github.com:DorianBourcet/volumio-controller.git"
INSTALL_DIR="/home/volumio/volumio-controller"
SERVICE_NAME="volumio-controller"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "==> Installing pip3..."
sudo apt update -qq
sudo apt install -y python3-pip

echo "==> Cloning repository..."
git clone "$REPO_URL" "$INSTALL_DIR"

echo "==> Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

echo "==> Installing systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Volumio Controller Service
After=multi-user.target

[Service]
User=volumio
Type=simple
Restart=always
ExecStart=/usr/bin/python3 ${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "==> Done. Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager
