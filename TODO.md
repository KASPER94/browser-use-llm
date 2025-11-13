# 📋 TODO - Prochaines Features BrowserGym Electron

**Date:** 13 Novembre 2025  
**Version:** 1.0  
**Projet:** BrowserGym Electron - Agent Hybride

---

## 🎯 PRIORITÉ 1 : MODE "REPRISE DE CONTRÔLE UTILISATEUR"

### **Description**
Permettre à l'utilisateur de **reprendre la main** sur le navigateur quand:
- Le modèle est trop lent
- L'agent est bloqué
- Besoin de saisir un mot de passe
- Intervention manuelle nécessaire

### **Comportement Souhaité**
1. **Mode Screenshot** (par défaut) → **Mode WebView Interactif** (smooth transition)
2. Bouton avec icône 🖐️ au-dessus du champ de prompt
3. Clic → pause de l'agent + affichage WebView interactif
4. Utilisateur peut interagir normalement avec la page
5. Bouton "Reprendre" → agent réanalyse la situation + continue

### **Implémentation Technique**

#### **Frontend (React + Electron)**
- [ ] **Ajouter bouton "Take Control"** dans `ChatPanel.tsx`
  - Icône: 🖐️ ou SVG hand icon
  - Position: Au-dessus de `InputBox`
  - État: `enabled` quand agent actif, `disabled` sinon
  
- [ ] **Créer composant `InteractiveWebView.tsx`**
  - BrowserView Electron ou WebView tag
  - Overlay qui remplace le screenshot quand activé
  - Bouton "Resume Agent" pour revenir au mode auto

- [ ] **Gérer la transition smooth screenshot → WebView**
  ```typescript
  // Mode actuel: Screenshot streaming (img#browser-screenshot)
  // Mode interactif: <webview> ou BrowserView par-dessus
  // Transition CSS: fade-out screenshot, fade-in webview
  ```

- [ ] **État global (Zustand) pour le mode**
  ```typescript
  interface AppState {
    controlMode: 'agent' | 'manual';
    setControlMode: (mode) => void;
  }
  ```

#### **Backend (Python + Playwright)**
- [ ] **Ajouter WebSocket event `pause_agent`**
  - Stopper la boucle d'exécution
  - Sauvegarder l'état actuel (URL, plan, historique)
  - Répondre avec `agent_paused`

- [ ] **Ajouter WebSocket event `resume_agent`**
  - Récupérer observation fraîche (screenshot + URL + AXTree)
  - Réanalyser la situation avec le LLM
  - Créer nouveau plan basé sur le nouvel état
  - Reprendre la boucle d'exécution

- [ ] **Modifier `HybridBrowserAgent`**
  ```python
  class HybridBrowserAgent:
      paused: bool = False
      pause_checkpoint: Dict = None
      
      async def pause(self):
          self.paused = True
          self.pause_checkpoint = {
              'url': self.page.url,
              'plan': self.current_plan,
              'history': self.action_history
          }
      
      async def resume_from_checkpoint(self, observation):
          # Réanalyser avec le LLM
          analysis = await self.analyze_situation(observation)
          new_plan = await self.create_plan(
              self.pause_checkpoint['user_task'],
              observation,
              previous_actions=self.action_history
          )
          self.current_plan = new_plan
          self.paused = False
  ```

#### **Electron Main Process**
- [ ] **Gérer BrowserView pour mode interactif**
  ```javascript
  let interactiveBrowserView = null;
  
  function enableInteractiveMode() {
      // Créer BrowserView attachée à hiddenWindow
      interactiveBrowserView = new BrowserView({...});
      mainWindow.setBrowserView(interactiveBrowserView);
      interactiveBrowserView.setBounds({...});
  }
  
  function disableInteractiveMode() {
      mainWindow.setBrowserView(null);
      interactiveBrowserView.destroy();
  }
  ```

### **Références**
- Electron BrowserView API: https://www.electronjs.org/docs/latest/api/browser-view
- Smooth transitions in React: CSS animations with `react-transition-group`
- Projets similaires:
  - **Playwright Inspector** (mode pas-à-pas)
  - **Selenium IDE** (record/playback avec intervention)
  - **Puppeteer DevTools** (mode debug interactif)

### **Tests à Effectuer**
1. Mode screenshot → clic bouton → webview s'affiche smooth
2. Interaction manuelle (remplir mot de passe, cliquer)
3. Clic "Resume" → agent analyse la nouvelle page → continue
4. Vérifier que le CDP reste connecté pendant la pause

---

## 🎯 PRIORITÉ 2 : INTÉGRATION VLM (VISION-LANGUAGE MODEL)

### **Description**
Utiliser un **modèle de vision** (GPT-4V, Claude 3.5 Sonnet, etc.) pour:
- **Analyser les screenshots** quand Playwright échoue
- **Extraire des informations visuelles** (étoiles GitHub, textes, boutons)
- **Détecter des blocages** (CAPTCHA, erreurs, pages blanches)
- **Fallback intelligent** quand les sélecteurs CSS ne fonctionnent pas

### **Comportement Souhaité**
1. Agent tente action avec Playwright (click, fill, etc.)
2. Si échec OU si aucun changement détecté → **Fallback VLM**
3. VLM analyse le screenshot + donne feedback structuré
4. Agent utilise le feedback pour ajuster sa stratégie

### **Use Cases**
- **GitHub stars** : VLM lit le nombre dans le screenshot
- **CAPTCHA** : VLM détecte → pause agent → demande intervention
- **Erreur 404** : VLM détecte → informe l'utilisateur
- **Bouton invisible** : VLM localise visuellement → donne coordonnées

### **Implémentation Technique**

#### **Backend (Python)**
- [ ] **Créer module `vlm_analyzer.py`**
  ```python
  class VLMAnalyzer:
      def __init__(self, model="gpt-4o-vision"):
          self.client = openai.OpenAI()
          self.model = model
      
      async def analyze_screenshot(
          self, 
          screenshot_base64: str, 
          question: str,
          context: Dict = None
      ) -> Dict[str, Any]:
          """
          Analyse un screenshot avec le VLM.
          
          Args:
              screenshot_base64: Screenshot en base64
              question: "How many stars does this repo have?"
              context: {url, last_action, goal, etc.}
          
          Returns:
              {
                  'answer': "The repo has 65.4k stars",
                  'confidence': 0.95,
                  'extracted_data': {'stars': 65400},
                  'observations': [
                      "GitHub repository page",
                      "Star button visible in top right",
                      "Number displayed: 65.4k"
                  ],
                  'suggested_actions': [
                      "The information has been extracted successfully"
                  ],
                  'blockers': []  # CAPTCHA, error pages, etc.
              }
          """
          
          messages = [
              {
                  "role": "system",
                  "content": VLM_SYSTEM_PROMPT
              },
              {
                  "role": "user",
                  "content": [
                      {"type": "text", "text": self._build_prompt(question, context)},
                      {
                          "type": "image_url",
                          "image_url": {
                              "url": f"data:image/png;base64,{screenshot_base64}",
                              "detail": "high"  # Important pour lire les petits textes
                          }
                      }
                  ]
              }
          ]
          
          response = await self.client.chat.completions.create(
              model=self.model,
              messages=messages,
              max_tokens=1000,
              temperature=0.1
          )
          
          return self._parse_vlm_response(response.choices[0].message.content)
      
      def _build_prompt(self, question, context):
          return f"""You are a web browser analysis expert.

Current Context:
- URL: {context.get('url', 'N/A')}
- User Goal: {context.get('goal', 'N/A')}
- Last Action: {context.get('last_action', 'N/A')}

Question: {question}

Please analyze the screenshot and provide:
1. Direct answer to the question
2. Confidence level (0-1)
3. Extracted data in structured format
4. Visual observations
5. Suggested next actions
6. Any blockers (CAPTCHA, errors, etc.)

Response format (JSON):
{{
  "answer": "...",
  "confidence": 0.95,
  "extracted_data": {{}},
  "observations": [],
  "suggested_actions": [],
  "blockers": []
}}"""
  ```

- [ ] **Intégrer VLM dans `HybridBrowserAgent`**
  ```python
  class HybridBrowserAgent:
      def __init__(self, ...):
          self.vlm = VLMAnalyzer(model="gpt-4o")
          self.vlm_fallback_threshold = 2  # Après 2 échecs, essayer VLM
      
      async def execute_action_with_vlm_fallback(self, action, observation):
          try:
              # Essayer avec Playwright d'abord
              result = await self.execute_playwright_action(action)
              
              # Vérifier si la page a changé
              new_observation = await self.get_rich_observation()
              if self._is_stuck(observation, new_observation):
                  logger.warning("Action seems stuck, trying VLM fallback")
                  return await self._vlm_fallback(action, new_observation)
              
              return result
              
          except Exception as e:
              logger.error(f"Playwright action failed: {e}")
              return await self._vlm_fallback(action, observation)
      
      async def _vlm_fallback(self, failed_action, observation):
          """Utiliser le VLM quand Playwright échoue"""
          
          # Analyser le screenshot
          analysis = await self.vlm.analyze_screenshot(
              screenshot_base64=observation.screenshot_base64,
              question=f"Why did the action '{failed_action}' fail? What do you see on this page?",
              context={
                  'url': observation.url,
                  'goal': self.current_plan.user_task,
                  'last_action': failed_action
              }
          )
          
          # Utiliser les suggestions du VLM
          if analysis['blockers']:
              return {
                  'success': False,
                  'reason': f"Blocker detected: {analysis['blockers']}",
                  'vlm_analysis': analysis,
                  'suggested_action': 'pause_for_user'
              }
          
          if analysis['suggested_actions']:
              return {
                  'success': True,
                  'vlm_guidance': analysis['suggested_actions'][0],
                  'retry_with': analysis['suggested_actions']
              }
          
          return {
              'success': False,
              'reason': analysis['answer']
          }
      
      def _is_stuck(self, old_obs, new_obs):
          """Détecter si l'agent est bloqué"""
          # Comparer URL
          if old_obs.url != new_obs.url:
              return False  # Page a changé, pas bloqué
          
          # Comparer screenshots (hash)
          old_hash = hashlib.md5(old_obs.screenshot_base64.encode()).hexdigest()
          new_hash = hashlib.md5(new_obs.screenshot_base64.encode()).hexdigest()
          
          if old_hash == new_hash:
              return True  # Screenshot identique, peut-être bloqué
          
          return False
  ```

- [ ] **Use case spécifique: Extraction de données**
  ```python
  async def extract_github_stars(self, url, screenshot_base64):
      """Use case: Extraire le nombre d'étoiles GitHub avec VLM"""
      
      analysis = await self.vlm.analyze_screenshot(
          screenshot_base64=screenshot_base64,
          question="How many stars does this GitHub repository have? Extract the exact number.",
          context={'url': url, 'goal': 'Extract star count'}
      )
      
      if analysis['extracted_data'].get('stars'):
          return {
              'success': True,
              'stars': analysis['extracted_data']['stars'],
              'confidence': analysis['confidence']
          }
      
      return {
          'success': False,
          'reason': "Could not extract star count from screenshot"
      }
  ```

#### **Détection Automatique du Besoin de VLM**
- [ ] **Implémenter logique de détection**
  ```python
  def should_use_vlm(self, action_result, iteration_count):
      """Décider si le VLM est nécessaire"""
      
      # Cas 1: Action échoue plusieurs fois
      if action_result['error'] and self._count_failures(action_result['action']) >= 2:
          return True, "repeated_failure"
      
      # Cas 2: Pas de progrès (validation à 0%)
      if iteration_count > 5 and self._get_progress() == 0:
          return True, "no_progress"
      
      # Cas 3: Action d'extraction (stars, prix, etc.)
      if 'extract' in action_result['action'] or 'read' in action_result['action']:
          return True, "extraction_task"
      
      # Cas 4: CAPTCHA/blocage détecté dans les logs
      if 'captcha' in str(action_result).lower() or 'blocked' in str(action_result).lower():
          return True, "captcha_detected"
      
      return False, None
  ```

### **Modèles VLM Supportés**
- [ ] **OpenAI GPT-4o** (vision) - **RECOMMANDÉ**
  - Meilleure qualité OCR
  - Compréhension contextuelle
  - Extraction de données structurées
  
- [ ] **Claude 3.5 Sonnet** (Anthropic)
  - Excellent pour analyse visuelle
  - Bonne extraction de texte
  
- [ ] **Gemini 1.5 Pro** (Google)
  - Gratuit avec quota généreux
  - Bonne performance générale
  
- [ ] **LLaVA / CogVLM** (Open-source)
  - Hébergeable localement
  - Moins performant mais gratuit

### **Coûts et Optimisations**
- [ ] **Cache des screenshots analysés**
  - Éviter d'analyser le même screenshot plusieurs fois
  - Hash MD5 pour identifier les duplicatas

- [ ] **Résolution adaptative**
  - `detail: "low"` pour analyse générale (moins cher)
  - `detail: "high"` pour OCR/extraction précise

- [ ] **Batching**
  - Analyser plusieurs questions dans un seul appel si possible

### **Références**
- **OpenAI Vision API**: https://platform.openai.com/docs/guides/vision
- **Anthropic Claude Vision**: https://docs.anthropic.com/claude/docs/vision
- **Projets similaires**:
  - **WebVoyager** (VLM pour navigation web)
  - **SeeAct** (VLM pour actions sur screenshot)
  - **GPT-4V Web Agent** (Microsoft Research)
  - **LiteWebAgent** (arxiv.org/abs/2503.02950)

### **Tests à Effectuer**
1. VLM extrait correctement le nombre d'étoiles GitHub
2. VLM détecte un CAPTCHA → pause agent
3. VLM suggère alternative quand sélecteur CSS échoue
4. VLM analyse erreur 404 → informe utilisateur
5. Vérifier les coûts (combien d'appels par tâche ?)

---

## 🚀 PRIORITÉ 3 : AMÉLIORATIONS GÉNÉRALES

### **3.1 Extraction de Données Visuelles**
- [ ] Utiliser VLM pour extraire texte, nombres, prix, etc.
- [ ] Fallback automatique quand `innerText` ou sélecteurs échouent

### **3.2 Gestion des CAPTCHAs**
- [ ] Détection automatique (VLM)
- [ ] Pause agent + notification utilisateur
- [ ] Reprendre après résolution manuelle

### **3.3 Mémoire à Long Terme**
- [ ] Sauvegarder les sessions (URL visitées, actions réussies)
- [ ] Apprendre des échecs (sélecteurs qui ne marchent pas)
- [ ] Base de données SQLite locale

### **3.4 Multi-Onglets**
- [ ] Support de plusieurs pages simultanées
- [ ] Agent peut ouvrir/fermer des onglets

### **3.5 UI/UX**
- [ ] Afficher le "thinking" du LLM en temps réel
- [ ] Timeline des actions (avec screenshots miniatures)
- [ ] Logs exportables (JSON, CSV)

### **3.6 Performance**
- [ ] Réduire latence LLM (streaming responses)
- [ ] Cache des plans similaires
- [ ] Parallélisation des observations

---

## 📚 RÉFÉRENCES GLOBALES

### **Projets Open-Source Similaires**
1. **LiteWebAgent** (2025) - arxiv.org/abs/2503.02950
   - VLM + planning + mémoire
2. **Surfer-H** (2024) - arxiv.org/abs/2506.02865
   - Cost-efficient web agent avec VLM
3. **Auto-GPT** - Autonomous agent avec retry logic
4. **BrowserGym** (original) - Observations riches (AXTree, screenshot)

### **Outils et Librairies**
- **Playwright** - Browser automation
- **OpenAI Vision API** - VLM
- **Electron BrowserView** - Embedded browser
- **React Transition Group** - Smooth UI transitions
- **Zustand** - React state management

### **Papers de Recherche**
- "WebVoyager: Building an End-to-End Web Agent"
- "SeeAct: GPT-4V(ision) is a Generalist Web Agent"
- "A Real-World WebAgent with Planning, Long Context Understanding"

---

## 🎯 PRIORITÉ 3 : "TEACH ME HOW TO DO IT" - MACRO RECORDING

### **Description**
Permettre à l'utilisateur d'**enregistrer des parcours web** (workflows) en mode "teaching by demonstration". Ces parcours pourront ensuite être **rejoués automatiquement** par l'agent quand l'utilisateur demande d'exécuter une action similaire.

**Concept :** "Montre-moi comment faire, et je le ferai pour toi"

### **Use Cases**
1. **Authentification** : Enregistrer la séquence de connexion à un site protégé
2. **E-commerce** : Enregistrer un parcours d'achat complet
3. **Formulaires complexes** : Enregistrer le remplissage d'un formulaire multi-étapes
4. **Workflows métier** : Enregistrer des tâches répétitives (ex: export de données, génération de rapports)
5. **Tests automatisés** : Créer des suites de tests sans coder

### **Comportement Souhaité**

#### **Phase 1 : Enregistrement**
```
1. User clique sur onglet "Record Workflow" (nouvelle tab en haut)
   ↓
2. Interface d'enregistrement s'affiche:
   - BrowserView interactif (pleine largeur)
   - Panel de contrôle (en overlay):
     * 🔴 REC indicator (recording actif)
     * ⏸️ Pause
     * ⏹️ Stop & Save
     * 🗑️ Cancel
   ↓
3. User interagit normalement avec le browser:
   - Clics
   - Saisie de texte
   - Navigation
   - Scroll
   - Hover
   ↓
4. Chaque action est capturée en temps réel:
   - Playwright events (click, fill, goto, etc.)
   - VLM screenshots (analyse visuelle du contexte)
   - Metadata (timestamp, URL, selector)
   ↓
5. User clique "Stop & Save":
   - Dialog s'ouvre pour:
     * Nom du workflow (ex: "Login GitHub")
     * Description (ex: "Se connecter avec OAuth")
     * Tags (ex: "authentication", "github")
     * Sélection des actions à garder (editing)
```

#### **Phase 2 : Sauvegarde & Indexation**
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
      "timestamp": 0,
      "screenshot_before": "base64..."
    },
    {
      "type": "click",
      "selector": "button[data-action='click->github-login']",
      "description": "Click 'Sign in with GitHub' button",
      "timestamp": 1500,
      "screenshot_before": "base64...",
      "vlm_context": "The page shows a login form with email and password fields..."
    },
    {
      "type": "fill",
      "selector": "input[name='login']",
      "value": "${USERNAME}", // Variable à remplacer
      "description": "Enter username",
      "timestamp": 3000
    },
    {
      "type": "fill",
      "selector": "input[name='password']",
      "value": "${PASSWORD}", // Variable sensible
      "is_sensitive": true,
      "timestamp": 5000
    },
    {
      "type": "click",
      "selector": "input[type='submit']",
      "description": "Submit login form",
      "timestamp": 7000
    },
    {
      "type": "wait_for_navigation",
      "url_pattern": "https://github.com/*",
      "timestamp": 9000,
      "screenshot_after": "base64..."
    }
  ],
  "variables": [
    {"name": "USERNAME", "type": "string", "required": true},
    {"name": "PASSWORD", "type": "password", "required": true}
  ],
  "success_criteria": {
    "final_url_pattern": "https://github.com/*",
    "expected_element": "avatar.CircleBadge",
    "vlm_validation": "Check if user avatar is visible in top-right corner"
  }
}
```

#### **Phase 3 : Utilisation**
```
User: "Log in to GitHub for me"
   ↓
Agent: 
1. Recherche semantic dans la library de workflows
2. Trouve "Login GitHub" (score de similarité élevé)
3. Demande les variables:
   "I found a workflow for 'Login GitHub'. Please provide:
    - USERNAME: [input field]
    - PASSWORD: [password field]"
4. User fournit les variables
5. Agent exécute le workflow enregistré
6. VLM valide le succès (avatar visible)
7. Agent confirme: "✅ Successfully logged in to GitHub"
```

### **Implémentation Technique**

#### **Frontend (React + Electron)**

##### **1. Nouvel Onglet "Workflows"**
```typescript
// src/renderer/components/WorkflowTab.tsx
interface WorkflowTabProps {
  mode: 'list' | 'record' | 'replay';
}

const WorkflowTab = () => {
  return (
    <div className="workflow-tab">
      <WorkflowList workflows={workflows} />
      <button onClick={startRecording}>+ New Workflow</button>
    </div>
  );
};
```

##### **2. Recorder UI**
```typescript
// src/renderer/components/WorkflowRecorder.tsx
const WorkflowRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [actions, setActions] = useState<RecordedAction[]>([]);
  
  return (
    <div className="recorder-overlay">
      <div className="recorder-controls">
        <span className={isRecording ? 'rec-active' : ''}>🔴 REC</span>
        <button onClick={pause}>⏸️ Pause</button>
        <button onClick={stopAndSave}>⏹️ Stop & Save</button>
        <ActionList actions={actions} />
      </div>
      <BrowserView src="about:blank" />
    </div>
  );
};
```

##### **3. Workflow Library**
```typescript
// src/renderer/components/WorkflowLibrary.tsx
interface Workflow {
  id: string;
  name: string;
  description: string;
  tags: string[];
  actions: Action[];
  last_used?: Date;
  success_rate?: number;
}

const WorkflowLibrary = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [search, setSearch] = useState('');
  
  return (
    <div className="workflow-library">
      <SearchBar value={search} onChange={setSearch} />
      <WorkflowGrid 
        workflows={workflows.filter(w => matchSearch(w, search))} 
        onPlay={playWorkflow}
        onEdit={editWorkflow}
        onDelete={deleteWorkflow}
      />
    </div>
  );
};
```

#### **Backend (Python + Playwright)**

##### **1. Recorder Service**
```python
# python/workflow_recorder.py
import asyncio
from typing import List, Dict, Any
from playwright.async_api import Page

class WorkflowRecorder:
    def __init__(self, page: Page):
        self.page = page
        self.is_recording = False
        self.actions: List[Dict[str, Any]] = []
        self.start_time = None
        self.vlm_enabled = True
    
    async def start_recording(self):
        """Démarrer l'enregistrement des actions"""
        self.is_recording = True
        self.start_time = time.time()
        self.actions = []
        
        # Attacher les listeners Playwright
        self.page.on("console", self._on_console)
        self.page.on("dialog", self._on_dialog)
        self.page.on("framenavigated", self._on_navigation)
        
        # Injecter un script pour capturer les events DOM
        await self.page.add_init_script("""
            window.__recordedActions = [];
            
            // Capturer les clics
            document.addEventListener('click', (e) => {
                window.__recordedActions.push({
                    type: 'click',
                    selector: getSelector(e.target),
                    timestamp: Date.now()
                });
            }, true);
            
            // Capturer les saisies
            document.addEventListener('input', (e) => {
                if (e.target.matches('input, textarea')) {
                    window.__recordedActions.push({
                        type: 'fill',
                        selector: getSelector(e.target),
                        value: e.target.value,
                        timestamp: Date.now()
                    });
                }
            }, true);
            
            // Helper pour générer un selector unique
            function getSelector(element) {
                if (element.id) return `#${element.id}`;
                if (element.name) return `[name="${element.name}"]`;
                // ... logique de fallback
                return element.tagName.toLowerCase();
            }
        """)
        
        logger.info("🔴 Recording started")
    
    async def capture_action(self, action_type: str, **kwargs):
        """Capturer une action manuelle"""
        if not self.is_recording:
            return
        
        timestamp = time.time() - self.start_time
        
        # Prendre screenshot AVANT l'action
        screenshot_before = None
        if self.vlm_enabled:
            screenshot_bytes = await self.page.screenshot()
            screenshot_before = base64.b64encode(screenshot_bytes).decode()
        
        action = {
            'type': action_type,
            'timestamp': timestamp,
            'url': self.page.url,
            'screenshot_before': screenshot_before,
            **kwargs
        }
        
        self.actions.append(action)
        logger.info(f"📝 Captured: {action_type}")
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Arrêter l'enregistrement et retourner le workflow"""
        self.is_recording = False
        
        # Récupérer les actions JS
        js_actions = await self.page.evaluate("window.__recordedActions")
        
        # Merger avec les actions Python
        all_actions = self._merge_actions(self.actions, js_actions)
        
        workflow = {
            'actions': all_actions,
            'duration': time.time() - self.start_time,
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"⏹️ Recording stopped: {len(all_actions)} actions")
        return workflow
```

##### **2. Workflow Player**
```python
# python/workflow_player.py
class WorkflowPlayer:
    def __init__(self, page: Page, vlm_client=None):
        self.page = page
        self.vlm_client = vlm_client
    
    async def play_workflow(
        self, 
        workflow: Dict[str, Any], 
        variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Rejouer un workflow enregistré"""
        variables = variables or {}
        
        logger.info(f"▶️ Playing workflow: {workflow.get('name')}")
        
        for i, action in enumerate(workflow['actions']):
            action_type = action['type']
            
            try:
                if action_type == 'goto':
                    url = self._replace_variables(action['url'], variables)
                    await self.page.goto(url, wait_until='networkidle')
                
                elif action_type == 'click':
                    selector = action['selector']
                    await self.page.click(selector, timeout=5000)
                
                elif action_type == 'fill':
                    selector = action['selector']
                    value = self._replace_variables(action['value'], variables)
                    
                    # Masquer les valeurs sensibles dans les logs
                    if action.get('is_sensitive'):
                        logger.info(f"[{i+1}] fill({selector}, ***)")
                    else:
                        logger.info(f"[{i+1}] fill({selector}, {value})")
                    
                    await self.page.fill(selector, value)
                
                elif action_type == 'wait_for_navigation':
                    pattern = action.get('url_pattern')
                    await self.page.wait_for_url(pattern, timeout=10000)
                
                # Attendre entre les actions (simulate human behavior)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Action {i+1} failed: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'failed_action': i
                }
        
        # Valider le succès
        success = await self._validate_workflow_success(workflow)
        
        return {
            'success': success,
            'actions_executed': len(workflow['actions'])
        }
    
    async def _validate_workflow_success(self, workflow: Dict) -> bool:
        """Valider que le workflow a réussi"""
        criteria = workflow.get('success_criteria', {})
        
        # Check URL pattern
        if 'final_url_pattern' in criteria:
            current_url = self.page.url
            pattern = criteria['final_url_pattern']
            if not re.match(pattern, current_url):
                return False
        
        # Check DOM element
        if 'expected_element' in criteria:
            element = await self.page.query_selector(criteria['expected_element'])
            if not element:
                return False
        
        # VLM validation
        if 'vlm_validation' in criteria and self.vlm_client:
            screenshot = await self.page.screenshot()
            prompt = criteria['vlm_validation']
            response = await self.vlm_client.analyze(screenshot, prompt)
            # Parse response for success/failure
            return 'success' in response.lower()
        
        return True
    
    def _replace_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Remplacer les variables ${VAR} par leurs valeurs"""
        for key, value in variables.items():
            text = text.replace(f"${{{key}}}", value)
        return text
```

##### **3. Workflow Storage**
```python
# python/workflow_storage.py
import json
from pathlib import Path

class WorkflowStorage:
    def __init__(self, storage_dir: str = "./workflows"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_workflow(self, workflow: Dict[str, Any]) -> str:
        """Sauvegarder un workflow"""
        workflow_id = workflow.get('id') or f"wf_{uuid.uuid4().hex[:8]}"
        workflow['id'] = workflow_id
        
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        logger.info(f"💾 Workflow saved: {workflow_id}")
        return workflow_id
    
    def load_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Charger un workflow"""
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """Lister tous les workflows"""
        workflows = []
        
        for file_path in self.storage_dir.glob("*.json"):
            with open(file_path, 'r') as f:
                workflow = json.load(f)
                # Enlever les actions complètes (trop lourd)
                workflow_summary = {
                    'id': workflow['id'],
                    'name': workflow['name'],
                    'description': workflow.get('description', ''),
                    'tags': workflow.get('tags', []),
                    'action_count': len(workflow.get('actions', [])),
                    'created_at': workflow.get('created_at')
                }
                workflows.append(workflow_summary)
        
        return workflows
    
    def search_workflows(self, query: str) -> List[Dict[str, Any]]:
        """Recherche semantique dans les workflows"""
        all_workflows = self.list_workflows()
        
        # Simple keyword matching (améliorer avec embeddings)
        query_lower = query.lower()
        results = []
        
        for wf in all_workflows:
            score = 0
            if query_lower in wf['name'].lower():
                score += 10
            if query_lower in wf.get('description', '').lower():
                score += 5
            for tag in wf.get('tags', []):
                if query_lower in tag.lower():
                    score += 3
            
            if score > 0:
                results.append({'workflow': wf, 'score': score})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['workflow'] for r in results]
```

#### **Electron Main Process**

##### **Navigation Tabs**
```javascript
// main.js - Ajouter support pour les tabs
let currentTab = 'agent'; // 'agent' | 'workflows'

ipcMain.handle('switch-tab', async (event, tabName) => {
  currentTab = tabName;
  
  if (tabName === 'workflows') {
    // Afficher l'interface workflows
    mainWindow.loadFile(path.join(__dirname, 'dist', 'workflows.html'));
  } else {
    // Retour à l'interface agent
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
  
  return { success: true };
});
```

### **Architecture Globale**

```
┌──────────────────────────────────────────────────────┐
│                  ELECTRON WINDOW                      │
├──────────────────────────────────────────────────────┤
│  [Agent 🤖]  [Workflows 📹]  [Settings ⚙️]          │ ← Tabs
├──────────────────────────────────────────────────────┤
│                                                        │
│  MODE: WORKFLOW TAB                                   │
│  ┌────────────────────────────────────────────────┐  │
│  │  Workflow Library                              │  │
│  │  ┌────────────┐  ┌────────────┐              │  │
│  │  │ Login GH   │  │ Buy Item   │  [+ New]    │  │
│  │  │ 5 actions  │  │ 12 actions │              │  │
│  │  │ ▶️ Play    │  │ ▶️ Play    │              │  │
│  │  └────────────┘  └────────────┘              │  │
│  └────────────────────────────────────────────────┘  │
│                                                        │
│  MODE: RECORDING                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  🔴 REC  |  ⏸️ Pause  |  ⏹️ Stop & Save       │  │
│  ├────────────────────────────────────────────────┤  │
│  │                                                 │  │
│  │         [BrowserView - Interactive]            │  │
│  │                                                 │  │
│  │  📝 Actions Recorded: 7                        │  │
│  │  1. goto(github.com)                           │  │
│  │  2. click('Sign in')                           │  │
│  │  3. fill('[name=login]', 'user')              │  │
│  │  ...                                            │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### **Technologies & Stack**

#### **Playwright Features Utilisées**
- **`page.on('*')`** - Event listeners pour capturer toutes les interactions
- **`page.evaluate()`** - Injection de scripts pour capturer events DOM
- **`page.screenshot()`** - Captures visuelles pour VLM
- **`page.context().tracing.start()`** - Enregistrement complet de la session (alternative)

#### **VLM Integration**
- **GPT-4V / GPT-4o** - Analyse visuelle des screenshots
- **Gemini Vision** - Alternative pour validation
- **Claude 3.5 Sonnet** - Analyse contextuelle

#### **Storage & Indexing**
- **Local JSON files** - Stockage simple des workflows
- **SQLite** - Alternative pour queries complexes
- **Vector DB (optional)** - Embeddings pour recherche semantique (Chroma, FAISS)

#### **UI Components**
- **React DnD** - Drag & drop pour réordonner actions
- **Monaco Editor** - Édition de code pour les power users
- **React Flow** - Visualisation graphique des workflows

### **Défis Techniques & Solutions**

#### **1. Sélecteurs fragiles**
**Problème :** Les selectors CSS changent entre les versions de sites

**Solutions :**
- Enregistrer **plusieurs selectors** par élément (CSS, XPath, text content)
- Utiliser **Playwright locators** (plus robustes)
- **VLM fallback** : "Click the button that looks like this [screenshot]"

#### **2. Données sensibles**
**Problème :** Mots de passe, tokens enregistrés

**Solutions :**
- Détecter automatiquement les champs `type="password"`
- Remplacer par des variables `${PASSWORD}`
- **Ne jamais stocker** les valeurs sensibles
- Prompt l'utilisateur à chaque replay

#### **3. Timing & Asynchronisme**
**Problème :** Sites modernes avec chargement asynchrone

**Solutions :**
- Enregistrer les **waits** (wait_for_selector, wait_for_navigation)
- Utiliser **smart waits** de Playwright (auto-waiting)
- **VLM validation** : "Is the page fully loaded?"

#### **4. Variations de contenu**
**Problème :** Contenu dynamique (prix, dates, noms)

**Solutions :**
- Utiliser **regex patterns** au lieu de valeurs exactes
- **VLM extraction** : "Extract the price from this screenshot"
- Variables d'environnement pour données contextuelles

### **Roadmap d'Implémentation**

#### **Phase 1 : MVP (2-3 semaines)**
- [ ] UI de base (onglet Workflows)
- [ ] Recorder simple (Playwright events uniquement)
- [ ] Storage JSON local
- [ ] Player basique (rejouer actions exactes)
- [ ] 3-5 workflows de test

#### **Phase 2 : Robustesse (2-3 semaines)**
- [ ] Multi-selector fallback
- [ ] Variables & paramètres
- [ ] VLM validation basique
- [ ] Edit mode (modifier workflows enregistrés)
- [ ] Import/export workflows

#### **Phase 3 : Intelligence (3-4 semaines)**
- [ ] VLM pour extraction de données
- [ ] Recherche semantique de workflows
- [ ] Auto-suggestions de workflows
- [ ] Workflows conditionnels (if/else)
- [ ] Loops & iterations

#### **Phase 4 : Advanced (4+ semaines)**
- [ ] Workflow marketplace (partage)
- [ ] Analytics (success rate, execution time)
- [ ] A/B testing de workflows
- [ ] Parallel execution
- [ ] Integration avec CI/CD

### **Exemples de Workflows Utiles**

1. **Authentication**
   - Login GitHub / GitLab / LinkedIn
   - OAuth flows
   - 2FA handling

2. **E-commerce**
   - Amazon: Add to cart + checkout
   - eBay: Place bid
   - Product comparison

3. **Data Extraction**
   - Scrape search results
   - Export data to CSV
   - Monitor price changes

4. **Content Creation**
   - Post to social media
   - Schedule emails
   - Generate reports

5. **Testing**
   - E2E test suites
   - Regression testing
   - Performance monitoring

---

## ✅ CRITÈRES DE SUCCÈS

### **Feature 1: Reprise de Contrôle**
- [x] Bouton visible et fonctionnel
- [x] Transition smooth (< 500ms)
- [x] Utilisateur peut interagir normalement
- [x] Agent reprend intelligemment après pause

### **Feature 2: VLM Integration**
- [ ] VLM extrait correctement les informations (précision > 90%)
- [ ] Détection automatique des blocages
- [ ] Coût raisonnable (< $0.10 par tâche complexe)
- [ ] Fallback fonctionne sans intervention

### **Feature 3: Macro Recording**
- [ ] Enregistrement d'actions utilisateur fluide (< 50ms latency)
- [ ] Storage local avec recherche rapide (< 100ms)
- [ ] Replay précis (taux de succès > 85%)
- [ ] Détection automatique de variables sensibles
- [ ] UI intuitive (utilisable sans documentation)

---

**PRÊT À COMMENCER L'IMPLÉMENTATION ! 🚀**
