# 🎬 FEATURE 3 : "TEACH ME HOW TO DO IT" - MACRO RECORDING

**Date:** 13 Novembre 2025  
**Status:** 📋 Spécifiée et prête pour implémentation  
**Priorité:** 🎯 Haute (après VLM Integration)

---

## 🎯 CONCEPT

**"Montre-moi comment faire, et je le ferai pour toi"**

Cette feature transforme BrowserGym en un **système d'apprentissage par démonstration**. L'utilisateur enregistre un parcours web complet (workflow), et l'agent peut ensuite **rejouer ce parcours automatiquement** quand on le lui demande.

---

## 🚀 VALEUR AJOUTÉE

### **Pour l'utilisateur**
- ✅ **Zero-code automation** : Créer des automatisations sans écrire de code
- ✅ **Réutilisabilité** : Enregistrer une fois, rejouer à l'infini
- ✅ **Partage de knowledge** : Exporter/importer des workflows
- ✅ **Gains de temps massifs** : Automatiser les tâches répétitives

### **Pour l'agent**
- ✅ **Précision accrue** : Workflows testés par des humains
- ✅ **Moins d'erreurs** : Pas besoin de deviner les actions
- ✅ **Apprentissage continu** : Bibliothèque de workflows qui s'enrichit
- ✅ **Fallback intelligent** : Si l'agent échoue, il peut chercher un workflow similaire

---

## 💡 USE CASES PRIORITAIRES

### **1. Authentification (🔥 High Priority)**
**Problème actuel :** L'agent ne peut pas gérer les authentifications complexes (OAuth, 2FA, CAPTCHA)

**Solution avec Macro Recording :**
```
User enregistre: "Login GitHub avec OAuth"
  1. Clic sur "Sign in with GitHub"
  2. Redirection vers GitHub
  3. Enter username ${USERNAME}
  4. Enter password ${PASSWORD}
  5. Click "Authorize app"
  6. Redirection retour
  
Agent peut rejouer ce workflow à la demande avec credentials fournis.
```

### **2. Workflows Métier**
**Exemples :**
- Export mensuel de données (comptabilité, analytics)
- Génération de rapports automatisés
- Veille concurrentielle (monitoring prix)
- Backup de données

### **3. E-commerce**
**Exemples :**
- Ajout au panier multi-sites
- Comparaison de prix automatisée
- Suivi de disponibilité produit
- Checkout automatique (drop shipping)

### **4. Formulaires Complexes**
**Exemples :**
- Déclarations administratives
- Inscriptions événements
- Candidatures (jobs, écoles)
- Enquêtes/questionnaires répétitifs

### **5. Tests Automatisés**
**Exemples :**
- Suites E2E sans Selenium
- Tests de régression visuels
- Validation de parcours utilisateur
- Performance monitoring

---

## 🏗️ ARCHITECTURE TECHNIQUE

### **Frontend : 3 Composants Principaux**

```
┌─────────────────────────────────────────┐
│        WORKFLOW TAB (Nouvel onglet)     │
├─────────────────────────────────────────┤
│                                         │
│  [1] WorkflowLibrary.tsx                │
│      - Grid de workflows enregistrés   │
│      - Search & filter                  │
│      - Play / Edit / Delete buttons    │
│                                         │
│  [2] WorkflowRecorder.tsx               │
│      - BrowserView pleine largeur      │
│      - Controls overlay: 🔴 ⏸️ ⏹️     │
│      - Action list (temps réel)        │
│                                         │
│  [3] WorkflowPlayer.tsx                 │
│      - Variable input form             │
│      - Progress indicator              │
│      - Error handling UI                │
│                                         │
└─────────────────────────────────────────┘
```

### **Backend : 3 Services Python**

```python
┌─────────────────────────────────────────┐
│         Python Backend Services          │
├─────────────────────────────────────────┤
│                                         │
│  [1] WorkflowRecorder                   │
│      - Capture Playwright events       │
│      - Inject DOM event listeners      │
│      - Take VLM screenshots            │
│      - Generate workflow JSON          │
│                                         │
│  [2] WorkflowPlayer                     │
│      - Parse workflow JSON             │
│      - Execute actions sequentially    │
│      - Handle variables replacement    │
│      - VLM validation                  │
│                                         │
│  [3] WorkflowStorage                    │
│      - Save/load workflows (JSON)      │
│      - Search & indexing               │
│      - Import/export                   │
│                                         │
└─────────────────────────────────────────┘
```

### **Format Workflow (JSON)**

```json
{
  "workflow_id": "wf_github_login_001",
  "name": "Login GitHub",
  "description": "Authenticate with GitHub OAuth",
  "tags": ["authentication", "github", "oauth"],
  "created_at": "2025-11-13T12:30:00Z",
  
  "actions": [
    {
      "type": "goto",
      "url": "https://github.com/login",
      "timestamp": 0
    },
    {
      "type": "click",
      "selector": "button.btn-primary",
      "description": "Click 'Sign in' button",
      "timestamp": 1500,
      "screenshot_before": "base64..."
    },
    {
      "type": "fill",
      "selector": "input[name='login']",
      "value": "${USERNAME}",
      "is_sensitive": false,
      "timestamp": 3000
    },
    {
      "type": "fill",
      "selector": "input[name='password']",
      "value": "${PASSWORD}",
      "is_sensitive": true,
      "timestamp": 5000
    }
  ],
  
  "variables": [
    {"name": "USERNAME", "type": "string", "required": true},
    {"name": "PASSWORD", "type": "password", "required": true}
  ],
  
  "success_criteria": {
    "final_url_pattern": "https://github.com/*",
    "expected_element": "avatar.CircleBadge",
    "vlm_validation": "Check if user avatar visible"
  }
}
```

---

## 🔧 DÉFIS TECHNIQUES & SOLUTIONS

### **1. Sélecteurs Fragiles**
**❌ Problème :** Sites modernes → DOM change fréquemment

**✅ Solutions :**
- Enregistrer **3 selectors par élément** :
  ```json
  "selectors": {
    "primary": "#login-button",
    "fallback1": "button[type='submit']",
    "fallback2": "text=Sign In"
  }
  ```
- Utiliser **Playwright smart locators** (`getByRole`, `getByText`)
- **VLM Fallback** : "Click the blue button that says 'Login'"

### **2. Données Sensibles**
**❌ Problème :** Passwords/tokens enregistrés en clair

**✅ Solutions :**
- Auto-détection `input[type="password"]`
- Remplacement par variables `${PASSWORD}`
- **Jamais stocker** les valeurs sensibles
- Masquer dans logs : `fill(selector, ***)` au lieu de `fill(selector, password123)`

### **3. Timing & Async**
**❌ Problème :** Contenus chargés de manière asynchrone

**✅ Solutions :**
- Enregistrer `wait_for_selector`, `wait_for_navigation`
- Utiliser **Playwright auto-wait** (built-in)
- VLM check : "Is page fully loaded?"

### **4. Variations de Contenu**
**❌ Problème :** Prix, dates, noms changent

**✅ Solutions :**
- Regex patterns : `price: /\$[\d,]+\.\d{2}/`
- VLM extraction : "Extract the price from screenshot"
- Variables d'environnement

---

## 📅 ROADMAP D'IMPLÉMENTATION

### **Phase 1 : MVP (2-3 semaines)** 🟢
**Objectif :** Workflow recorder + player fonctionnel

- [ ] UI onglet Workflows (React)
- [ ] Recorder basique (Playwright events)
- [ ] Storage JSON local
- [ ] Player simple (rejouer actions)
- [ ] 3 workflows de test (login, search, form)

**Livrable :** Demo enregistrement + replay d'un login GitHub

---

### **Phase 2 : Robustesse (2-3 semaines)** 🟡
**Objectif :** Production-ready avec gestion d'erreurs

- [ ] Multi-selector fallback
- [ ] Variables & paramètres
- [ ] VLM validation basique
- [ ] Edit mode (modifier workflows)
- [ ] Import/export workflows

**Livrable :** Bibliothèque de 10 workflows utiles

---

### **Phase 3 : Intelligence (3-4 semaines)** 🟠
**Objectif :** Agent intelligent avec workflows

- [ ] VLM extraction de données
- [ ] Recherche sémantique (embeddings)
- [ ] Auto-suggestions workflows
- [ ] Workflows conditionnels (if/else)
- [ ] Loops & iterations

**Livrable :** Agent qui suggère workflows pertinents

---

### **Phase 4 : Advanced (4+ semaines)** 🔴
**Objectif :** Plateforme collaborative

- [ ] Workflow marketplace (partage communauté)
- [ ] Analytics (success rate, temps d'exécution)
- [ ] A/B testing workflows
- [ ] Parallel execution
- [ ] CI/CD integration

**Livrable :** Marketplace avec 50+ workflows partagés

---

## 🎨 UI/UX DESIGN

### **1. Workflow Library**
```
┌───────────────────────────────────────────┐
│  🔍 Search workflows...      [+ New]      │
├───────────────────────────────────────────┤
│                                           │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ 🔐 Login GH │  │ 🛒 Buy Item │       │
│  │ 5 actions   │  │ 12 actions  │       │
│  │ Last: 2d ago│  │ Last: 1w ago│       │
│  │ ▶️ Play  ✏️ │  │ ▶️ Play  ✏️ │       │
│  └─────────────┘  └─────────────┘       │
│                                           │
│  Tags: [Auth] [E-commerce] [Forms]       │
└───────────────────────────────────────────┘
```

### **2. Recording Mode**
```
┌───────────────────────────────────────────┐
│  🔴 REC  ⏸️ Pause  ⏹️ Stop & Save  🗑️   │
├───────────────────────────────────────────┤
│                                           │
│     [BrowserView - Interactive]          │
│                                           │
├───────────────────────────────────────────┤
│  📝 Actions: 7                           │
│  1. 0.0s  goto(github.com)               │
│  2. 1.5s  click('Sign in')               │
│  3. 3.0s  fill('[name=login]', 'usr')   │
│  4. 5.0s  fill('[name=pass]', ***)      │
│  5. 7.0s  click('Submit')                │
│  6. 9.0s  wait_for_navigation            │
│  7. 10.0s verified: User logged in       │
└───────────────────────────────────────────┘
```

### **3. Replay Mode**
```
┌───────────────────────────────────────────┐
│  ▶️ Replaying: "Login GitHub"            │
├───────────────────────────────────────────┤
│                                           │
│  Variables Required:                      │
│  USERNAME: [input________]                │
│  PASSWORD: [●●●●●●●●●●●●]                │
│                                           │
│  [▶️ Start Replay]                        │
│                                           │
├───────────────────────────────────────────┤
│  Progress: ████████░░ 80% (4/5)          │
│  Current: Waiting for navigation...       │
└───────────────────────────────────────────┘
```

---

## 📊 MÉTRIQUES DE SUCCÈS

### **MVP (Phase 1)**
- [ ] Record 1 workflow en < 2min
- [ ] Replay success rate > 80%
- [ ] UI responsive (< 100ms interactions)

### **Production (Phase 2)**
- [ ] 10+ workflows enregistrés
- [ ] Success rate > 90%
- [ ] < 50ms latency recording
- [ ] Auto-detect 95% variables sensibles

### **Intelligent (Phase 3)**
- [ ] Agent suggère workflows corrects dans 85% des cas
- [ ] VLM extraction accuracy > 90%
- [ ] Search < 100ms pour 100+ workflows

---

## 🌟 EXEMPLES CONCRETS

### **Exemple 1 : Login GitHub**
```bash
# Enregistrement
User: *clique Record* → navigue github.com → se connecte
System: Workflow "Login GitHub" saved (5 actions, 2 variables)

# Utilisation
User: "log me in to github"
Agent: "I found workflow 'Login GitHub'. Variables?"
User: username=john, password=***
Agent: ▶️ Executing... ✅ Done! You're logged in.
```

### **Exemple 2 : Amazon Price Monitor**
```bash
# Enregistrement
User: *Record* → Amazon → search "iPhone 15" → note price
System: Workflow "Amazon Price Check" saved

# Utilisation
Agent (cron): Runs workflow daily
Agent: "iPhone 15 price: $799 (↓ $50 from yesterday)"
```

---

## 🔗 RESSOURCES & RÉFÉRENCES

### **Technologies**
- **Playwright Tracing** : [docs](https://playwright.dev/docs/trace-viewer)
- **Playwright Codegen** : [docs](https://playwright.dev/docs/codegen)
- **Monaco Editor** : [docs](https://microsoft.github.io/monaco-editor/)
- **React Flow** : [docs](https://reactflow.dev/)

### **Projets Similaires**
- **Selenium IDE** : Browser recorder (mais deprecated)
- **Katalon Recorder** : Chrome extension macro recorder
- **UI.Vision** : Open-source RPA
- **Puppeteer Recorder** : Chrome DevTools extension

### **Papers**
- "Teaching Agents with Demonstrations" (DeepMind)
- "Web Macro Recording for Automation" (ACM)

---

## 🎯 NEXT STEPS

1. **Valider le concept** avec des mockups UI
2. **Prototyper** le recorder (Playwright event capture)
3. **Définir le format JSON** workflow (version 1.0)
4. **Implémenter MVP** (Phase 1)
5. **Beta test** avec 5 workflows réels

---

**FEATURE COMPLÈTEMENT SPÉCIFIÉE ! PRÊTE POUR IMPLÉMENTATION ! 🚀**

