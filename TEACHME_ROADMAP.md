# TeachMe - Roadmap des améliorations

## 📊 État actuel (✅ Fait)

### Capture basique
- ✅ Clics avec contexte (texte, href, aria-label, index)
- ✅ Saisies de texte
- ✅ Scroll (position x, y)
- ✅ Navigations
- ✅ Sélecteurs CSS robustes (filtre classes dynamiques)

### Replay intelligent
- ✅ Fallback multi-stratégies (6 stratégies)
- ✅ Support du contexte (href, aria-label, texte, index)
- ✅ Gestion basique des erreurs (3 échecs max)

---

## 🎯 Améliorations prioritaires

### 1. **Analyse sémantique des actions** 🧠

#### Objectif
Comprendre **l'intention** de l'utilisateur, pas seulement les actions brutes.

#### Implémentation

**Détection de patterns :**
```javascript
// Dans la capture
function detectActionIntent(action, previousActions) {
  const patterns = {
    // Login flow
    isLogin: () => {
      const hasEmailField = previousActions.some(a => 
        a.type === 'fill' && /email|username|login/.test(a.selector)
      );
      const hasPasswordField = previousActions.some(a => 
        a.type === 'fill' && /password|pwd/.test(a.selector)
      );
      return hasEmailField && hasPasswordField;
    },
    
    // Search flow
    isSearch: () => {
      return action.type === 'fill' && 
             /search|query|q/.test(action.selector) &&
             nextAction?.type === 'click' && 
             /search|submit/.test(nextAction.selector);
    },
    
    // Form submission
    isFormSubmit: () => {
      return action.type === 'click' && 
             /submit|send|save|create/.test(action.context?.text || '');
    },
    
    // Navigation
    isNavigation: () => {
      return action.type === 'click' && 
             action.context?.href && 
             !action.context.href.includes('#');
    }
  };
  
  // Annoter l'action
  return {
    ...action,
    intent: {
      type: detectIntentType(patterns),
      confidence: 0.85,
      description: generateDescription(action)
    }
  };
}
```

**Génération de description automatique :**
```javascript
function generateActionDescription(action) {
  switch (action.intent?.type) {
    case 'login':
      return '🔐 Se connecter avec un compte utilisateur';
    case 'search':
      return `🔍 Rechercher "${action.value}"`;
    case 'navigation':
      return `🌐 Naviguer vers ${new URL(action.context.href).hostname}`;
    case 'form_submit':
      return '📤 Soumettre le formulaire';
    default:
      return `${action.type} sur ${action.context?.text || action.selector}`;
  }
}
```

**Backend (Python) :**
```python
class WorkflowAnalyzer:
    """Analyse sémantique des workflows"""
    
    def analyze_workflow(self, actions: List[Dict]) -> Dict:
        """Analyse complète d'un workflow"""
        return {
            'intents': self._detect_intents(actions),
            'flows': self._detect_flows(actions),
            'variables': self._detect_variables(actions),
            'recommendations': self._generate_recommendations(actions)
        }
    
    def _detect_flows(self, actions: List[Dict]) -> List[Dict]:
        """Détecte des flows métier (login, checkout, search, etc.)"""
        flows = []
        
        # Login flow
        email_action = next((a for a in actions if 'email' in a.get('selector', '').lower()), None)
        password_action = next((a for a in actions if 'password' in a.get('selector', '').lower()), None)
        
        if email_action and password_action:
            flows.append({
                'type': 'authentication',
                'steps': [email_action, password_action],
                'confidence': 0.9
            })
        
        return flows
    
    def _detect_variables(self, actions: List[Dict]) -> List[Dict]:
        """Détecte les valeurs qui pourraient être des variables"""
        variables = []
        
        for action in actions:
            if action.get('type') == 'fill':
                value = action.get('value', '')
                
                # Email
                if '@' in value:
                    variables.append({
                        'name': 'user_email',
                        'type': 'email',
                        'example_value': value,
                        'action_index': actions.index(action)
                    })
                
                # Numéro de téléphone
                elif re.match(r'^\+?\d{10,}$', value):
                    variables.append({
                        'name': 'phone_number',
                        'type': 'phone',
                        'example_value': value,
                        'action_index': actions.index(action)
                    })
                
                # Texte générique
                elif len(value) > 3:
                    variables.append({
                        'name': f'input_{actions.index(action)}',
                        'type': 'text',
                        'example_value': value,
                        'action_index': actions.index(action)
                    })
        
        return variables
```

---

### 2. **Variables et paramètres dynamiques** 🔄

#### Objectif
Permettre de rejouer un workflow avec des valeurs différentes.

#### Implémentation

**Interface de paramétrage :**
```typescript
interface WorkflowVariable {
  name: string;
  type: 'text' | 'email' | 'phone' | 'url' | 'number';
  defaultValue: string;
  description: string;
  required: boolean;
}

interface ParameterizedWorkflow extends Workflow {
  variables: WorkflowVariable[];
  parameterized_actions: Array<{
    ...Action,
    value: string | { variable: string }  // "{{user_email}}" ou valeur fixe
  }>;
}
```

**UI de paramétrage :**
```typescript
function WorkflowParametersForm({ workflow, onPlay }: Props) {
  const [parameters, setParameters] = useState<Record<string, string>>({});
  
  return (
    <div className="workflow-parameters">
      <h3>🔧 Paramètres du workflow</h3>
      {workflow.variables.map(variable => (
        <div key={variable.name} className="parameter-field">
          <label>{variable.description}</label>
          <input
            type={variable.type}
            defaultValue={variable.defaultValue}
            required={variable.required}
            onChange={(e) => setParameters({
              ...parameters,
              [variable.name]: e.target.value
            })}
          />
        </div>
      ))}
      <button onClick={() => onPlay(parameters)}>
        ▶️ Lancer avec ces paramètres
      </button>
    </div>
  );
}
```

**Replay avec substitution :**
```python
class ParameterizedWorkflowPlayer:
    """Player qui supporte les variables"""
    
    async def play(self, workflow: Dict, parameters: Dict[str, str]) -> Dict:
        """Rejoue avec substitution des variables"""
        
        for action in workflow['actions']:
            # Substituer les variables dans value
            if action.get('type') == 'fill':
                value = action.get('value', '')
                
                # Remplacer {{variable_name}} par la valeur réelle
                for var_name, var_value in parameters.items():
                    value = value.replace(f'{{{{{var_name}}}}}', var_value)
                
                action['value'] = value
            
            # Exécuter l'action
            await self._execute_action(action)
```

---

### 3. **Détection de patterns et optimisation** ⚡

#### Objectif
Identifier les actions redondantes et optimiser le workflow.

#### Patterns à détecter

**1. Clics multiples sur le même élément (debounce)**
```javascript
// AVANT (capturé)
[
  { type: 'click', selector: '#button', timestamp: 1000 },
  { type: 'click', selector: '#button', timestamp: 1050 },
  { type: 'click', selector: '#button', timestamp: 1100 }
]

// APRÈS (optimisé)
[
  { type: 'click', selector: '#button', timestamp: 1000 }
]
```

**2. Saisies progressives → Saisie finale**
```javascript
// AVANT (capturé - chaque caractère)
[
  { type: 'fill', selector: '#search', value: 'p' },
  { type: 'fill', selector: '#search', value: 'pl' },
  { type: 'fill', selector: '#search', value: 'pla' },
  { type: 'fill', selector: '#search', value: 'play' },
  { type: 'fill', selector: '#search', value: 'playm' },
  { type: 'fill', selector: '#search', value: 'playmo' },
  { type: 'fill', selector: '#search', value: 'playmob' },
  { type: 'fill', selector: '#search', value: 'playmobi' },
  { type: 'fill', selector: '#search', value: 'playmobil' }
]

// APRÈS (optimisé)
[
  { type: 'fill', selector: '#search', value: 'playmobil' }
]
```

**3. Navigation inutile**
```javascript
// AVANT
[
  { type: 'goto', url: 'https://duckduckgo.com' },
  { type: 'goto', url: 'https://duckduckgo.com' },  // Doublon
  { type: 'goto', url: 'https://duckduckgo.com' }   // Doublon
]

// APRÈS
[
  { type: 'goto', url: 'https://duckduckgo.com' }
]
```

**Implémentation de l'optimiseur :**
```python
class WorkflowOptimizer:
    """Optimise un workflow en supprimant les actions redondantes"""
    
    def optimize(self, actions: List[Dict]) -> List[Dict]:
        """Optimise le workflow"""
        optimized = []
        
        # 1. Fusionner les fills consécutifs sur le même champ
        optimized = self._merge_consecutive_fills(actions)
        
        # 2. Supprimer les clics multiples
        optimized = self._debounce_clicks(optimized)
        
        # 3. Supprimer les navigations redondantes
        optimized = self._remove_duplicate_navigations(optimized)
        
        # 4. Supprimer les scroll intermédiaires (garder le dernier avant une action)
        optimized = self._optimize_scrolls(optimized)
        
        return optimized
    
    def _merge_consecutive_fills(self, actions: List[Dict]) -> List[Dict]:
        """Fusionne les fills consécutifs sur le même champ"""
        result = []
        i = 0
        
        while i < len(actions):
            action = actions[i]
            
            if action['type'] == 'fill':
                # Chercher le dernier fill sur ce champ
                selector = action['selector']
                last_fill_index = i
                
                for j in range(i + 1, len(actions)):
                    if actions[j]['type'] == 'fill' and actions[j]['selector'] == selector:
                        last_fill_index = j
                    else:
                        break
                
                # Garder seulement le dernier fill
                result.append(actions[last_fill_index])
                i = last_fill_index + 1
            else:
                result.append(action)
                i += 1
        
        return result
    
    def _debounce_clicks(self, actions: List[Dict], threshold_ms: int = 500) -> List[Dict]:
        """Supprime les clics multiples rapides sur le même élément"""
        result = []
        last_click = None
        
        for action in actions:
            if action['type'] == 'click':
                if last_click and \
                   action['selector'] == last_click['selector'] and \
                   action['timestamp'] - last_click['timestamp'] < threshold_ms:
                    # Skip ce clic (doublon)
                    continue
                
                last_click = action
            
            result.append(action)
        
        return result
```

---

### 4. **Assertions et validations** ✔️

#### Objectif
Vérifier que le workflow produit le résultat attendu.

#### Types d'assertions

```python
class WorkflowAssertion:
    """Une assertion à vérifier pendant le replay"""
    
    def __init__(self, type: str, **kwargs):
        self.type = type
        self.params = kwargs
    
    async def verify(self, page: Page) -> bool:
        """Vérifie l'assertion"""
        if self.type == 'url_contains':
            return self.params['text'] in page.url
        
        elif self.type == 'element_visible':
            return await page.locator(self.params['selector']).is_visible()
        
        elif self.type == 'text_present':
            return await page.get_by_text(self.params['text']).count() > 0
        
        elif self.type == 'page_title':
            title = await page.title()
            return self.params['expected'] in title
        
        return False
```

**Capture automatique d'assertions :**
```javascript
function capturePostActionState(action) {
  // Après chaque action importante, capturer l'état
  if (action.type === 'click' || action.type === 'fill') {
    return {
      ...action,
      assertions: [
        {
          type: 'url_contains',
          text: window.location.pathname,
          description: `URL contient "${window.location.pathname}"`
        },
        {
          type: 'element_visible',
          selector: action.selector,
          description: `Element "${action.selector}" est visible`
        }
      ]
    };
  }
}
```

---

### 5. **Attentes intelligentes (Smart waits)** ⏱️

#### Objectif
Attendre les bonnes conditions avant d'exécuter une action.

#### Implémentation

```python
class SmartWaiter:
    """Gère les attentes intelligentes"""
    
    async def wait_for_action(self, page: Page, action: Dict):
        """Attend les bonnes conditions avant d'exécuter l'action"""
        
        # 1. Attendre que la page soit stable (pas de network activity)
        await page.wait_for_load_state('networkidle', timeout=5000)
        
        # 2. Pour un click, attendre que l'élément soit cliquable
        if action['type'] == 'click':
            selector = action['selector']
            await page.wait_for_selector(selector, state='visible', timeout=5000)
            await page.wait_for_selector(selector, state='attached', timeout=5000)
            
            # Attendre que l'animation CSS soit terminée
            await page.evaluate(f'''
                (selector) => {{
                    const el = document.querySelector(selector);
                    return new Promise(resolve => {{
                        if (!el) return resolve();
                        
                        const checkAnimation = () => {{
                            const style = window.getComputedStyle(el);
                            if (style.animationName === 'none') {{
                                resolve();
                            }} else {{
                                setTimeout(checkAnimation, 100);
                            }}
                        }};
                        checkAnimation();
                    }});
                }}
            ''', selector)
        
        # 3. Pour un fill, attendre que le champ soit éditable
        elif action['type'] == 'fill':
            selector = action['selector']
            await page.wait_for_selector(selector, state='visible', timeout=5000)
            await page.locator(selector).wait_for(state='editable', timeout=5000)
```

---

### 6. **Export et partage de workflows** 📤

#### Formats d'export

**1. JSON portable**
```json
{
  "format": "browsergym-workflow-v1",
  "workflow": {
    "name": "Login to Gmail",
    "description": "Automatise la connexion à Gmail",
    "variables": [
      {
        "name": "user_email",
        "type": "email",
        "description": "Votre adresse email"
      }
    ],
    "actions": [...]
  }
}
```

**2. Code Python généré**
```python
# Export en tant que script Playwright
async def run_workflow(page, user_email, password):
    """Workflow: Login to Gmail"""
    
    # Step 1: Navigate to Gmail
    await page.goto('https://gmail.com')
    
    # Step 2: Fill email
    await page.fill('input[type="email"]', user_email)
    await page.click('button:has-text("Next")')
    
    # Step 3: Fill password
    await page.fill('input[type="password"]', password)
    await page.click('button:has-text("Sign in")')
    
    # Assertion: Check we're logged in
    await page.wait_for_url('**/mail/**')
```

**3. Documentation Markdown**
```markdown
# Workflow: Login to Gmail

## Description
Automatise la connexion à Gmail avec un compte utilisateur.

## Paramètres requis
- `user_email` (email) - Votre adresse email
- `password` (password) - Votre mot de passe

## Étapes
1. 🌐 Naviguer vers https://gmail.com
2. ✏️ Saisir l'email dans le champ "Email"
3. 👆 Cliquer sur "Next"
4. ✏️ Saisir le mot de passe
5. 👆 Cliquer sur "Sign in"

## Assertions
- ✅ L'URL finale contient "/mail/"
- ✅ Le bouton "Compose" est visible
```

---

### 7. **Visualisation et timeline** 📊

#### Interface de visualisation

```typescript
function WorkflowTimeline({ workflow }: Props) {
  return (
    <div className="workflow-timeline">
      {workflow.actions.map((action, index) => (
        <div key={index} className="timeline-item">
          <div className="timeline-marker">
            {getActionIcon(action.type)}
          </div>
          <div className="timeline-content">
            <div className="action-type">{action.type}</div>
            <div className="action-details">
              {action.intent?.description || action.selector}
            </div>
            <div className="action-timestamp">
              {formatTimestamp(action.timestamp)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Graphe de dépendances :**
```typescript
// Visualiser les relations entre actions
function WorkflowGraph({ workflow }: Props) {
  const nodes = workflow.actions.map((action, i) => ({
    id: i,
    label: action.intent?.description || action.type,
    type: action.type
  }));
  
  const edges = detectDependencies(workflow.actions);
  
  return <ReactFlowRenderer nodes={nodes} edges={edges} />;
}
```

---

### 8. **Analytics et métriques** 📈

#### Métriques à tracker

```python
class WorkflowAnalytics:
    """Analytics pour les workflows"""
    
    def compute_metrics(self, workflow: Dict, execution_result: Dict) -> Dict:
        """Calcule les métriques d'un workflow"""
        
        actions = workflow['actions']
        
        return {
            # Performance
            'total_duration': execution_result['duration'],
            'avg_action_duration': execution_result['duration'] / len(actions),
            'slowest_action': max(actions, key=lambda a: a.get('duration', 0)),
            
            # Fiabilité
            'success_rate': execution_result['actions_executed'] / len(actions),
            'failure_points': execution_result['errors'],
            
            # Complexité
            'action_count': len(actions),
            'unique_selectors': len(set(a['selector'] for a in actions if 'selector' in a)),
            'navigation_count': sum(1 for a in actions if a['type'] == 'goto'),
            
            # Patterns détectés
            'detected_flows': self.analyzer.detect_flows(actions),
            'potential_variables': self.analyzer.detect_variables(actions)
        }
```

---

## 🎨 Interface utilisateur améliorée

### 1. Mode "Ghost" pendant l'enregistrement
```typescript
// Overlay transparent qui montre ce qui est capturé
function RecordingOverlay() {
  return (
    <div className="recording-overlay">
      <div className="captured-actions-feed">
        {capturedActions.map((action, i) => (
          <div key={i} className="captured-action-pill">
            {getActionIcon(action.type)} {action.intent?.description}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 2. Éditeur de workflow
```typescript
function WorkflowEditor({ workflow, onChange }: Props) {
  return (
    <div className="workflow-editor">
      {workflow.actions.map((action, index) => (
        <ActionEditor
          key={index}
          action={action}
          onUpdate={(updated) => updateAction(index, updated)}
          onDelete={() => deleteAction(index)}
          onMoveUp={() => moveAction(index, index - 1)}
          onMoveDown={() => moveAction(index, index + 1)}
        />
      ))}
    </div>
  );
}
```

### 3. Debugger interactif
```typescript
function WorkflowDebugger({ workflow }: Props) {
  const [currentStep, setCurrentStep] = useState(0);
  const [breakpoints, setBreakpoints] = useState<number[]>([]);
  
  return (
    <div className="workflow-debugger">
      <div className="debugger-controls">
        <button onClick={() => stepInto()}>⏭️ Step Into</button>
        <button onClick={() => stepOver()}>⏩ Step Over</button>
        <button onClick={() => continue()}>▶️ Continue</button>
        <button onClick={() => pause()}>⏸️ Pause</button>
      </div>
      
      <div className="debugger-state">
        <h4>Current State</h4>
        <pre>{JSON.stringify(getCurrentState(), null, 2)}</pre>
      </div>
    </div>
  );
}
```

---

## 📋 Priorités suggérées

### Phase 1 : Optimisation (1-2 semaines)
1. ✅ Fusion des fills consécutifs
2. ✅ Debounce des clics
3. ✅ Suppression des navigations dupliquées
4. ✅ Smart waits basiques

### Phase 2 : Intelligence (2-3 semaines)
5. 🧠 Détection d'intentions (login, search, form)
6. 📝 Génération de descriptions automatiques
7. 🔍 Détection de variables potentielles
8. ✨ Suggestions d'amélioration

### Phase 3 : Paramétrage (2 semaines)
9. 🔧 Support des variables
10. 📋 Interface de paramétrage
11. 🔄 Replay avec substitution

### Phase 4 : Qualité (1-2 semaines)
12. ✔️ Système d'assertions
13. 📊 Métriques et analytics
14. 🐛 Debugger interactif

### Phase 5 : Partage (1 semaine)
15. 📤 Export multi-format (JSON, Python, Markdown)
16. 📚 Bibliothèque de workflows partagés
17. 🎨 Visualisation avancée

---

## 🚀 Quick wins (à faire en premier)

Ces améliorations apportent le plus de valeur avec le moins d'effort :

1. **Fusion des fills** (2h) → Réduit immédiatement le bruit
2. **Descriptions automatiques** (4h) → Rend les workflows lisibles
3. **Smart waits** (3h) → Améliore la fiabilité
4. **Export JSON** (2h) → Permet le partage

**Total : ~11 heures pour un impact majeur !**

