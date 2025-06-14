#!/bin/bash
set -e  # Stop on error

# Mise à jour des outils de base
python -m pip install --upgrade pip setuptools wheel

# Installation des dépendances système requises
sudo apt-get update && sudo apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz-dev \
    libffi-dev

# Installation des dépendances Python
pip install -r requirements.txt