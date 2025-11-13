#!/usr/bin/env python3
"""
WorkflowPlayer - Rejoue un workflow enregistré
MVP: goto, click, fill (pas de variables pour l'instant)
"""

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
            display_value = value[:20] + '...' if len(value) > 20 else value
            logger.info(f"  → Filled: {selector} = '{display_value}'")

