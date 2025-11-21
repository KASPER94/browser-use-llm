#!/usr/bin/env python3
"""
WorkflowRecorder - Enregistre les actions utilisateur en temps réel
MVP: clicks, navigation, fill (pas de scroll/hover)
"""

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
                // Priorité 1: ID (le plus stable)
                if (element.id) {
                    return '#' + element.id;
                }
                
                // Priorité 2: Attribut name
                if (element.name) {
                    return `[name="${element.name}"]`;
                }
                
                const tag = element.tagName.toLowerCase();
                
                // Priorité 3: Classes
                const classes = element.className ? '.' + element.className.trim().split(/\\s+/).join('.') : '';
                if (classes && classes.length < 50) { // Eviter les classes trop longues/dynamiques
                    return tag + classes;
                }
                
                // Priorité 4: Full Path (Fallback)
                try {
                  let path = tag;
                  let current = element;
                  while (current.parentElement && current.parentElement !== document.body) {
                    current = current.parentElement;
                    const parentTag = current.tagName.toLowerCase();
                    const siblings = Array.from(current.children);
                    
                    // Ajouter index si nécessaire
                    const sameTagSiblings = siblings.filter(s => s.tagName.toLowerCase() === element.tagName.toLowerCase());
                    if (sameTagSiblings.length > 1) {
                       const sameTagIndex = sameTagSiblings.indexOf(element) + 1;
                       path = \`\${parentTag} > \${tag}:nth-of-type(\${sameTagIndex})\`;
                    } else {
                       path = \`\${parentTag} > \${tag}\`;
                    }
                    
                    if (current.id) {
                       path = \`#\${current.id} > \${path}\`;
                       return path;
                    }
                    break; 
                  }
                  return path;
                } catch (e) {
                  return tag;
                }
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
        if not self.is_recording or frame.parent_frame:
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
        try:
            self.page.remove_listener("framenavigated", self._on_navigation)
        except Exception as e:
            logger.warning(f"Failed to remove listener: {e}")
        
        return workflow
    
    def _deduplicate_fills(self, actions: List[Dict]) -> List[Dict]:
        """Garder uniquement le dernier fill pour chaque champ"""
        seen_selectors = {}
        result = []
        
        for action in actions:
            if action.get('type') == 'fill':
                selector = action.get('selector')
                # Remplacer si déjà vu
                if selector in seen_selectors:
                    result[seen_selectors[selector]] = action
                else:
                    seen_selectors[selector] = len(result)
                    result.append(action)
            else:
                result.append(action)
        
        return result
