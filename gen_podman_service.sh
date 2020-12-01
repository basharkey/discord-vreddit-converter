#!/bin/bash
if [[ $(id -u) -ne 0 ]]; then
    echo "Not running as root"
    exit
fi

podman stop vreddit
podman rm vreddit
podman build . -t discord-vreddit-converter:latest
podman run -it -d --name vreddit discord-vreddit-converter:latest

cd /tmp
podman generate systemd --restart-policy=always vreddit -f
systemctl stop vreddit
cp container-*.service /etc/systemd/system/vreddit.service
rm container-*.service
systemctl daemon-reload 
systemctl start vreddit
