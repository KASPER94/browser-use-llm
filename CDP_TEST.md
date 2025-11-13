# TEST CDP Connection - Quick Guide

## Ce qu'on vient d'implémenter

1. ✅ **ElectronBrowserEnv** : Adaptateur BrowserGym pour CDP
2. ✅ **CDP activé dans Electron** : `--remote-debugging-port=9222`
3. ✅ **Serveur Python adapté** : Utilise `connect_over_cdp()`

## Test à faire

```bash
cd /Users/simonkaperski/Documents/BrowserGym/browsergym-electron
./start.sh
```

## Ce qui devrait se passer

1. ✅ Electron démarre avec CDP sur port 9222
2. ✅ Serveur Python se connecte via CDP
3. ✅ Interface s'affiche
4. ✅ Tape un message : "go to google.com"
5. ✅ La page devrait s'afficher dans le BrowserView à droite

## Vérifications

### Logs à surveiller

```
[Python] Initializing BrowserGym environment in Electron mode...
[Python] CDP URL: http://localhost:9222
[Python] Connected to Electron browser
[Python] Environment initialized successfully
```

### Si erreur de connexion CDP

**Erreur possible :** `connect ECONNREFUSED localhost:9222`

**Solution :** Le endpoint CDP pour Playwright doit être WebSocket, pas HTTP.

Vérifier avec :
```bash
curl http://localhost:9222/json/version
```

Devrait retourner le WebSocket endpoint.

## Debug

Si ça ne marche pas :

1. **Vérifier CDP actif :**
   ```bash
   curl http://localhost:9222/json/version
   ```

2. **Vérifier les logs Python** pour voir l'erreur exacte

3. **Ouvrir DevTools** (Cmd+Option+I) et regarder la console

## Prochaine étape si CDP OK

Si la connexion CDP fonctionne mais qu'il n'y a pas de navigateur visible :
- Ajouter l'agent intelligent
- Implémenter les actions de navigation

