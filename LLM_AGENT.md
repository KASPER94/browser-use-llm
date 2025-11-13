# 🤖 LLM Agent Integration

## ✅ INTÉGRÉ !

L'agent LLM (GPT-4o-mini) est maintenant intégré dans l'app Electron !

---

## 🔑 Configuration requise

### **Clé API OpenAI**

L'app va chercher `OPENAI_API_KEY` dans l'environnement. Deux options :

#### **Option 1 : Fichier `.env` (déjà configuré)**
```bash
# .env à la racine de BrowserGym
OPENAI_API_KEY=sk-proj-...
```

#### **Option 2 : Export direct**
```bash
export OPENAI_API_KEY="sk-proj-..."
```

---

## 📋 Comment ça marche

### **Avec LLM activé** (par défaut si `OPENAI_API_KEY` est définie) :
```
User: "search for python tutorials"
  ↓
LLM: goto("https://www.google.com/search?q=python+tutorials")
  ↓
Navigation automatique ✅
```

### **Sans LLM** (fallback) :
```
User: "go on google"
  ↓
Simple keyword matching
  ↓
Navigation ✅
```

---

## 🎯 Actions supportées (pour l'instant)

- ✅ **goto(url)** : Navigation vers une URL
- ⚠️ **click(element)** : Pas encore implémenté
- ⚠️ **fill(input, text)** : Pas encore implémenté
- ✅ **send_msg_to_user(message)** : Réponse texte

---

## 🧪 Exemples de commandes

Avec le LLM, tu peux maintenant dire :
- "search for python tutorials"
- "go to wikipedia"
- "open the github page for playwright"
- "find information about machine learning"

Au lieu de juste :
- "go on google"
- "open github"

---

## 🚀 Lancement

```bash
cd browsergym-electron
source ../.venv/bin/activate  # Active l'environnement Python avec la clé API
./start.sh
```

Le serveur va afficher :
- `✅ LLM Agent initialized (gpt-4o-mini)` si la clé API est trouvée
- `⚠️ Failed to initialize LLM agent` sinon (fallback sur keyword matching)

