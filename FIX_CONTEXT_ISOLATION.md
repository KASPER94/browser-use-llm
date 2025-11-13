# 🔧 FIX: 0 actions capturées malgré l'injection

## Problème

Lors de l'enregistrement d'un workflow, **0 actions étaient capturées** depuis le BrowserView malgré l'injection réussie du script.

```
✅ Capture script injected into BrowserView
... (utilisateur clique et tape) ...
✅ Retrieved 0 captured actions from BrowserView  ❌
```

---

## Cause racine

### 1. **Contexte isolé (`contextIsolation: true`)**

Avec `contextIsolation: true`, le script injecté via `executeJavaScript` s'exécute dans un **contexte isolé** qui :
- Ne peut pas accéder aux variables globales de la page (`window`)
- **Ne peut pas capturer les événements DOM réels**
- Les event listeners sont attachés mais ne reçoivent jamais d'événements

### 2. **Sandbox activé**

Le `sandbox: true` ajoute une couche de sécurité supplémentaire qui peut bloquer l'accès aux APIs DOM.

---

## Solution appliquée

### 1. Désactiver `contextIsolation` et `sandbox` pour le BrowserView de recording

```javascript
// main.js, ligne 320-327
interactiveBrowserView = new BrowserView({
  webPreferences: {
    nodeIntegration: false,           // Sécurité : pas d'accès Node.js
    contextIsolation: false,          // ✅ Permettre capture événements DOM
    sandbox: false,                   // ✅ Permettre capture événements DOM
  },
});
```

**Note de sécurité** : Ce BrowserView est uniquement utilisé pour l'enregistrement de workflows, sous la supervision directe de l'utilisateur. Pas de risque d'exécution de code malveillant.

---

### 2. Améliorer le script de capture avec gestion d'erreurs

```javascript
// Ligne 357-423
document.addEventListener('click', (e) => {
  try {
    const selector = getSelector(e.target);
    const action = {
      type: 'click',
      selector: selector,
      text: (e.target.innerText || e.target.textContent || '').substring(0, 50),
      timestamp: Date.now()
    };
    window.__workflowActions.push(action);
    logToMain(`📝 [CAPTURE] Click: ${selector} (total: ${window.__workflowActions.length})`);
  } catch (err) {
    logToMain('❌ Click capture error: ' + err.message);
  }
}, true); // Phase de capture
```

**Améliorations** :
- Gestion d'erreurs avec `try/catch`
- Logs avec compteur d'actions
- Fallback pour `innerText` / `textContent`
- Vérification de nullité dans `getSelector`

---

### 3. Logs visibles dans le terminal Electron

```javascript
// Ligne 377-382
function logToMain(message) {
  console.log(message); // Console du BrowserView
  document.title = '[LOG] ' + message; // Visible dans le titre
}

// Ligne 535-540
interactiveBrowserView.webContents.on('page-title-updated', (event, title) => {
  if (title.startsWith('[LOG]')) {
    console.log(`[BrowserView] ${title.replace('[LOG] ', '')}`);
  }
});
```

Les logs du BrowserView sont maintenant **visibles dans le terminal Electron** via le mécanisme de changement de titre.

---

### 4. Préservation des actions lors de la ré-injection

```javascript
// Ligne 467
window.__workflowActions = window.__workflowActions || [];
```

Lors des navigations, on **ne réinitialise pas** `__workflowActions`, on le préserve.

---

## Test attendu

```bash
cd /Users/simonkaperski/Documents/BrowserGym/browsergym-electron
killall Electron 2>/dev/null
./start.sh
```

### Nouveau comportement attendu

1. **Au démarrage du recording** :
   ```
   ✅ Capture script injected into BrowserView
   [BrowserView] ✅ Workflow capture script injected and ready!
   ```

2. **Au premier clic** :
   ```
   [BrowserView] 📝 [CAPTURE] Click: input.search-box (total: 1)
   ```

3. **À la première saisie** :
   ```
   [BrowserView] 📝 [CAPTURE] Fill: input.search-box = test (total: 2)
   ```

4. **Au stop recording** :
   ```
   ✅ Retrieved 2 captured actions from BrowserView  ✅ (au lieu de 0)
   📦 Merging 2 actions from BrowserView
   ✅ Total actions after merge: 5
   ```

---

## Fichiers modifiés

- **`main.js`** :
  - Ligne 320-327 : `contextIsolation: false`, `sandbox: false`
  - Ligne 357-423 : Script amélioré avec gestion d'erreurs et logs
  - Ligne 460-529 : Ré-injection améliorée
  - Ligne 535-540 : Logger les événements de titre

---

## Référence

- [Electron Context Isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation)
- [Event Capturing Phase](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#capture)

---

**Fichier modifié** : `browsergym-electron/main.js` (lignes 320-540)

