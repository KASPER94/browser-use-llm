# 🐛 FIX: Workflow Recorder ne capturait pas les clics et saisies

## Problème

Lorsque l'utilisateur enregistrait un workflow, **seules les navigations** étaient capturées :
- ❌ Aucun clic détecté
- ❌ Aucune saisie détectée
- ❌ Aucune interaction utilisateur enregistrée

### Cause racine

Le script de capture (`WorkflowRecorder`) était injecté dans la page **Playwright** (`hiddenWindow`), mais l'utilisateur interagissait dans le **BrowserView** (`interactiveBrowserView`). Ces deux fenêtres sont complètement distinctes !

```
┌─────────────────────────────────────┐
│   Fenêtre Electron Principale       │
├─────────────────┬───────────────────┤
│  React UI       │  BrowserView      │ ← L'utilisateur clique ICI
│  (Chat)         │  (interactif)     │
└─────────────────┴───────────────────┘

┌─────────────────────────────────────┐
│   hiddenWindow (offscreen)          │ ← WorkflowRecorder écoutait ICI
│   Contrôlé par Playwright           │
└─────────────────────────────────────┘
```

---

## Solution

**Injecter le script de capture directement dans le BrowserView** et récupérer les actions capturées au moment de `stop_recording`.

### Architecture de la solution

```
BrowserView (User)  ──┐
                      │ 1. User clicks/types
                      ▼
           window.__workflowActions[] (capture DOM events)
                      │
                      │ 2. Stop recording
                      ▼
         Electron IPC: get-captured-actions
                      │
                      │ 3. Retrieve actions
                      ▼
         React: useWorkflows.stopRecording()
                      │
                      │ 4. Send to Python
                      ▼
         WebSocket: { type: 'stop_recording', captured_actions: [...] }
                      │
                      │ 5. Merge & save
                      ▼
    WorkflowStorage.save(workflow)
```

---

## Changements effectués

### 1. **Electron Main (`main.js`)**

#### A. Injection du script de capture au démarrage
```javascript
// Ligne 365-407
await interactiveBrowserView.webContents.executeJavaScript(`
  window.__workflowActions = [];
  
  // Capturer les CLICS
  document.addEventListener('click', (e) => {
    const selector = getSelector(e.target);
    window.__workflowActions.push({
      type: 'click',
      selector: selector,
      text: e.target.innerText?.substring(0, 50) || '',
      timestamp: Date.now()
    });
    console.log('📝 [CAPTURE] Click:', selector);
  }, true);
  
  // Capturer les SAISIES
  document.addEventListener('input', (e) => {
    if (e.target.matches('input, textarea')) {
      const selector = getSelector(e.target);
      window.__workflowActions.push({
        type: 'fill',
        selector: selector,
        value: e.target.value,
        timestamp: Date.now()
      });
      console.log('📝 [CAPTURE] Fill:', selector);
    }
  }, true);
`);
```

#### B. Ré-injection après chaque navigation
```javascript
// Ligne 425-470
const navigationHandler = async (details) => {
  // ... sync hiddenWindow ...
  
  // Ré-injecter le script après navigation
  await interactiveBrowserView.webContents.executeJavaScript(`
    // ... même script de capture ...
  `);
};
```

#### C. Nouveau handler IPC pour récupérer les actions
```javascript
// Ligne 492-509
ipcMain.handle('get-captured-actions', async (event) => {
  const actions = await interactiveBrowserView.webContents.executeJavaScript(
    'window.__workflowActions || []'
  );
  console.log(`✅ Retrieved ${actions.length} captured actions`);
  return { success: true, actions };
});
```

---

### 2. **Preload (`preload.js`)**

```javascript
// Ligne 63
getCapturedActions: () => ipcRenderer.invoke('get-captured-actions'),
```

---

### 3. **Frontend React (`useWorkflows.ts`)**

```typescript
// Ligne 74-97
const stopRecording = useCallback(async (workflowName?: string) => {
  // Récupérer les actions capturées depuis le BrowserView
  const result = await window.electronAPI.getCapturedActions();
  const capturedActions = result.success ? result.actions : [];
  
  console.log(`📦 Retrieved ${capturedActions.length} captured actions`);
  
  // Envoyer stop_recording avec les actions capturées
  window.electronAPI.sendUserMessage(JSON.stringify({
    type: 'stop_recording',
    workflow_name: workflowName || `Workflow ${Date.now()}`,
    captured_actions: capturedActions
  }));
}, []);
```

---

### 4. **Backend Python (`browsergym_server.py`)**

#### A. Handler `stop_recording` accepte `captured_actions`
```python
# Ligne 583-630
async def handle_stop_recording(
    self, 
    workflow_name: str = None, 
    captured_actions: List[Dict] = None  # NOUVEAU
) -> Dict[str, Any]:
    workflow = await self.workflow_recorder.stop_recording()
    
    # Fusionner les actions capturées depuis le BrowserView
    if captured_actions:
        logger.info(f"📦 Merging {len(captured_actions)} actions from BrowserView")
        all_actions = workflow.get('actions', []) + captured_actions
        all_actions.sort(key=lambda x: x.get('timestamp', 0))
        workflow['actions'] = all_actions
    
    # Sauvegarder
    workflow_id = self.workflow_storage.save(workflow)
    return {'type': 'recording_stopped', ...}
```

#### B. Router les `captured_actions`
```python
# Ligne 758-761
elif msg_type == 'stop_recording':
    workflow_name = data.get('workflow_name')
    captured_actions = data.get('captured_actions', [])  # NOUVEAU
    response = await self.handle_stop_recording(workflow_name, captured_actions)
```

---

### 5. **Types TypeScript (`types.ts`)**

```typescript
// Ligne 64
getCapturedActions: () => Promise<{ success: boolean; actions: any[]; error?: string }>;
```

---

## Test

```bash
npm start
```

1. Onglet **📹 Workflows**
2. Cliquer **🎬 New Recording**
3. Dans le BrowserView (droite) :
   - Cliquer sur un lien
   - Saisir du texte dans un champ
   - Naviguer vers une autre page
4. Cliquer **⏹️ Stop Recording**
5. Entrer un nom (ex: "find a toy")
6. Vérifier les logs :

```
📝 [CAPTURE] Click: textarea.gLFyf
📝 [CAPTURE] Fill: textarea.gLFyf = playmobil
✅ Retrieved 5 captured actions from BrowserView
📦 Merging 5 actions from BrowserView
✅ Total actions after merge: 7
💾 Workflow saved: wf_abc123
```

7. Jouer le workflow depuis la liste
8. Vérifier que les clics et saisies sont bien **rejoués** !

---

## Fichiers modifiés

1. `main.js` (lignes 365-509)
2. `preload.js` (ligne 63)
3. `src/renderer/hooks/useWorkflows.ts` (lignes 74-97)
4. `python/browsergym_server.py` (lignes 583-630, 758-761)
5. `src/renderer/types.ts` (ligne 64)

---

## Résultat attendu

✅ **Tous les événements utilisateur sont maintenant capturés** :
- Clics sur boutons/liens
- Saisies dans champs texte/textarea
- Navigations
- Soumissions de formulaires (via Enter après fill)

✅ **Les workflows peuvent être rejoués fidèlement** !

