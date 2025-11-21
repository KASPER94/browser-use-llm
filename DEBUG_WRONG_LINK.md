# 🔍 Guide de Debug - Clic sur le mauvais lien

## Problème
L'agent ne clique toujours pas sur le bon lien dans les résultats de recherche DuckDuckGo.

## 🆕 Améliorations apportées

### 1. Logs ultra-détaillés
Maintenant, lors du replay, tu verras **exactement** :
- Le texte et domaine attendus
- Tous les liens trouvés sur la page
- Le score de chaque lien (top 5)
- Quelle stratégie fonctionne/échoue

### 2. Score amélioré
- ✅ Correspondance de texte plus intelligente (mots communs)
- ✅ Gestion des variantes de domaine (www.site.com vs site.com)
- ✅ Seuil abaissé à 50 (au lieu de 80)

### 3. Toutes les stratégies loggées
Chaque stratégie affiche maintenant son résultat.

---

## 📋 Comment débugger

### Étape 1 : Enregistrer un nouveau workflow

**IMPORTANT** : Les anciens workflows n'ont pas le contexte enrichi !

```bash
./start.sh
# 1. Démarrer un enregistrement
# 2. DuckDuckGo → "playmobil"
# 3. SCROLL pour voir les résultats
# 4. Clic sur le site officiel (playmobil.fr)
# 5. Arrêter l'enregistrement
```

### Étape 2 : Vérifier le contexte capturé

```bash
# Regarder le workflow enregistré
cat workflows/wf_xxxxx.json | jq '.actions[] | select(.type == "click" and .context.href != null)'

# Tu DOIS voir quelque chose comme :
{
  "type": "click",
  "selector": "a",
  "context": {
    "text": "PLAYMOBIL® France - Site Officiel",
    "href": "https://www.playmobil.fr/",
    "index": 0
  }
}
```

**Si le contexte est vide ou incomplet** → Le problème est à la capture, pas au replay !

---

### Étape 3 : Rejouer et analyser les logs

```bash
# Rejouer le workflow
# Dans le terminal, tu verras maintenant :

[X/Y] click
  📋 Click action details:
     selector: a
     context: {'text': 'PLAYMOBIL® France...', 'href': 'https://www.playmobil.fr/', ...}
  
  🔍 Smart link matching:
     Expected text: 'PLAYMOBIL® France - Site Officiel'
     Expected domain: 'www.playmobil.fr'
     Expected href: 'https://www.playmobil.fr/'
     Found 15 visible links on page
     
     💡 New best match (score=190): ['text_contains=70', 'domain_exact=100']
        text: PLAYMOBIL® France - Site Officiel
        href: https://www.playmobil.fr/
  
  📊 Top candidates:
     #1 [score=190] PLAYMOBIL® France - Site Officiel
         → https://www.playmobil.fr/
         → text_contains=70, domain_exact=100
     #2 [score= 50] Playmobil - Amazon.fr
         → https://www.amazon.fr/playmobil
         → text_partial=50
     #3 [score= 30] Jouets Playmobil
         → https://www.jouetclub.fr/playmobil
         → common_words=30
  
  ✅ Clicked best match (score=190)
```

---

## 🔍 Diagnostics possibles

### Cas 1 : Le contexte est vide
```
context: {}
```

**Problème** : Ancien workflow sans contexte  
**Solution** : Réenregistrer le workflow

---

### Cas 2 : Le domaine ne correspond pas
```
Expected domain: 'www.playmobil.fr'
#1 [score=50] PLAYMOBIL® France
    → https://www.playmobil.com/fr-fr  ← Domaine différent !
    → text_contains=50
```

**Problème** : Le domaine change entre enregistrement et replay  
**Solution** : Le score devrait quand même être suffisant (50+). Regarder les autres candidats.

---

### Cas 3 : Aucun lien trouvé
```
Found 0 visible links on page
```

**Problème** : La page n'a pas fini de charger  
**Solution** : Augmenter le timeout `networkidle`

---

### Cas 4 : Le bon lien existe mais score trop faible
```
#3 [score=45] PLAYMOBIL® Site Officiel  ← C'est celui-ci !
    → https://www.playmobil.fr/
    → common_words=30, domain_main=90
```

**Problème** : Score < 50 (seuil actuel)  
**Solution** : Abaisser encore le seuil ou améliorer le scoring

---

### Cas 5 : Plusieurs liens avec score élevé
```
#1 [score=150] PLAYMOBIL® France
#2 [score=150] PLAYMOBIL® Official
```

**Problème** : Ambiguïté  
**Solution** : Utiliser l'index ou améliorer le scoring

---

## 🛠️ Ajustements possibles

### 1. Abaisser le seuil (si score juste en dessous de 50)

Dans `workflow_player.py` ligne 247 :
```python
# Actuellement
if best_match and best_score >= 50:

# Essayer
if best_match and best_score >= 40:  # ou 30
```

---

### 2. Booster le score du texte

Lignes 168-187, augmenter les valeurs :
```python
# Actuellement
if text_lower == link_text_lower:
    score += 100  # exact
elif text_lower in link_text_lower:
    score += 70   # contains

# Essayer
if text_lower == link_text_lower:
    score += 150  # exact
elif text_lower in link_text_lower:
    score += 100  # contains
```

---

### 3. Utiliser l'index comme tiebreaker

Si plusieurs liens ont le même score, utiliser l'index capturé :
```python
# Après la boucle de scoring
if len([c for c in all_candidates if c['score'] == best_score]) > 1:
    # Plusieurs candidats avec le même score
    if context.get('index') is not None:
        index = context['index']
        # Utiliser le candidat à l'index capturé
        best_match = links[index]
```

---

## 📤 Partage des logs pour debug

Si le problème persiste, copie et partage :

```bash
# 1. Le contexte capturé
cat workflows/wf_xxxxx.json | jq '.actions[] | select(.type == "click" and .context.href != null)'

# 2. Les logs du replay (section "Smart link matching")
# Copier depuis le terminal, de "🔍 Smart link matching:" jusqu'à "✅ Clicked" ou "❌ Strategy"
```

Avec ces infos, on pourra voir exactement pourquoi le mauvais lien est choisi.

---

## 🎯 Test rapide

```bash
# 1. Enregistrer NOUVEAU workflow
./start.sh → Record → DuckDuckGo → "playmobil" → scroll → clic site officiel

# 2. Vérifier le contexte
cat workflows/*.json | tail -1 | jq '.actions[] | select(.type == "click")'

# 3. Rejouer et copier les logs
# Chercher la section avec "📊 Top candidates"

# 4. Partager les logs ici
```

Les logs ultra-détaillés montreront exactement ce qui se passe ! 🔍

