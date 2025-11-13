# 📋 FEATURE 3 : TEACH ME HOW TO DO IT - PLAN D'IMPLÉMENTATION MVP

**Date:** 13 Novembre 2025  
**Timeline:** 5-7 jours  
**Status:** 🟢 Ready to start

---

## 🎯 CHOIX STRATÉGIQUES VALIDÉS

| Aspect | Choix | Justification |
|--------|-------|---------------|
| **Use Case** | Navigation simple | Le plus rapide pour MVP, fondation solide |
| **UI** | Option B - Minimal propre | Onglet séparé + liste + recorder |
| **VLM** | Option D - Pas dans MVP | On l'ajoute en Phase 2 |
| **Storage** | Option A - JSON local | Simple, pas de dépendances |
| **Integration** | Bouton sous prompt | Accès rapide aux workflows |

---

## 🏗️ ARCHITECTURE TECHNIQUE

```
┌────────────────────────────────────────────────┐
│           ELECTRON WINDOW                      │
├────────────────────────────────────────────────┤
│  [Agent 🤖]  [Workflows 📹]                   │ ← Tabs
├────────────────────────────────────────────────┤
│                                                │
│  TAB: WORKFLOWS                                │
│  ┌──────────────────────────────────────────┐ │
│  │  📹 Workflows Library                    │ │
│  │                                          │ │
│  │  [🎬 New Recording]                      │ │
│  │                                          │ │
│  │  ┌─────────────┐  ┌─────────────┐      │ │
│  │  │ Workflow 1  │  │ Workflow 2  │      │ │
│  │  │ 5 actions   │  │ 8 actions   │      │ │
│  │  │ ▶️ Play     │  │ ▶️ Play     │      │ │
│  │  └─────────────┘  └─────────────┘      │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  TAB: AGENT (avec dropdown workflows)         │
│  ┌──────────────────────────────────────────┐ │
│  │  Chat messages...                        │ │
│  └──────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────┐ │
│  │  [▼ Select workflow]  [▶️ Play]          │ │ ← NOUVEAU
│  │  [Type your message...]  [Send]          │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

---

## 📦 STRUCTURE DES FICHIERS

```
browsergym-electron/
├── python/
│   ├── workflow_recorder.py      ✨ NOUVEAU
│   ├── workflow_player.py        ✨ NOUVEAU
│   ├── workflow_storage.py       ✨ NOUVEAU
│   └── browsergym_server.py      📝 MODIFIÉ (+ WebSocket events)
│
├── workflows/                     ✨ NOUVEAU (folder pour JSON)
│   └── .gitkeep
│
├── src/renderer/
│   ├── components/
│   │   ├── WorkflowTab.tsx       ✨ NOUVEAU
│   │   ├── WorkflowRecorder.tsx  ✨ NOUVEAU
│   │   ├── WorkflowList.tsx      ✨ NOUVEAU
│   │   ├── WorkflowCard.tsx      ✨ NOUVEAU
│   │   ├── WorkflowDropdown.tsx  ✨ NOUVEAU
│   │   └── ChatPanel.tsx         📝 MODIFIÉ (+ dropdown)
│   │
│   ├── hooks/
│   │   ├── useWorkflows.ts       ✨ NOUVEAU
│   │   └── useBrowserGym.ts      📝 MODIFIÉ
│   │
│   └── types.ts                   📝 MODIFIÉ (+ Workflow types)
│
└── main.js                        📝 MODIFIÉ (+ tab switching)
```

---

## 🚀 PHASE 1 : BACKEND - RECORDER (Jour 1)

### **1.1 - WorkflowRecorder.py**

```python
# browsergym-electron/python/workflow_recorder.py

import time
import logging
from typing import List, Dict, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class WorkflowRecorder:
    """
    Enregistre les actions utilisateur en temps réel
    MVP: clicks, navigation, fill (pas de scroll/hover)
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.is_recording = False
        self.actions: List[Dict[str, Any]] = []
        self.start_time = None
        self.start_url = None
    
    async def start_recording(self) -> None:
        """Démarrer l'enregistrement"""
        logger.info("🎬 Starting workflow recording...")
        
        self.is_recording = True
        self.start_time = time.time()
        self.start_url = self.page.url
        self.actions = []
        
        # Injecter script pour capturer events DOM
        await self.page.add_init_script("""
            window.__workflowActions = [];
            
            // Helper: générer selector robuste
            function getSelector(element) {
                // Priorité: ID > Name > Class + Tag
                if (element.id) {
                    return '#' + element.id;
                }
                if (element.name) {
                    return `[name="${element.name}"]`;
                }
                
                const tag = element.tagName.toLowerCase();
                const classes = element.className ? '.' + element.className.split(' ').join('.') : '';
                return tag + classes;
            }
            
            // Capturer les CLICS
            document.addEventListener('click', (e) => {
                const selector = getSelector(e.target);
                window.__workflowActions.push({
                    type: 'click',
                    selector: selector,
                    text: e.target.innerText?.substring(0, 50) || '',
                    timestamp: Date.now()
                });
                console.log('📝 Captured click:', selector);
            }, true);
            
            // Capturer les SAISIES (input/textarea)
            document.addEventListener('input', (e) => {
                if (e.target.matches('input, textarea')) {
                    const selector = getSelector(e.target);
                    window.__workflowActions.push({
                        type: 'fill',
                        selector: selector,
                        value: e.target.value,
                        timestamp: Date.now()
                    });
                    console.log('📝 Captured fill:', selector);
                }
            }, true);
        """)
        
        # Capturer les navigations
        self.page.on("framenavigated", self._on_navigation)
        
        logger.info("✅ Recording started")
    
    def _on_navigation(self, frame):
        """Callback pour les navigations"""
        if not self.is_recording or not frame.parent_frame:
            return
        
        url = frame.url
        timestamp = (time.time() - self.start_time) * 1000
        
        self.actions.append({
            'type': 'goto',
            'url': url,
            'timestamp': timestamp
        })
        
        logger.info(f"📝 Captured navigation: {url}")
    
    async def stop_recording(self) -> Dict[str, Any]:
        """Arrêter et retourner le workflow"""
        logger.info("⏹️ Stopping recording...")
        
        self.is_recording = False
        
        # Récupérer les actions JS
        try:
            js_actions = await self.page.evaluate("window.__workflowActions || []")
        except Exception as e:
            logger.error(f"Failed to get JS actions: {e}")
            js_actions = []
        
        # Merger et trier par timestamp
        all_actions = self.actions + js_actions
        all_actions.sort(key=lambda x: x.get('timestamp', 0))
        
        # Nettoyer les doublons de fill (garder le dernier)
        cleaned_actions = self._deduplicate_fills(all_actions)
        
        workflow = {
            'name': f"Workflow {int(time.time())}",  # Nom temporaire
            'description': '',
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'start_url': self.start_url,
            'actions': cleaned_actions,
            'duration': time.time() - self.start_time
        }
        
        logger.info(f"✅ Recording stopped: {len(cleaned_actions)} actions")
        
        # Détacher les listeners
        self.page.remove_listener("framenavigated", self._on_navigation)
        
        return workflow
    
    def _deduplicate_fills(self, actions: List[Dict]) -> List[Dict]:
        """Garder uniquement le dernier fill pour chaque champ"""
        seen_selectors = {}
        result = []
        
        for action in actions:
            if action['type'] == 'fill':
                selector = action['selector']
                # Remplacer si déjà vu
                if selector in seen_selectors:
                    result[seen_selectors[selector]] = action
                else:
                    seen_selectors[selector] = len(result)
                    result.append(action)
            else:
                result.append(action)
        
        return result
```

### **1.2 - WorkflowStorage.py**

```python
# browsergym-electron/python/workflow_storage.py

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WorkflowStorage:
    """
    Stockage local des workflows (JSON files)
    MVP: Simple file storage, pas de DB
    """
    
    def __init__(self, storage_dir: str = "./workflows"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Workflow storage: {self.storage_dir.absolute()}")
    
    def save(self, workflow: Dict[str, Any], workflow_id: Optional[str] = None) -> str:
        """Sauvegarder un workflow"""
        if not workflow_id:
            workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        
        workflow['id'] = workflow_id
        
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Workflow saved: {workflow_id}")
        return workflow_id
    
    def load(self, workflow_id: str) -> Dict[str, Any]:
        """Charger un workflow"""
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_id}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """Lister tous les workflows (summary uniquement)"""
        workflows = []
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    
                    # Summary uniquement (pas les actions complètes)
                    summary = {
                        'id': workflow.get('id'),
                        'name': workflow.get('name', 'Untitled'),
                        'description': workflow.get('description', ''),
                        'created_at': workflow.get('created_at'),
                        'action_count': len(workflow.get('actions', [])),
                        'duration': workflow.get('duration', 0),
                        'start_url': workflow.get('start_url', '')
                    }
                    workflows.append(summary)
            
            except Exception as e:
                logger.error(f"Failed to load workflow {file_path}: {e}")
        
        # Trier par date de création (plus récent d'abord)
        workflows.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return workflows
    
    def delete(self, workflow_id: str) -> bool:
        """Supprimer un workflow"""
        file_path = self.storage_dir / f"{workflow_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️ Workflow deleted: {workflow_id}")
            return True
        
        return False
    
    def update_metadata(self, workflow_id: str, name: str = None, description: str = None) -> bool:
        """Mettre à jour les métadonnées d'un workflow"""
        try:
            workflow = self.load(workflow_id)
            
            if name:
                workflow['name'] = name
            if description:
                workflow['description'] = description
            
            self.save(workflow, workflow_id)
            logger.info(f"✏️ Workflow updated: {workflow_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update workflow: {e}")
            return False
```

---

## 🎮 PHASE 2 : BACKEND - PLAYER (Jour 2)

### **2.1 - WorkflowPlayer.py**

```python
# browsergym-electron/python/workflow_player.py

import asyncio
import logging
from typing import Dict, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class WorkflowPlayer:
    """
    Rejoue un workflow enregistré
    MVP: goto, click, fill (pas de variables pour l'instant)
    """
    
    def __init__(self, page: Page):
        self.page = page
    
    async def play(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Rejouer un workflow complet"""
        workflow_name = workflow.get('name', 'Unknown')
        actions = workflow.get('actions', [])
        
        logger.info(f"▶️ Playing workflow: {workflow_name} ({len(actions)} actions)")
        
        results = {
            'success': True,
            'actions_executed': 0,
            'actions_failed': 0,
            'errors': []
        }
        
        for i, action in enumerate(actions):
            action_type = action.get('type')
            
            try:
                logger.info(f"[{i+1}/{len(actions)}] {action_type}")
                
                if action_type == 'goto':
                    await self._execute_goto(action)
                
                elif action_type == 'click':
                    await self._execute_click(action)
                
                elif action_type == 'fill':
                    await self._execute_fill(action)
                
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                
                results['actions_executed'] += 1
                
                # Petit délai entre actions (human-like)
                await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.error(f"❌ Action {i+1} failed: {e}")
                results['actions_failed'] += 1
                results['errors'].append({
                    'action_index': i,
                    'action': action,
                    'error': str(e)
                })
                
                # Continuer ou arrêter ?
                if results['actions_failed'] >= 3:
                    logger.error("Too many failures, stopping workflow")
                    results['success'] = False
                    break
        
        if results['success']:
            logger.info(f"✅ Workflow completed: {results['actions_executed']} actions")
        else:
            logger.error(f"❌ Workflow failed: {results['actions_failed']} errors")
        
        return results
    
    async def _execute_goto(self, action: Dict[str, Any]):
        """Exécuter une navigation"""
        url = action.get('url')
        
        if not url:
            raise ValueError("Missing URL for goto action")
        
        await self.page.goto(url, wait_until='networkidle', timeout=30000)
        logger.info(f"  → Navigated to: {url}")
    
    async def _execute_click(self, action: Dict[str, Any]):
        """Exécuter un clic"""
        selector = action.get('selector')
        
        if not selector:
            raise ValueError("Missing selector for click action")
        
        # Essayer plusieurs stratégies
        try:
            # Stratégie 1: Selector direct
            await self.page.click(selector, timeout=5000)
            logger.info(f"  → Clicked: {selector}")
        
        except Exception as e1:
            # Stratégie 2: Recherche par texte si disponible
            text = action.get('text', '').strip()
            if text:
                try:
                    await self.page.get_by_text(text).first.click(timeout=5000)
                    logger.info(f"  → Clicked by text: {text}")
                    return
                except Exception as e2:
                    pass
            
            # Échec
            raise e1
    
    async def _execute_fill(self, action: Dict[str, Any]):
        """Exécuter un remplissage de champ"""
        selector = action.get('selector')
        value = action.get('value', '')
        
        if not selector:
            raise ValueError("Missing selector for fill action")
        
        # Clear puis fill
        await self.page.fill(selector, '', timeout=5000)
        await self.page.fill(selector, value, timeout=5000)
        
        # Log masqué si c'est un password
        if 'password' in selector.lower():
            logger.info(f"  → Filled: {selector} (***)")
        else:
            logger.info(f"  → Filled: {selector} = '{value[:20]}...'")
```

---

## 🔌 PHASE 3 : BACKEND - WEBSOCKET INTEGRATION (Jour 2)

### **3.1 - Modifier browsergym_server.py**

```python
# Ajouter en haut du fichier
from workflow_recorder import WorkflowRecorder
from workflow_player import WorkflowPlayer
from workflow_storage import WorkflowStorage

class BrowserGymServer:
    def __init__(self, ...):
        # ... existing code ...
        
        # NOUVEAU: Workflow management
        self.workflow_recorder = None
        self.workflow_player = None
        self.workflow_storage = WorkflowStorage()
    
    async def handle_client(self, websocket, path):
        # ... existing message routing ...
        
        # NOUVEAU: Workflow events
        elif msg_type == 'start_recording':
            response = await self.handle_start_recording()
        
        elif msg_type == 'stop_recording':
            response = await self.handle_stop_recording(data.get('metadata', {}))
        
        elif msg_type == 'list_workflows':
            response = await self.handle_list_workflows()
        
        elif msg_type == 'play_workflow':
            response = await self.handle_play_workflow(data.get('workflow_id'))
        
        elif msg_type == 'delete_workflow':
            response = await self.handle_delete_workflow(data.get('workflow_id'))
    
    async def handle_start_recording(self):
        """Démarrer l'enregistrement d'un workflow"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Page not initialized'}
            
            if self.workflow_recorder and self.workflow_recorder.is_recording:
                return {'type': 'error', 'error': 'Already recording'}
            
            self.workflow_recorder = WorkflowRecorder(self.page)
            await self.workflow_recorder.start_recording()
            
            return {
                'type': 'recording_started',
                'message': '🎬 Recording started'
            }
        
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_stop_recording(self, metadata: dict):
        """Arrêter l'enregistrement et sauvegarder"""
        try:
            if not self.workflow_recorder or not self.workflow_recorder.is_recording:
                return {'type': 'error', 'error': 'Not recording'}
            
            # Arrêter et récupérer le workflow
            workflow = await self.workflow_recorder.stop_recording()
            
            # Appliquer metadata (name, description)
            workflow['name'] = metadata.get('name', workflow['name'])
            workflow['description'] = metadata.get('description', '')
            
            # Sauvegarder
            workflow_id = self.workflow_storage.save(workflow)
            
            return {
                'type': 'recording_stopped',
                'data': {
                    'workflow_id': workflow_id,
                    'name': workflow['name'],
                    'action_count': len(workflow['actions'])
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_list_workflows(self):
        """Lister tous les workflows"""
        try:
            workflows = self.workflow_storage.list_all()
            
            return {
                'type': 'workflows_list',
                'data': {'workflows': workflows}
            }
        
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_play_workflow(self, workflow_id: str):
        """Rejouer un workflow"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Page not initialized'}
            
            if not workflow_id:
                return {'type': 'error', 'error': 'Missing workflow_id'}
            
            # Charger le workflow
            workflow = self.workflow_storage.load(workflow_id)
            
            # Créer player et exécuter
            self.workflow_player = WorkflowPlayer(self.page)
            results = await self.workflow_player.play(workflow)
            
            return {
                'type': 'workflow_completed',
                'data': results
            }
        
        except FileNotFoundError:
            return {'type': 'error', 'error': f'Workflow not found: {workflow_id}'}
        
        except Exception as e:
            logger.error(f"Failed to play workflow: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_delete_workflow(self, workflow_id: str):
        """Supprimer un workflow"""
        try:
            success = self.workflow_storage.delete(workflow_id)
            
            return {
                'type': 'workflow_deleted',
                'data': {'workflow_id': workflow_id, 'success': success}
            }
        
        except Exception as e:
            logger.error(f"Failed to delete workflow: {e}")
            return {'type': 'error', 'error': str(e)}
```

**C'est parti ! Je commence par créer les fichiers backend. Dis-moi si tu veux que je continue ou si tu as des questions ! 🚀**
