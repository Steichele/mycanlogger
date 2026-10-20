#!/bin/bash

# Konfiguration
sudo apt -y install sshpass
USER="$2"
HOST="$1"
PASSWORD="$3"
KEY_PATH="$HOME/.ssh/id_rsa"

# Schritt 1: Vorhandenen SchlÜssel löschen
echo "Lösche vorhandene SSH-Schlüssel..."
rm -f "$KEY_PATH" "$KEY_PATH.pub"

# Schritt 2: Neuen Schlüssel erstellen
echo "Erstelle neuen SSH-Schlüssel..."
ssh-keygen -t rsa -b 2048 -f "$KEY_PATH" -N ""

# Schritt 3: Öffentlichen Schlüssel übertragen
echo "Übertrage öffentlichen Schlüssel mit sshpass..."
sshpass -p "$PASSWORD" ssh-copy-id -i "$KEY_PATH.pub" "$USER@$HOST"

echo "? SSH-Schlüssel erfolgreich übertragen."
