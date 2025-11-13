# 🎬 TEST: Workflow Capture (Clics & Saisies)

## Procédure de test

### Étape 1: Lancer l'application
```bash
./start.sh
```

### Étape 2: Démarrer l'enregistrement
1. Cliquer sur l'onglet **📹 Workflows**
2. Cliquer sur **🎬 New Recording**
3. Un **BrowserView** doit s'ouvrir à droite avec Google

### Étape 3: Effectuer des actions
Dans le BrowserView (partie droite) :
1. **Cliquer** dans la barre de recherche Google
2. **Saisir** "playmobil" ou "test"
3. **Appuyer** sur Enter (ou cliquer sur "Recherche Google")
4. **Cliquer** sur un résultat de recherche
5. **Naviguer** sur la page

### Étape 4: Arrêter l'enregistrement
1. Cliquer sur **⏹️ Stop Recording**
2. Entrer un nom : "test search playmobil"
3. Cliquer sur "Save"

### Étape 5: Vérifier les logs
Dans le terminal, vous devriez voir :
```
📝 [CAPTURE] Click: textarea.gLFyf
📝 [CAPTURE] Fill: textarea.gLFyf = playmobil
✅ Retrieved 5 captured actions from BrowserView
📦 Merging 5 actions from BrowserView
✅ Total actions after merge: 7
💾 Workflow saved: wf_abc123
```

### Étape 6: Jouer le workflow
1. Le workflow "test search playmobil" doit apparaître dans la liste
2. Cliquer sur **▶️ Play**
3. Observer l'agent **rejouer** automatiquement les actions :
   - Navigation vers Google
   - Remplissage de la barre de recherche
   - Soumission du formulaire
   - Clics sur les liens

### Étape 7: Vérifier depuis l'onglet Agent
1. Retourner sur l'onglet **🤖 Agent**
2. Ouvrir le dropdown "▼ Select a workflow" en dessous du prompt
3. Sélectionner "test search playmobil"
4. Cliquer sur **▶️ Play**
5. Le workflow doit se rejouer dans le screenshot streaming

---

## Résultats attendus

✅ **Le script de capture est injecté** :
```
✅ Workflow capture script injected!
✅ Capture script injected into BrowserView
```

✅ **Les clics sont capturés** :
```
📝 [CAPTURE] Click: button.FPdoLc
📝 [CAPTURE] Click: a.clickable-link
```

✅ **Les saisies sont capturées** :
```
📝 [CAPTURE] Fill: textarea[name="q"] = playmobil
```

✅ **Les actions sont récupérées** :
```
📦 Retrieved 5 captured actions from BrowserView
```

✅ **Les actions sont fusionnées et sauvegardées** :
```
📦 Merging 5 actions from BrowserView
✅ Total actions after merge: 7
💾 Workflow saved: wf_abc123
```

✅ **Le workflow est rejoué correctement** :
```
▶️ Playing workflow: test search playmobil (7 actions)
[1/7] goto
  → Navigated to: https://www.google.com/
[2/7] fill
  → Filled: [name="q"] = playmobil
[3/7] click
  → Clicked: button.submit
✅ Workflow completed: 7 actions
```

---

## Problèmes potentiels

### ❌ Aucun clic/saisie capturé
- **Symptôme** : `Retrieved 0 captured actions`
- **Cause** : Le script n'est pas injecté ou les listeners ne sont pas attachés
- **Solution** : Vérifier les logs pour `✅ Workflow capture script injected!`

### ❌ `window.__workflowActions is undefined`
- **Cause** : Le script a été perdu lors d'une navigation
- **Solution** : Vérifier que le script est ré-injecté après navigation (logs : `✅ Capture script re-injected after navigation`)

### ❌ Les saisies ne sont pas capturées
- **Cause** : Le champ n'est pas `input` ou `textarea`
- **Solution** : Vérifier dans la console du BrowserView (DevTools) que l'événement `input` est déclenché

### ❌ Les clics ne sont pas rejoués
- **Cause** : Le selector CSS généré est trop strict ou invalide
- **Solution** : Améliorer la fonction `getSelector()` pour utiliser des sélecteurs plus robustes

---

## Tests réussis si

- [x] Le BrowserView s'ouvre au démarrage de l'enregistrement
- [x] Les clics sont capturés et loggés
- [x] Les saisies sont capturées et loggées
- [x] Les actions sont récupérées au stop
- [x] Le workflow est sauvegardé avec toutes les actions
- [x] Le workflow peut être rejoué fidèlement
- [x] Le workflow peut être lancé depuis les 2 onglets (Agent & Workflows)

---

**STATUS: PRÊT POUR TEST** ✅
