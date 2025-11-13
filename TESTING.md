# Guide de Test - BrowserGym Electron

## 🚀 Installation & Premier Lancement

### Méthode rapide

```bash
cd /Users/simonkaperski/Documents/BrowserGym

# Setup automatique
cd browsergym-electron
./setup.sh

# OU utiliser make
make install-electron
make electron-build
```

### Installation manuelle

```bash
cd /Users/simonkaperski/Documents/BrowserGym/browsergym-electron

# 1. Installer dépendances Node.js
npm install

# 2. Installer dépendances Python
pip install websockets

# 3. Build l'interface React
npm run build
```

## 🏃 Lancer l'application

### Option 1 : Via Make (depuis la racine du projet)

```bash
cd /Users/simonkaperski/Documents/BrowserGym
make electron
```

### Option 2 : Directement

```bash
cd browsergym-electron
npm start
```

### Option 3 : Mode développement (avec auto-reload)

```bash
# Terminal 1: Serveur Python (optionnel, lancé auto par Electron)
cd browsergym-electron
python python/browsergym_server.py --debug

# Terminal 2: Electron
npm run dev
```

## ✅ Checklist de Test

### Phase 1 : Vérifications de base

- [ ] L'application Electron se lance
- [ ] La fenêtre s'affiche avec 2 panneaux (chat gauche, navigateur droite)
- [ ] Le panneau de chat affiche "Welcome to BrowserGym!"
- [ ] Le status bar en haut affiche les indicateurs
- [ ] Le BrowserView (droite) affiche une page blanche

### Phase 2 : Connexion WebSocket

- [ ] Le serveur Python démarre automatiquement
- [ ] Logs Python visibles dans le terminal Electron
- [ ] Status badge passe à "Connected" (🟢)
- [ ] Message système "Connected to BrowserGym server" apparaît

### Phase 3 : Interface Utilisateur

- [ ] Pouvoir taper dans le champ de saisie
- [ ] Le bouton "Send" (➤) est cliquable
- [ ] Enter envoie le message
- [ ] Shift+Enter crée une nouvelle ligne
- [ ] Les messages s'affichent avec timestamps
- [ ] Auto-scroll vers le bas

### Phase 4 : Communication (Test basique)

Taper dans le chat :
```
Hello, can you navigate to Google?
```

Vérifier :
- [ ] Message utilisateur apparaît (bleu, 👤)
- [ ] Réponse de l'agent apparaît (vert, 🤖)
- [ ] Status passe à "executing" puis "idle"

### Phase 5 : Reset

- [ ] Cliquer sur bouton "🔄 Reset"
- [ ] Messages sont effacés
- [ ] Environment se réinitialise
- [ ] Message "Resetting environment..." apparaît

## 🐛 Debugging

### Ouvrir les DevTools

- **macOS**: `Cmd + Option + I`
- **Windows/Linux**: `Ctrl + Shift + I`

### Vérifier les logs

**Console Electron (DevTools):**
```javascript
// Vérifier la connexion WebSocket
console.log('Test')

// Vérifier l'API Electron
window.electronAPI
```

**Terminal Python:**
```
[2025-01-12 10:30:00] INFO - Server started on ws://localhost:8765
[2025-01-12 10:30:05] INFO - Client connected: 12345
[2025-01-12 10:30:10] INFO - User message: Hello
```

### Tests manuels WebSocket

```bash
# Terminal 1: Lancer le serveur Python seul
cd browsergym-electron
python python/browsergym_server.py --debug

# Terminal 2: Tester avec wscat
npm install -g wscat
wscat -c ws://localhost:8765

# Envoyer un message de test
> {"type": "init", "config": {"headless": false}}

# Réponse attendue
< {"type": "init_complete", "data": {"ready": true}}
```

## 📝 Tests Fonctionnels

### Test 1 : Connexion basique

1. Lancer l'app : `npm start`
2. Vérifier status "Connected"
3. Logs Python : "Client connected"

**Résultat attendu :** ✅ Connexion établie

### Test 2 : Message utilisateur

1. Taper : "Go to Google"
2. Appuyer sur Enter
3. Vérifier message dans la liste

**Résultat attendu :** ✅ Message affiché

### Test 3 : Réponse agent

1. Envoyer message
2. Attendre réponse (actuellement simulée)
3. Vérifier message assistant apparaît

**Résultat attendu :** ✅ Réponse reçue

### Test 4 : Gestion d'erreur

1. Arrêter le serveur Python (Ctrl+C)
2. Essayer d'envoyer un message
3. Vérifier status "Disconnected"

**Résultat attendu :** ✅ Erreur gérée proprement

### Test 5 : Reset

1. Envoyer plusieurs messages
2. Cliquer "Reset"
3. Vérifier messages effacés

**Résultat attendu :** ✅ Environnement réinitialisé

## ⚠️ Problèmes Connus

### BrowserView vide

**État actuel :** La BrowserView affiche "about:blank"

**Pourquoi :** Playwright n'est pas encore connecté au CDP du BrowserView

**Solution :** TODO - Implémenter la connexion CDP (prochaine étape)

### Serveur Python ne démarre pas

**Erreur possible :**
```
ModuleNotFoundError: No module named 'websockets'
```

**Solution :**
```bash
pip install websockets
```

### Port déjà utilisé (8765)

**Erreur :**
```
OSError: [Errno 48] Address already in use
```

**Solution :**
```bash
# Trouver et tuer le processus
lsof -ti:8765 | xargs kill -9
```

## 🔜 Prochaines Étapes

1. **Connexion CDP** : Permettre à Playwright de contrôler le BrowserView
2. **Agent intelligent** : Intégrer l'agent BrowserGym/OpenAI
3. **Actions visibles** : Afficher les actions de l'agent en temps réel
4. **Historique** : Persister les conversations
5. **Packaging** : Créer des installateurs (.dmg, .exe, .AppImage)

## 📞 Support

En cas de problème :
1. Vérifier les logs (DevTools + Terminal)
2. Relancer avec `--debug` pour plus de logs
3. Vérifier que ports 8765 et 9222 sont libres
4. Tester le serveur Python séparément

---

**Version :** 0.1.0-alpha  
**Date :** 2025-01-12

