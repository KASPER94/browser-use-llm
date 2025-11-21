# Fix final des 2 problèmes critiques

## 🔴 Problème 1 : Suppression ne fonctionne pas + Aucun log

### Cause racine
Le système `onPythonMessage` dans le preload ne supportait pas **plusieurs listeners** simultanés. Quand `useBrowserGym` ET `useWorkflows` appelaient tous les deux `onPythonMessage`, seul le dernier listener était actif.

De plus, `useBrowserGym` appelait `removeAllListeners()` au démontage, ce qui supprimait TOUS les listeners, y compris ceux de `useWorkflows`.

### Solution appliquée

#### 1. Preload.js - Support de multiples listeners
```javascript
// AVANT (un seul listener possible)
onPythonMessage: (callback) => {
  ipcRenderer.on('python-message', (event, data) => {
    callback(data);
  });
}

// APRÈS (multiples listeners + cleanup individuel)
onPythonMessage: (callback) => {
  const listener = (event, data) => callback(data);
  ipcRenderer.on('python-message', listener);
  
  // Retourner une fonction de nettoyage individuelle
  return () => {
    ipcRenderer.removeListener('python-message', listener);
  };
}
```

#### 2. useWorkflows.ts - Utiliser le cleanup
```typescript
useEffect(() => {
  const handlePythonMessage = (data: PythonMessage) => {
    console.log('[useWorkflows] Received message:', data.type, data);
    // ... traitement
  };

  // S'abonner et récupérer la fonction de nettoyage
  const cleanup = window.electronAPI.onPythonMessage(handlePythonMessage);
  
  // Nettoyer UNIQUEMENT ce listener au démontage
  return cleanup;
}, [refreshWorkflows]);
```

#### 3. useBrowserGym.ts - Cleanup individuel
```typescript
useEffect(() => {
  const cleanup1 = window.electronAPI.onPythonMessage(handlePythonMessage);
  const cleanup2 = window.electronAPI.onWebSocketStatus(handleWebSocketStatus);

  // Nettoyer UNIQUEMENT nos listeners (pas tous)
  return () => {
    cleanup1();
    cleanup2();
  };
}, [addMessage, addSystemMessage]);
```

### Résultat
- ✅ Les deux hooks (`useBrowserGym` + `useWorkflows`) reçoivent maintenant les messages
- ✅ Les logs `[useWorkflows]` vont maintenant apparaître
- ✅ La suppression devrait fonctionner

---

## 🔴 Problème 2 : Scroll pas capturé ni rejoué

### Constat
En analysant les workflows sauvegardés :
```bash
$ cat workflows/wf_ed885bec.json | jq '.actions | map(.type) | unique'
[
  "click",
  "fill",
  "goto"
]
```

**Aucun type `"scroll"` n'existe !**

### Causes possibles

#### 1. Le code de capture du scroll n'est peut-être pas exécuté
Le code est dans `main.js` lignes 508-525 et 698-713, mais il faut vérifier qu'il est bien injecté dans le BrowserView.

#### 2. Le debounce de 300ms est peut-être trop long
```javascript
let scrollTimeout;
document.addEventListener('scroll', (e) => {
  clearTimeout(scrollTimeout);
  scrollTimeout = setTimeout(() => {
    logAction({
      type: 'scroll',
      x: window.scrollX || window.pageXOffset || 0,
      y: window.scrollY || window.pageYOffset || 0,
      timestamp: Date.now()
    });
  }, 300); // ← Peut-être trop long ?
}, true);
```

Si l'utilisateur scroll puis clique immédiatement, le timeout n'a pas le temps de se déclencher !

### Solution recommandée

#### Option A : Réduire le debounce (Quick fix)
```javascript
// Dans main.js, lignes 509 et 699
setTimeout(() => {
  logAction({ type: 'scroll', ... });
}, 100); // ← Réduit de 300ms à 100ms
```

#### Option B : Capturer immédiatement + debounce (Mieux)
```javascript
document.addEventListener('scroll', (e) => {
  // Capturer IMMÉDIATEMENT la première position
  if (!window.__lastScrollCapture) {
    window.__lastScrollCapture = Date.now();
    logAction({
      type: 'scroll',
      x: window.scrollX || window.pageXOffset || 0,
      y: window.scrollY || window.pageYOffset || 0,
      timestamp: Date.now()
    });
  }
  
  // Ensuite debounce pour les scrolls suivants
  clearTimeout(scrollTimeout);
  scrollTimeout = setTimeout(() => {
    const now = Date.now();
    // Ne capturer que si > 100ms depuis le dernier
    if (now - window.__lastScrollCapture > 100) {
      window.__lastScrollCapture = now;
      logAction({
        type: 'scroll',
        x: window.scrollX || window.pageXOffset || 0,
        y: window.scrollY || window.pageYOffset || 0,
        timestamp: now
      });
    }
  }, 100);
}, true);
```

#### Option C : Capturer le scroll avant chaque clic (Le plus simple)
```javascript
document.addEventListener('click', (e) => {
  try {
    // NOUVEAU: Capturer la position de scroll AVANT le clic
    const scrollX = window.scrollX || window.pageXOffset || 0;
    const scrollY = window.scrollY || window.pageYOffset || 0;
    
    // Si position non-zéro, capturer le scroll
    if (scrollX > 0 || scrollY > 0) {
      logAction({
        type: 'scroll',
        x: scrollX,
        y: scrollY,
        timestamp: Date.now()
      });
      
      // Petit délai pour que le scroll soit enregistré avant le clic
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    // Puis capturer le clic
    const selector = getSelector(e.target);
    const context = getElementContext(e.target);
    logAction({
      type: 'click',
      selector: selector,
      context: context,
      timestamp: Date.now()
    });
  } catch (err) {
    console.log('[LOG] ❌ Click capture error: ' + err.message);
  }
}, true);
```

---

## 🔧 Actions à prendre

### Étape 1 : Tester la suppression (après redémarrage)
```bash
./start.sh
# Ouvrir la console (F12)
# Aller dans l'onglet Workflows
# Supprimer un workflow

# Vérifier les logs :
[useWorkflows] 🗑️ Deleting workflow: wf_xxxxx
[useWorkflows] Received message: workflow_deleted
[useWorkflows] ✅ → workflow_deleted, refreshing list...
```

Si les logs apparaissent → ✅ Suppression corrigée !

### Étape 2 : Implémenter une des options pour le scroll

**Je recommande l'Option C** (capturer scroll avant clic) car c'est :
- Le plus simple
- Le plus fiable (pas de race condition)
- Compatible avec tous les workflows

### Étape 3 : Tester le timing

Après avoir implémenté le scroll, tester le workflow complet :
```bash
# Enregistrer :
1. DuckDuckGo
2. Recherche "playmobil"
3. SCROLL pour voir les résultats
4. Clic sur le site officiel

# Rejouer

# Vérifier les logs :
[1/X] scroll
  → Scrolled to: x=0, y=300
[2/X] click
  → Clicked best match (score=150)
```

---

## 📊 Résumé des fichiers modifiés

| Fichier | Changement | Status |
|---------|-----------|--------|
| `preload.js` | Support multiples listeners | ✅ Fait |
| `useWorkflows.ts` | Cleanup individuel | ✅ Fait |
| `useBrowserGym.ts` | Cleanup individuel | ✅ Fait |
| `main.js` | Capture scroll améliorée | ⏳ À faire |

---

## 🐛 Debug si la suppression ne marche toujours pas

### 1. Vérifier que les deux hooks sont montés
```javascript
// Dans la console
console.log('useBrowserGym mounted:', !!window.electronAPI);
console.log('useWorkflows mounted:', !!window.electronAPI);
```

### 2. Compter les listeners
```javascript
// Dans main.js, après ipcRenderer.on('python-message')
console.log('Python message listeners count:', 
  ipcRenderer.listenerCount('python-message'));
// Devrait être 2 (un pour chaque hook)
```

### 3. Test manuel
```javascript
// Dans la console
window.electronAPI.sendUserMessage(JSON.stringify({
  type: 'delete_workflow',
  workflow_id: 'wf_xxxxx'
}));

// Observer les logs dans la console ET dans le terminal Python
```

---

## 🎯 Prochaines étapes

1. **Redémarrer l'app** pour que les changements de listener prennent effet
2. **Tester la suppression** avec la console ouverte
3. **Implémenter Option C** pour le scroll
4. **Réenregistrer** un workflow test avec scroll
5. **Rejouer** et vérifier que le timing est respecté

