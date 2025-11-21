# Améliorations du système TeachMe

## 🎯 Problèmes résolus

### 1. **Scroll non capturé** ✅
- **Avant** : Aucun événement de scroll n'était enregistré
- **Après** : Capture automatique du scroll avec debounce (300ms) pour éviter trop d'événements
- **Fichiers modifiés** : `main.js` (lignes 508-525, 698-713)

### 2. **Sélecteurs CSS inadaptés** ✅
- **Avant** : Utilisation de classes CSS dynamiques/hachées (ex: `EKtkFWMYpwzMKOYr0GYm`)
- **Après** : Système de priorités intelligent :
  1. ID (#id)
  2. Attribut name ([name="..."])
  3. data-testid et data-* attributes
  4. Attributs ARIA (aria-label, role)
  5. Classes CSS **filtrées** (ignore les hash dynamiques)
  6. Tag simple en dernier recours
- **Fichiers modifiés** : `main.js` (lignes 371-420, 576-623)

### 3. **Manque d'informations contextuelles** ✅
- **Avant** : Seulement le sélecteur CSS
- **Après** : Capture enrichie avec :
  - Texte visible (limité à 100 caractères)
  - Position dans une liste (index + totalSiblings)
  - Attributs ARIA (aria-label, role)
  - Href pour les liens
- **Fichiers modifiés** : `main.js` (lignes 422-457, 625-655)

### 4. **Replay fragile** ✅
- **Avant** : Échec immédiat si le sélecteur CSS ne fonctionne pas
- **Après** : Système de fallback intelligent avec 6 stratégies :
  1. Sélecteur CSS direct
  2. href (pour les liens)
  3. aria-label
  4. Texte visible (exact puis partial)
  5. role + index
  6. tag + index
- **Fichiers modifiés** : `python/workflow_player.py` (lignes 96-183)

### 5. **Support du scroll au replay** ✅
- **Avant** : Actions de scroll ignorées
- **Après** : Replay correct des positions de scroll
- **Fichiers modifiés** : `python/workflow_player.py` (lignes 53-54, 204-212)

## 🔍 Exemples de transformations

### Avant (problématique)
```javascript
// Sélecteur capturé
selector: "span.EKtkFWMYpwzMKOYr0GYm.LQVY1Jpkk8nyJ6HBWKAk"
text: "Playmobil Official Website"
```

### Après (robuste)
```javascript
{
  selector: "a[href='https://www.playmobil.com']",  // ou "a" si classes filtrées
  context: {
    text: "Playmobil Official Website",
    href: "https://www.playmobil.com/fr-fr",
    index: 0,
    totalSiblings: 10
  }
}
```

## 🛠️ Détails techniques

### Filtrage des classes dynamiques
```javascript
const classes = element.className.trim().split(/\s+/).filter(cls => {
  return cls.length < 30 &&                    // Pas trop longues
         !/^[A-Z][a-z0-9]{15,}/.test(cls) &&  // Pas de pattern hash React
         !/^[a-f0-9]{8,}/.test(cls);          // Pas de hash hexadécimal
});
```

### Debounce du scroll
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
  }, 300); // Attendre 300ms après le dernier scroll
}, true);
```

### Fallback intelligent au replay
```python
# Stratégie 1: CSS
await self.page.click(selector, timeout=5000)

# Stratégie 2: href
if context.get('href'):
    await self.page.click(f'a[href="{href}"]', timeout=5000)

# Stratégie 3: aria-label
if context.get('ariaLabel'):
    await self.page.click(f'[aria-label="{aria_label}"]', timeout=5000)

# Stratégie 4: Texte visible
if text:
    await self.page.get_by_text(text, exact=True).first.click(timeout=5000)

# etc...
```

## 📊 Résultats attendus

Avec ces améliorations, le workflow playmobil devrait :

1. ✅ **Capturer le scroll** avant de cliquer sur un résultat de recherche
2. ✅ **Utiliser le texte visible ou le href** au lieu des classes dynamiques
3. ✅ **Replay réussi** même si la page DuckDuckGo change légèrement
4. ✅ **Trouver le bon lien** parmi les résultats de recherche grâce au contexte

## 🧪 Test recommandé

Pour tester les améliorations :

1. Lancer l'application : `./start.sh`
2. Enregistrer un nouveau workflow avec :
   - Navigation sur DuckDuckGo
   - Recherche "playmobil"
   - **Scroll** pour voir les résultats
   - Clic sur le bon lien (celui avec le texte "Playmobil Official")
3. Rejouer le workflow
4. Vérifier que le système :
   - Enregistre bien le scroll
   - Clique sur le bon lien (même si les classes CSS ont changé)
   - Utilise le fallback si nécessaire

## 📝 Notes importantes

- Les **anciennes macros** enregistrées **ne bénéficient PAS** des améliorations de fallback (pas de contexte sauvegardé)
- Il faut **réenregistrer** les workflows pour profiter du nouveau système
- Le **debounce du scroll** peut être ajusté (300ms actuellement) selon les besoins
- Les **logs de fallback** sont en mode `debug` pour ne pas polluer la console

## 🔄 Prochaines étapes possibles

1. Ajouter support des événements clavier (tab, enter, esc)
2. Capturer les changements de viewport (resize)
3. Ajouter un système de "smart wait" (attendre qu'un élément apparaisse)
4. Améliorer la détection des classes dynamiques avec ML
5. Ajouter des assertions visuelles (screenshot diff)

