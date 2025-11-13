# BrowserGym Electron

Interface Electron unifiée pour BrowserGym - Une seule fenêtre avec le chat à gauche et le navigateur contrôlé à droite.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           FENÊTRE ELECTRON UNIQUE                │
├──────────────────┬──────────────────────────────┤
│   PANNEAU GAUCHE │      PANNEAU DROIT           │
│   (35%)          │      (65%)                   │
│                  │                               │
│   Chat React     │   BrowserView                │
│   - Messages     │   (Chromium intégré)         │
│   - Input        │                               │
│   - Status       │   Contrôlé par               │
│                  │   Playwright via CDP         │
└──────────────────┴──────────────────────────────┘
         ↕                       ↕
    IPC/WebSocket           CDP Connection
         ↕                       ↕
┌────────────────────────────────────────────────┐
│      PROCESSUS PRINCIPAL ELECTRON (Node.js)     │
│                      ↕                          │
│      SERVEUR WEBSOCKET PYTHON                   │
│      (BrowserGym + Playwright)                  │
└────────────────────────────────────────────────┘
```

## 📦 Installation

### Prérequis

- Node.js >= 18
- Python >= 3.11
- BrowserGym installé (`../browsergym/`)

### Setup

```bash
# 1. Installer les dépendances Node.js
cd browsergym-electron
npm install

# 2. Installer les dépendances Python
pip install websockets
# OU utiliser l'environnement virtuel BrowserGym existant

# 3. Build l'interface React
npm run build
```

## 🚀 Lancer l'application

```bash
# Option 1: Tout en un (recommandé)
npm start

# Option 2: Développement avec hot-reload
npm run dev
```

L'application va :
1. Compiler l'interface React
2. Lancer le serveur Python WebSocket
3. Ouvrir la fenêtre Electron

## 🛠️ Développement

### Structure du projet

```
browsergym-electron/
├── main.js                 # Processus principal Electron
├── preload.js              # Script de préchargement (sécurité)
├── package.json
├── webpack.config.js
├── tsconfig.json
├── src/
│   └── renderer/           # Code React (UI)
│       ├── index.tsx
│       ├── App.tsx
│       ├── types.ts
│       ├── components/
│       │   ├── ChatPanel.tsx
│       │   ├── MessageList.tsx
│       │   ├── InputBox.tsx
│       │   └── StatusBar.tsx
│       ├── hooks/
│       │   └── useBrowserGym.ts
│       └── styles/
│           └── index.css
├── python/
│   ├── browsergym_server.py    # Serveur WebSocket
│   └── requirements.txt
└── dist/                   # Build output
```

### Mode développement

Le serveur Python doit être lancé séparément en mode dev :

```bash
# Terminal 1: Serveur Python
python python/browsergym_server.py --debug

# Terminal 2: Electron avec hot-reload
npm run dev
```

## 🔧 Configuration

### Variables d'environnement

- `PYTHON_PATH`: Chemin vers l'interpréteur Python (défaut: `python`)
- `NODE_ENV`: `development` ou `production`

### Ports

- WebSocket Python: `8765`
- CDP (Chrome DevTools Protocol): `9222`

## 📝 TODO / Roadmap

- [x] Structure projet Electron
- [x] Interface React (ChatPanel + composants)
- [x] Serveur WebSocket Python
- [x] Communication Electron ↔ Python
- [ ] **Adapter BrowserGym pour mode CDP** (en cours)
- [ ] Connexion Playwright au BrowserView Electron
- [ ] Intégration agent demo
- [ ] Tests d'intégration
- [ ] Packaging pour distribution (macOS/Windows/Linux)

## ⚠️ État actuel

**Version**: 0.1.0-alpha  
**Statut**: En développement actif

### Ce qui fonctionne
- ✅ Interface Electron avec BrowserView
- ✅ UI React pour le chat
- ✅ Communication WebSocket basique
- ✅ Serveur Python fonctionnel

### Ce qui reste à faire
- ⏳ Connexion Playwright → Electron BrowserView via CDP
- ⏳ Adaptation de BrowserGym pour mode Electron
- ⏳ Intégration de l'agent intelligent

## 🐛 Debugging

### Problèmes courants

**Le serveur Python ne démarre pas:**
```bash
# Vérifier que BrowserGym est installé
python -c "import browsergym.core; print('OK')"

# Vérifier websockets
pip install websockets
```

**La BrowserView est vide:**
- C'est normal, elle attend la connexion CDP de Playwright
- Vérifier les logs dans DevTools (Cmd+Option+I)

**WebSocket ne se connecte pas:**
```bash
# Tester manuellement le serveur Python
python python/browsergym_server.py --debug
# Dans un autre terminal:
wscat -c ws://localhost:8765
```

### Logs

- Electron: Console DevTools (Cmd/Ctrl+Shift+I)
- Python: Terminal où `browsergym_server.py` tourne
- WebSocket: Messages dans les deux consoles

## 📚 Ressources

- [Electron Documentation](https://www.electronjs.org/docs)
- [BrowserGym](https://github.com/ServiceNow/BrowserGym)
- [Playwright CDP](https://playwright.dev/docs/api/class-cdpsession)

## 📄 Licence

Apache-2.0 (même licence que BrowserGym)

