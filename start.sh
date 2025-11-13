#!/bin/bash

# Charger les variables d'environnement (.env avec OPENAI_API_KEY)
source ./setup_env.sh

# Activer l'environnement virtuel Python
echo "Activating Python virtual environment..."
source ../.venv/bin/activate

# Lancer l'application Electron
echo "Launching Electron application..."
npm start
