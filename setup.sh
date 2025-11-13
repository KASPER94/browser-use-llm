#!/bin/bash

# Script de setup rapide pour BrowserGym Electron

set -e

echo "======================================"
echo "  BrowserGym Electron - Quick Setup"
echo "======================================"
echo ""

# 1. Vérifier Node.js
echo "✓ Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js >= 18"
    exit 1
fi
NODE_VERSION=$(node -v)
echo "  Found: $NODE_VERSION"
echo ""

# 2. Vérifier Python
echo "✓ Checking Python..."
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python not found. Please install Python >= 3.11"
    exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON_CMD --version)
echo "  Found: $PYTHON_VERSION"
echo ""

# 3. Installer dépendances Node.js
echo "✓ Installing Node.js dependencies..."
npm install
echo ""

# 4. Installer dépendances Python
echo "✓ Installing Python dependencies..."
$PYTHON_CMD -m pip install websockets
echo ""

# 5. Build l'interface
echo "✓ Building React interface..."
npm run build
echo ""

echo "======================================"
echo "  ✅ Setup complete!"
echo "======================================"
echo ""
echo "To start the application:"
echo "  make electron"
echo ""
echo "Or for development mode:"
echo "  make electron-dev"
echo ""

