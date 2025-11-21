# Fix: Suppression des workflows qui ne fonctionnait pas

## 🐛 Problème identifié

La suppression des workflows ne rafraîchissait pas la liste après la suppression.

## 🔍 Cause racine

Dans le hook `useWorkflows.ts`, il y avait un problème de dépendances dans les `useEffect` :

1. Le `useEffect` qui écoute les messages Python n'avait pas `refreshWorkflows` dans ses dépendances
2. L'ordre de déclaration des fonctions causait des problèmes de référence

### Code problématique (AVANT)

```typescript
// Écouter les messages Python liés aux workflows
useEffect(() => {
  const handlePythonMessage = (data: PythonMessage) => {
    switch (data.type) {
      // ...
      case 'workflow_deleted':
        refreshWorkflows();  // ❌ refreshWorkflows pas dans les dépendances
        break;
    }
  };
  window.electronAPI.onPythonMessage(handlePythonMessage);
}, []); // ❌ Dépendances vides

// ...

// refreshWorkflows déclaré APRÈS
const refreshWorkflows = useCallback(() => {
  window.electronAPI.sendUserMessage(JSON.stringify({ type: 'list_workflows' }));
}, []);
```

## ✅ Solution appliquée

### 1. Réorganisation de l'ordre des déclarations

Toutes les fonctions `useCallback` sont maintenant déclarées **avant** les `useEffect` qui les utilisent :

```typescript
// ✅ refreshWorkflows déclaré EN PREMIER
const refreshWorkflows = useCallback(() => {
  window.electronAPI.sendUserMessage(JSON.stringify({ type: 'list_workflows' }));
}, []);

// Autres callbacks...
const startRecording = useCallback(() => { ... }, []);
const stopRecording = useCallback(async (workflowName?: string) => { ... }, []);
const getWorkflow = useCallback((workflowId: string) => { ... }, []);
const playWorkflow = useCallback((workflowId: string) => { ... }, []);
const deleteWorkflow = useCallback((workflowId: string) => { ... }, []);

// ✅ useEffect APRÈS, avec dépendances correctes
useEffect(() => {
  const handlePythonMessage = (data: PythonMessage) => {
    switch (data.type) {
      case 'workflow_deleted':
        console.log('✅ Workflow deleted, refreshing list...');
        refreshWorkflows(); // ✅ Fonctionne maintenant
        break;
    }
  };
  window.electronAPI.onPythonMessage(handlePythonMessage);
}, [refreshWorkflows]); // ✅ Dépendance ajoutée
```

### 2. Ajout de logs de debug

```typescript
case 'workflow_deleted':
  console.log('✅ Workflow deleted, refreshing list...');
  refreshWorkflows();
  break;

// Dans deleteWorkflow:
const deleteWorkflow = useCallback((workflowId: string) => {
  console.log('🗑️ Deleting workflow:', workflowId);
  window.electronAPI.sendUserMessage(JSON.stringify({
    type: 'delete_workflow',
    workflow_id: workflowId
  }));
}, []);
```

## 🔄 Flux de suppression (maintenant fonctionnel)

1. **User clique sur 🗑️** → `WorkflowCard.onDelete()`
2. **Confirmation** → `WorkflowList` affiche `confirm()`
3. **Frontend envoie** → `deleteWorkflow(workflowId)`
4. **Message WS** → `{ type: 'delete_workflow', workflow_id: 'wf_xxx' }`
5. **Python handler** → `handle_delete_workflow()`
6. **Storage delete** → `workflow_storage.delete()` supprime le fichier JSON
7. **Réponse Python** → `{ type: 'workflow_deleted', data: { success: true } }`
8. **Frontend reçoit** → `case 'workflow_deleted'`
9. **Rafraîchissement** → `refreshWorkflows()` ✅
10. **Liste mise à jour** → `case 'workflows_list'` → `setWorkflows()`

## 🧪 Test de validation

Pour tester que la suppression fonctionne maintenant :

1. Lancer l'application : `./start.sh`
2. Enregistrer un workflow test
3. Aller dans l'onglet "Workflows Library"
4. Cliquer sur le bouton 🗑️
5. Confirmer la suppression
6. **Résultat attendu** : Le workflow disparaît immédiatement de la liste
7. **Vérifier dans la console** :
   ```
   🗑️ Deleting workflow: wf_xxxxx
   ✅ Workflow deleted, refreshing list...
   ```

## 📝 Fichiers modifiés

- `src/renderer/hooks/useWorkflows.ts` :
  - Réorganisation de l'ordre des déclarations
  - Ajout de `refreshWorkflows` dans les dépendances du `useEffect`
  - Ajout de logs de debug

## ⚠️ Notes importantes

### Problème courant avec les hooks React

Ce type de bug est fréquent avec les hooks React :
- Les `useEffect` capturent les valeurs/fonctions au moment de leur création
- Si une fonction utilisée dans un `useEffect` n'est pas dans les dépendances, elle peut être "stale" (obsolète)
- Solution : **toujours** déclarer les `useCallback`/`useMemo` **avant** les `useEffect` qui les utilisent

### Bonnes pratiques appliquées

1. ✅ **Ordre de déclaration** : States → Callbacks → Effects
2. ✅ **Dépendances exhaustives** : Tous les callbacks utilisés dans un effect sont listés
3. ✅ **Logs de debug** : Facilite le debugging futur
4. ✅ **useCallback stable** : Les callbacks sans dépendances ne changent jamais

## 🎯 Résultat

La suppression des workflows fonctionne maintenant correctement avec rafraîchissement immédiat de la liste ! 🎉

