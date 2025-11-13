# 🎯 Agent Hybride : BrowserGym + BrowserOS

## ✅ IMPLÉMENTÉ !

L'agent hybride combine le meilleur des deux mondes :

### **🟢 De BrowserGym :**
- ✅ Observations riches (screenshots, AXTree, DOM)
- ✅ Historique des actions et erreurs
- ✅ Action set complet

### **🟣 De BrowserOS :**
- ✅ Planning multi-étapes (rolling-horizon)
- ✅ Raisonnement explicite (step-by-step thinking)
- ✅ Validation périodique
- ✅ Re-planification adaptative
- ✅ Détection de boucles

---

## 🔧 Architecture

```python
for iteration in range(MAX_ITERATIONS):
    # 1. Get Rich Observation (BrowserGym)
    obs = {
        'screenshot': base64 image,
        'url': current URL,
        'title': page title,
        'axtree': DOM structure,
        'last_action': previous action,
        'last_error': error if any
    }
    
    # 2. Plan (BrowserOS - every 5 steps or on error)
    if should_replan(obs):
        plan = create_plan({
            'user_task': "user's goal",
            'execution_history': "what's been tried",
            'current_state': "page + screenshot",
            'challenges': "errors encountered",
            'reasoning': "step-by-step thinking",
            'proposed_actions': [
                {'action': 'goto(url)', 'reasoning': 'why'},
                {'action': 'click(button)', 'reasoning': 'why'}
            ]
        })
    
    # 3. Execute next action
    action = plan.proposed_actions.pop(0)
    result = execute_action(action)
    
    # 4. Validate (every 3 steps)
    if iteration % 3 == 0:
        validation = validate_progress(user_task, obs)
        if validation.is_complete:
            break
    
    # 5. Detect loops & replan
    if detect_loop() or result.error:
        plan = replan()
```

---

## 🎮 Utilisation

L'agent hybride est activé **par défaut** si `OPENAI_API_KEY` est configuré.

### **Mode Hybrid (recommandé) :**
```python
# Le serveur détecte automatiquement et utilise l'agent hybride
server = BrowserGymServer(use_hybrid=True)
```

Logs :
```
✅ Hybrid Agent initialized (BrowserGym + BrowserOS)
🎯 Using Hybrid Agent (Planning + Rich Observations)
🧠 Creating multi-step plan...
📌 Executing: goto('https://google.com')
💭 Reasoning: Need to access search engine first
🔍 Validating progress...
```

### **Mode Simple LLM (fallback) :**
```python
server = BrowserGymServer(use_hybrid=False, use_llm=True)
```

Logs :
```
✅ LLM Agent initialized (simple)
🤖 Using Simple LLM Agent
```

### **Mode Keyword (sans LLM) :**
```python
server = BrowserGymServer(use_hybrid=False, use_llm=False)
```

---

## 🔬 Fonctionnalités Avancées

### **1. Vision avec Screenshots**
L'agent peut voir les pages via GPT-4o-mini vision :
```python
observation = get_rich_observation(page)
# observation.screenshot_base64 envoyé au LLM
plan = create_plan(user_task, observation)
```

### **2. Raisonnement Explicite**
Chaque action est justifiée :
```json
{
  "action": "fill('search', 'python tutorials')",
  "reasoning": "User wants to search for Python tutorials, need to fill the search box first"
}
```

### **3. Validation Continue**
Tous les 3 steps :
```python
validation = validate_progress(user_task, observation)
# {"is_complete": false, "progress_percentage": 40, "next_needed": "Click search button"}
```

### **4. Détection de Boucles**
Si l'agent répète 3x la même action :
```python
if detect_loop():
    logger.warning("⚠️ Loop detected, replanning...")
    plan = replan()
```

---

## 📊 Comparaison

| Feature | Simple LLM | **Hybrid Agent** |
|---------|------------|------------------|
| Planning | ❌ | ✅ (rolling-horizon) |
| Screenshots | ❌ | ✅ (vision) |
| Reasoning | ⚠️ (implicite) | ✅ (explicite) |
| Validation | ❌ | ✅ (périodique) |
| Replan on error | ❌ | ✅ (automatique) |
| Loop detection | ❌ | ✅ |
| Max actions | 1 | 30 (configurable) |

---

## 🧪 Test

```bash
cd browsergym-electron
./start.sh
```

**Commandes de test :**
- Simple : `search for python tutorials`
- Complexe : `find the latest Python tutorial on Real Python and summarize it`
- Multi-étapes : `go to github, search for browsergym, open the first result, and tell me the number of stars`

---

## 🔮 Prochaines Étapes (TODO)

- [ ] Implémenter actions `click()` et `fill()`
- [ ] Ajouter extraction complète de l'AXTree
- [ ] Support multi-tabs
- [ ] Système de mémoire pour tâches longues
- [ ] UI pour afficher le plan et le raisonnement

