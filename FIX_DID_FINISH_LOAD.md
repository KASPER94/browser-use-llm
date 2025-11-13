# 🐛 FIX: Script injecté trop tôt (avant chargement DOM)

## Problème

Les clics et saisies **n'étaient PAS capturés** malgré l'injection du script.

### Symptômes
- ✅ Le BrowserView s'ouvre
- ✅ Google se charge
- ✅ Log : `✅ Capture script injected into BrowserView`
- ❌ **AUCUN log `📝 [CAPTURE] Click:` ou `📝 [CAPTURE] Fill:`**

### Cause racine

Le script était injecté **immédiatement après `loadURL()`**, MAIS :
- `loadURL()` est **asynchrone** et retourne avant que la page soit chargée
- Le DOM n'est **pas encore prêt**
- Quand la page finit de charger, **le DOM est réinitialisé**, écrasant nos event listeners

```javascript
// AVANT (❌ MAUVAIS)
await interactiveBrowserView.webContents.loadURL(urlToLoad);
await interactiveBrowserView.webContents.executeJavaScript(`
  document.addEventListener('click', ...) // ❌ DOM pas encore prêt !
`);
```

---

## Solution

Utiliser l'événement **`did-finish-load`** pour attendre que le DOM soit complètement chargé avant d'injecter le script.

### Changement 1 : Injection initiale

```javascript
// APRÈS (✅ BON)
// 1. D'abord, attacher l'event listener
interactiveBrowserView.webContents.once('did-finish-load', async () => {
  console.log('📄 Page loaded, injecting capture script...');
  await interactiveBrowserView.webContents.executeJavaScript(`
    // ... script de capture ...
  `);
  console.log('✅ Capture script injected into BrowserView');
});

// 2. ENSUITE, charger l'URL
await interactiveBrowserView.webContents.loadURL(urlToLoad);
```

**Important** : Le listener doit être attaché **AVANT** `loadURL()` !

---

### Changement 2 : Ré-injection après navigation

Séparer les handlers pour plus de clarté :

```javascript
// Handler de navigation (sync URL avec hiddenWindow)
const navigationHandler = async (details) => {
  const newUrl = details.url;
  await hiddenWindow.webContents.loadURL(newUrl);
};

// Handler de ré-injection (APRÈS chargement complet)
const reInjectScript = async () => {
  console.log('📄 Page navigation complete, re-injecting capture script...');
  await interactiveBrowserView.webContents.executeJavaScript(`
    // ... script de capture ...
  `);
};

// Attacher les 3 événements
interactiveBrowserView.webContents.on('did-navigate', navigationHandler);
interactiveBrowserView.webContents.on('did-navigate-in-page', navigationHandler);
interactiveBrowserView.webContents.on('did-finish-load', reInjectScript); // ✅ NOUVEAU
```

---

## Cycle de vie Electron WebContents

```
User clicks link
       ↓
  did-navigate         ← URL change (DOM pas encore chargé)
       ↓
  will-navigate        ← Avant de commencer le chargement
       ↓
  did-start-loading    ← Début du chargement
       ↓
  dom-ready            ← DOM parsé (mais ressources pas chargées)
       ↓
  did-finish-load      ← ✅ PAGE COMPLÈTE (DOM + JS + CSS)
       ↓
  ✅ SCRIPT INJECTÉ ICI
```

---

## Fichiers modifiés

- **`main.js`** (lignes 352-486)
  - Ligne 353-403 : Injection initiale avec `once('did-finish-load')`
  - Ligne 434-482 : Fonction `reInjectScript` séparée
  - Ligne 486 : Ajout de `on('did-finish-load', reInjectScript)`
  - Ligne 543-546 : Cleanup du listener `reInjectScript`

---

## Test

```bash
npm start
```

1. Onglet **📹 Workflows** → **🎬 New Recording**
2. **Attendre les logs** :
   ```
   ✓ BrowserView loaded for recording: https://www.google.com
   📄 Page loaded, injecting capture script...
   ✅ Capture script injected into BrowserView
   ```
3. **Cliquer** sur la barre de recherche → Log attendu :
   ```
   📝 [CAPTURE] Click: textarea.gLFyf
   ```
4. **Taper** "test" → Log attendu :
   ```
   📝 [CAPTURE] Fill: textarea.gLFyf = test
   ```
5. **Naviguer** vers une autre page → Log attendu :
   ```
   📄 Page navigation complete, re-injecting capture script...
   ✅ Capture script re-injected after navigation
   ```

---

## Référence

- [Electron WebContents Events](https://www.electronjs.org/docs/latest/api/web-contents#events)
- [`did-finish-load`](https://www.electronjs.org/docs/latest/api/web-contents#event-did-finish-load): Fired when the navigation is done, i.e. the spinner of the tab has stopped spinning, and the `onload` event was dispatched.

---

**Fichier modifié** : `browsergym-electron/main.js` (lignes 352-546)

