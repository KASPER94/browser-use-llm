# 🎬 QUICK START - Feature 3: Teach Me How To Do It

## 🚀 Démarrage Rapide

### 1. Démarrer l'application

```bash
cd browsergym-electron
npm start
```

### 2. Premier Test : Enregistrer un workflow

1. **Aller dans l'onglet "📹 Workflows"**
2. **Cliquer sur "🎬 New Recording"**
3. **Actions à faire** (exemple simple) :
   - Le navigateur va naviguer ou attendre vos actions
   - Exemple : Aller sur Google, chercher "BrowserGym"
4. **Cliquer sur "⏹️ Stop Recording"**
5. **Entrer un nom** : "Google Search Test"
6. **Cliquer sur "💾 Save Workflow"**

### 3. Rejouer le workflow

**Méthode 1 : Depuis l'onglet Workflows**
- Trouver la card "Google Search Test"
- Cliquer sur **▶️ Play Workflow**

**Méthode 2 : Depuis l'onglet Agent** ⭐
- Revenir à l'onglet **🤖 Agent**
- Ouvrir le dropdown sous le prompt
- Sélectionner "Google Search Test"
- Cliquer sur **▶️**

---

## 📦 Fichiers Créés

```
Backend:
✅ python/workflow_recorder.py
✅ python/workflow_storage.py
✅ python/workflow_player.py

Frontend:
✅ src/renderer/hooks/useWorkflows.ts
✅ src/renderer/components/WorkflowTab.tsx
✅ src/renderer/components/WorkflowRecorder.tsx
✅ src/renderer/components/WorkflowList.tsx
✅ src/renderer/components/WorkflowCard.tsx
✅ src/renderer/components/WorkflowDropdown.tsx

Storage:
✅ workflows/ (JSON files)
```

---

## ⚡ Features Implémentées

- ✅ Enregistrement actions (click, fill, navigation)
- ✅ Stockage JSON local
- ✅ Liste workflows avec cards
- ✅ Replay workflows
- ✅ Suppression workflows
- ✅ Dropdown dans l'onglet Agent
- ✅ UI moderne avec animations

---

## 🐛 Si problème

1. **Workflows ne se chargent pas ?**
   - Vérifier que `workflows/` existe
   - Vérifier les logs Python : `[Python]` dans la console

2. **Enregistrement ne démarre pas ?**
   - Vérifier WebSocket connecté (🟢 Server)
   - Vérifier environnement prêt

3. **Replay échoue ?**
   - Selectors peuvent changer entre sites
   - Vérifier logs Python pour erreurs

---

## 📚 Documentation Complète

- `FEATURE3_MVP_READY.md` : Documentation technique complète
- `FEATURE3_IMPLEMENTATION_PLAN.md` : Plan d'implémentation
- `TODO.md` : Liste des prochaines features
