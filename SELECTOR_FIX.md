# 🔍 DIAGNOSTIC : Pourquoi l'agent ne trouve pas les champs de recherche

## ✅ PROBLÈME IDENTIFIÉ

### **Google utilise un `<textarea>` et NON un `<input>` !**

**Résultats du diagnostic :**
```
input[name="q"]      → count=0  ❌ N'EXISTE PAS
textarea[name="q"]   → count=1  ✅ TROUVÉ !
[name="q"]           → count=1  ✅ TROUVÉ !
#APjFqb              → count=1  ✅ TROUVÉ !
```

---

## 🔴 CAUSE DU BUG

L'agent générait des actions comme :
```python
fill('input[name="q"]', 'Playwright GitHub')
```

Mais **Google n'a PAS de `<input name="q">`** !
→ La recherche échouait systématiquement
→ `count=0` → ❌ Could not find field

---

## 🔧 SOLUTION APPLIQUÉE

### **1. Détecter `name=` dans le sélecteur**

```python
if 'name=' in selector:
    # Extraire: input[name="q"] → q
    field_name = extract_name(selector)
    
    # Utiliser sélecteur générique (marche pour input ET textarea)
    generic_selector = f'[name="{field_name}"]'
    await page.fill(generic_selector, text)
```

### **2. Recherche multi-type pour tous les autres cas**

```python
# Avant (ne marchait QUE pour input)
f'input[placeholder*="{selector}" i]'

# Après (marche pour input ET textarea)
f'input[placeholder*="{selector}" i], textarea[placeholder*="{selector}" i]'
```

---

## 📊 STRATÉGIES DE RECHERCHE (dans l'ordre)

1. **Sélecteur CSS direct** : Si le sélecteur fonctionne tel quel
2. **Sélecteur générique `[name="..."]`** : Si `name=` est détecté → **FIX PRINCIPAL**
3. **Par placeholder** : `input[placeholder*="..."], textarea[placeholder*="..."]`
4. **Par name** : `input[name*="..."], textarea[name*="..."]`
5. **Par aria-label** : `input[aria-label*="..."], textarea[aria-label*="..."]`
6. **Générique name** : `[name*="..."]` (dernier recours)

---

## 🧪 TEST

**Avant :**
```
fill('input[name="q"]', 'Playwright')
→ ❌ Could not find field 'input[name="q"]'
```

**Après :**
```
fill('input[name="q"]', 'Playwright')
→ Détection de 'name=' dans le sélecteur
→ Extraction: name="q" → q
→ Recherche avec '[name="q"]' (générique)
→ ✅ Filled [name="q"] with 'Playwright'
```

---

## 🎯 IMPACT

- ✅ **Google** : Fonctionne maintenant (textarea)
- ✅ **GitHub** : Devrait fonctionner (input ou textarea)
- ✅ **Autres sites** : Plus robuste (multi-type)

---

**RELANCE L'APP ET RÉESSAYE ! 🚀**

