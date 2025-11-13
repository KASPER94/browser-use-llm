#!/bin/bash
# setup_env.sh - Configure l'environnement avec la clé OpenAI

# Chercher le fichier .env
ENV_FILE="../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Fichier .env non trouvé à la racine de BrowserGym"
    echo ""
    echo "Créez un fichier .env avec :"
    echo "OPENAI_API_KEY=sk-proj-..."
    exit 1
fi

# Sourcer le .env
echo "📂 Loading environment from .env..."
set -a
source "$ENV_FILE"
set +a

# Vérifier que la clé est bien chargée
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in .env"
    exit 1
fi

echo "✅ OPENAI_API_KEY loaded successfully"
echo ""

