#!/usr/bin/env python3
"""
BrowserGym WebSocket Server pour Electron - SCREENSHOT STREAMING
Fait le pont entre l'interface Electron et BrowserGym
"""

import asyncio
import json
import logging
import argparse
import base64
from typing import Optional, Dict, Any, List
import websockets
from websockets.server import serve, WebSocketServerProtocol

# Ajouter le répertoire python au PYTHONPATH pour import local
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from browsergym.core.action.highlevel import HighLevelActionSet
    from electron_browser_env import connect_to_electron_browser_async
    from demo_agent_adapter import ElectronDemoAgent
    from hybrid_agent import HybridBrowserAgent
    from workflow_recorder import WorkflowRecorder
    from workflow_storage import WorkflowStorage
    from workflow_player import WorkflowPlayer  # NOUVEAU
    BROWSERGYM_AVAILABLE = True
    print("✓ BrowserGym loaded successfully")
except ImportError as e:
    BROWSERGYM_AVAILABLE = False
    print(f"✗ Warning: BrowserGym not available: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BrowserGymServer:
    """Serveur WebSocket pour BrowserGym"""
    
    def __init__(self, cdp_port: int = 9222, ws_port: int = 8765, use_llm: bool = True, use_hybrid: bool = True):
        self.cdp_port = cdp_port
        self.ws_port = ws_port
        self.browser = None
        self.context = None
        self.page = None
        self.clients: set = set()
        self.agent_busy = False
        self.screenshot_task = None
        self.streaming_active = False
        
        # Choix de l'agent
        self.use_hybrid = use_hybrid and BROWSERGYM_AVAILABLE
        self.use_llm = use_llm and BROWSERGYM_AVAILABLE
        self.hybrid_agent = None
        self.llm_agent = None
        
        # NOUVEAU: Workflow recording
        self.workflow_recorder: Optional[WorkflowRecorder] = None
        self.workflow_storage = WorkflowStorage() if BROWSERGYM_AVAILABLE else None
        self.is_recording = False
        
        if self.use_hybrid:
            try:
                self.hybrid_agent = HybridBrowserAgent(model_name="gpt-4o-mini", max_iterations=30)
                logger.info("✅ Hybrid Agent initialized (BrowserGym + BrowserOS)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize hybrid agent: {e}")
                self.use_hybrid = False
        
        if not self.use_hybrid and self.use_llm:
            try:
                self.llm_agent = ElectronDemoAgent(model_name="gpt-4o-mini")
                logger.info("✅ LLM Agent initialized (simple)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize LLM agent: {e}")
                self.use_llm = False
        
    async def initialize_env(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialiser l'environnement BrowserGym"""
        try:
            if not BROWSERGYM_AVAILABLE:
                logger.warning("BrowserGym not available, running in demo mode")
                return {
                    'type': 'init_complete',
                    'data': {
                        'viewport': config.get('viewport', {'width': 1024, 'height': 768}),
                        'ready': True,
                        'demo_mode': True
                    }
                }
            
            logger.info("Initializing BrowserGym environment in Electron mode...")
            cdp_url = f"http://localhost:{self.cdp_port}"
            logger.info(f"CDP URL: {cdp_url}")
            
            # Utiliser la fonction async pour se connecter
            self.browser, self.context, self.page = await connect_to_electron_browser_async(cdp_url)
            
            logger.info("Environment initialized successfully")
            logger.info(f"Page URL: {self.page.url}")
            
            # Démarrer le streaming de screenshots
            self.start_screenshot_streaming()
            
            return {
                'type': 'init_complete',
                'data': {
                    'viewport': config.get('viewport'),
                    'ready': True
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize environment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'type': 'error',
                'error': str(e)
            }
    
    async def handle_user_message(self, message: str) -> Dict[str, Any]:
        """Traiter un message utilisateur"""
        try:
            logger.info(f"User message: {message}")
            self.agent_busy = True

            # Mode démo (sans BrowserGym)
            if not BROWSERGYM_AVAILABLE or not self.page:
                await asyncio.sleep(0.5)
                self.agent_busy = False
                return {
                    'type': 'agent_message',
                    'message': f"🤖 Received: '{message}'\n\nPlaywright est connecté !"
                }

            # ===== HYBRID AGENT (BrowserGym + BrowserOS) =====
            if self.use_hybrid and self.hybrid_agent:
                logger.info(f"🎯 Using Hybrid Agent (Planning + Rich Observations)")
                
                try:
                    # BOUCLE D'EXÉCUTION : continuer jusqu'à ce que le plan soit vide ou max_iterations
                    max_actions_per_message = 10  # Sécurité pour éviter boucles infinies
                    actions_executed = 0
                    all_responses = []
                    
                    while actions_executed < max_actions_per_message:
                        # Get rich observation
                        observation = await self.hybrid_agent.get_rich_observation(self.page)
                        
                        # Besoin de plan ?
                        if self.hybrid_agent.should_replan(observation):
                            plan = await self.hybrid_agent.create_plan(message, observation)
                            self.hybrid_agent.current_plan = plan
                            
                            # Envoyer le raisonnement au frontend (une seule fois)
                            if actions_executed == 0:
                                await self.broadcast({
                                    'type': 'agent_thinking',
                                    'data': {
                                        'reasoning': plan.step_by_step_reasoning,
                                        'actions_planned': len(plan.proposed_actions)
                                    }
                                })
                        
                        # Vérifier si le plan est terminé
                        if not self.hybrid_agent.current_plan or not self.hybrid_agent.current_plan.proposed_actions:
                            if actions_executed == 0:
                                response_message = "🤔 No actions to execute, task might be complete."
                            break
                        
                        # Exécuter la prochaine action du plan
                        next_step = self.hybrid_agent.current_plan.proposed_actions.pop(0)
                        action_str = next_step['action']
                        reasoning = next_step['reasoning']
                        
                        logger.info(f"📌 [{actions_executed+1}] Executing: {action_str}")
                        logger.info(f"💭 Reasoning: {reasoning}")
                        
                        # Parser et exécuter l'action
                        action_result = ""
                        import re
                        
                        # === GOTO ===
                        if 'goto' in action_str.lower():
                            url_match = re.search(r'goto\(["\'](.+?)["\']\)', action_str)
                            if url_match:
                                url = url_match.group(1)
                                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                                action_result = f"✅ [{actions_executed+1}] Navigated to {url}\n💭 {reasoning}"
                            else:
                                action_result = f"⚠️ Could not parse URL from: {action_str}"
                        
                        # === FILL ===
                        elif 'fill' in action_str.lower():
                            # Formats possibles :
                            # fill('selector', 'text')
                            # fill("selector", "text")
                            # fill('field name', 'text')
                            fill_match = re.search(r'fill\(["\'](.+?)["\']\s*,\s*["\'](.+?)["\']\)', action_str)
                            if fill_match:
                                selector = fill_match.group(1)
                                text = fill_match.group(2)
                                
                                try:
                                    # Essayer plusieurs stratégies pour trouver le champ
                                    # IMPORTANT: Tester input ET textarea !
                                    
                                    # 1. Sélecteur CSS direct
                                    if await self.page.locator(selector).count() > 0:
                                        await self.page.fill(selector, text, timeout=5000)
                                        # Presser Enter automatiquement pour les champs de recherche
                                        await self.page.press(selector, 'Enter', timeout=1000)
                                        action_result = f"✅ [{actions_executed+1}] Filled '{selector}' with '{text}' and pressed Enter\n💭 {reasoning}"
                                    
                                    # 2. Sélecteur générique [name="..."] (fonctionne pour input ET textarea)
                                    elif 'name=' in selector:
                                        # Extraire le nom: input[name="q"] → q
                                        name_match = re.search(r'name\s*=\s*["\']?(\w+)["\']?', selector)
                                        if name_match:
                                            field_name = name_match.group(1)
                                            generic_selector = f'[name="{field_name}"]'
                                            if await self.page.locator(generic_selector).count() > 0:
                                                await self.page.fill(generic_selector, text, timeout=5000)
                                                # Presser Enter automatiquement
                                                try:
                                                    await self.page.press(generic_selector, 'Enter', timeout=1000)
                                                    action_result = f"✅ [{actions_executed+1}] Filled [name=\"{field_name}\"] with '{text}' and pressed Enter\n💭 {reasoning}"
                                                except:
                                                    action_result = f"✅ [{actions_executed+1}] Filled [name=\"{field_name}\"] with '{text}'\n💭 {reasoning}"
                                            else:
                                                action_result = f"❌ [{actions_executed+1}] Field [name=\"{field_name}\"] not found\n💭 {reasoning}"
                                        else:
                                            action_result = f"❌ [{actions_executed+1}] Could not parse name from '{selector}'\n💭 {reasoning}"
                                    
                                    # 3. Recherche par placeholder (input ET textarea)
                                    elif await self.page.locator(f'input[placeholder*="{selector}" i], textarea[placeholder*="{selector}" i]').count() > 0:
                                        await self.page.fill(f'input[placeholder*="{selector}" i], textarea[placeholder*="{selector}" i]', text, timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Filled field (placeholder: '{selector}') with '{text}'\n💭 {reasoning}"
                                    
                                    # 4. Recherche par name (input ET textarea)
                                    elif await self.page.locator(f'input[name*="{selector}" i], textarea[name*="{selector}" i]').count() > 0:
                                        await self.page.fill(f'input[name*="{selector}" i], textarea[name*="{selector}" i]', text, timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Filled field (name: '{selector}') with '{text}'\n💭 {reasoning}"
                                    
                                    # 5. Recherche par aria-label (input ET textarea)
                                    elif await self.page.locator(f'input[aria-label*="{selector}" i], textarea[aria-label*="{selector}" i]').count() > 0:
                                        await self.page.fill(f'input[aria-label*="{selector}" i], textarea[aria-label*="{selector}" i]', text, timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Filled field (aria-label: '{selector}') with '{text}'\n💭 {reasoning}"
                                    
                                    # 6. Recherche générique par attribut name (dernier recours)
                                    elif await self.page.locator(f'[name*="{selector}" i]').count() > 0:
                                        await self.page.fill(f'[name*="{selector}" i]', text, timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Filled field with name containing '{selector}' with '{text}'\n💭 {reasoning}"
                                    
                                    else:
                                        action_result = f"❌ [{actions_executed+1}] Could not find field '{selector}'\n💭 {reasoning}"
                                
                                except Exception as e:
                                    action_result = f"❌ [{actions_executed+1}] Fill error: {str(e)}\n💭 {reasoning}"
                            else:
                                action_result = f"⚠️ Could not parse fill action from: {action_str}"
                        
                        # === CLICK ===
                        elif 'click' in action_str.lower():
                            # Formats possibles :
                            # click('selector')
                            # click("button text")
                            click_match = re.search(r'click\(["\'](.+?)["\']\)', action_str)
                            if click_match:
                                selector = click_match.group(1)
                                
                                try:
                                    # Essayer plusieurs stratégies
                                    # 1. Sélecteur CSS direct
                                    if await self.page.locator(selector).count() > 0:
                                        await self.page.click(selector, timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Clicked '{selector}'\n💭 {reasoning}"
                                    
                                    # 2. Recherche par texte
                                    elif await self.page.get_by_text(selector).count() > 0:
                                        await self.page.get_by_text(selector).first.click(timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Clicked element with text '{selector}'\n💭 {reasoning}"
                                    
                                    # 3. Recherche par role + name
                                    elif await self.page.get_by_role("button", name=re.compile(selector, re.IGNORECASE)).count() > 0:
                                        await self.page.get_by_role("button", name=re.compile(selector, re.IGNORECASE)).first.click(timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Clicked button '{selector}'\n💭 {reasoning}"
                                    
                                    # 4. Recherche par aria-label
                                    elif await self.page.locator(f'[aria-label*="{selector}" i]').count() > 0:
                                        await self.page.locator(f'[aria-label*="{selector}" i]').first.click(timeout=5000)
                                        action_result = f"✅ [{actions_executed+1}] Clicked element (aria-label: '{selector}')\n💭 {reasoning}"
                                    
                                    else:
                                        action_result = f"❌ [{actions_executed+1}] Could not find clickable element '{selector}'\n💭 {reasoning}"
                                
                                except Exception as e:
                                    action_result = f"❌ [{actions_executed+1}] Click error: {str(e)}\n💭 {reasoning}"
                            else:
                                action_result = f"⚠️ Could not parse click action from: {action_str}"
                        
                        # === SEND_MSG_TO_USER / MESSAGE ===
                        elif 'send_msg_to_user' in action_str.lower() or (action_str.startswith('message') or action_str.startswith('MESSAGE')):
                            # Extraire le message
                            msg_match = re.search(r'["\'](.+?)["\']', action_str)
                            if msg_match:
                                user_message = msg_match.group(1)
                                action_result = f"💬 [{actions_executed+1}] {user_message}\n💭 {reasoning}"
                            else:
                                action_result = f"💬 [{actions_executed+1}] Message action\n💭 {reasoning}"
                        
                        # === DONE ===
                        elif 'done' in action_str.lower():
                            final_msg = self.hybrid_agent.current_plan.final_answer if self.hybrid_agent.current_plan else "Task completed"
                            action_result = f"✅ Task complete!\n\n{final_msg}"
                            all_responses.append(action_result)
                            break  # Terminer la boucle
                        
                        # === READ / EXTRACT (actions informatives) ===
                        elif 'read' in action_str.lower() or 'extract' in action_str.lower():
                            # Ces actions nécessitent du scraping, pour l'instant on les simule
                            action_result = f"📖 [{actions_executed+1}] Action '{action_str}' requires page scraping (not yet implemented)\n💭 {reasoning}"
                        
                        # === UNKNOWN ===
                        else:
                            action_result = f"⚠️ [{actions_executed+1}] Unknown action type: '{action_str}'\n💭 {reasoning}"
                        
                        all_responses.append(action_result)
                        
                        # Envoyer un message intermédiaire au frontend
                        await self.broadcast({
                            'type': 'agent_message',
                            'message': action_result
                        })
                        
                        # Enregistrer l'action avec son résultat (succès ou erreur)
                        action_error = None
                        if "❌" in action_result or "⚠️" in action_result:
                            action_error = action_result
                        
                        self.hybrid_agent.action_history.append({
                            'action': action_str,
                            'reasoning': reasoning,
                            'error': action_error,
                            'result': action_result
                        })
                        self.hybrid_agent.execution_history.append(f"{action_str} → {action_result[:100]}")
                        self.hybrid_agent.iteration += 1
                        actions_executed += 1
                        
                        # Validation périodique
                        if self.hybrid_agent.iteration % self.hybrid_agent.VALIDATE_EVERY_N_STEPS == 0:
                            validation = await self.hybrid_agent.validate_progress(message, observation)
                            logger.info(f"🔍 Progress: {validation.get('progress_percentage', 0)}%")
                            if validation.get('is_complete'):
                                action_result += f"\n\n✅ Task validated as complete!"
                                await self.broadcast({
                                    'type': 'agent_message',
                                    'message': action_result
                                })
                                break
                        
                        # Petite pause pour laisser le temps au screenshot de se mettre à jour
                        await asyncio.sleep(0.5)
                    
                    # Message final récapitulatif
                    if actions_executed > 0:
                        response_message = f"✅ Executed {actions_executed} actions.\n\n" + "\n\n".join(all_responses[-3:])  # Dernières 3 actions
                    else:
                        response_message = "🤔 No actions executed."
                    
                except Exception as nav_error:
                    logger.error(f"Hybrid agent error: {nav_error}")
                    response_message = f"❌ Error: {str(nav_error)}"
                    
                    # Enregistrer l'erreur pour replanification
                    if self.hybrid_agent.action_history:
                        self.hybrid_agent.action_history[-1]['error'] = str(nav_error)
            
            # ===== SIMPLE LLM AGENT (fallback) =====
            elif self.use_llm and self.llm_agent:
                logger.info(f"🤖 Using Simple LLM Agent")
                
                page_info = {
                    'url': self.page.url,
                    'title': await self.page.title() if self.page else None
                }
                
                llm_result = self.llm_agent.get_action_from_message(message, page_info)
                
                if llm_result.get('error'):
                    self.agent_busy = False
                    return {'type': 'agent_message', 'message': f"❌ {llm_result['error']}"}
                
                action_str = llm_result.get('action', '')
                parsed_action = self.llm_agent.parse_action(action_str)
                
                try:
                    if parsed_action['type'] == 'goto':
                        url = parsed_action['url']
                        await self.page.goto(url, wait_until='networkidle', timeout=30000)
                        response_message = f"✅ Navigated to {url}"
                    else:
                        response_message = f"⚠️ Action type '{parsed_action['type']}' not implemented"
                except Exception as exec_error:
                    response_message = f"❌ Error: {str(exec_error)}"
            
            # ===== KEYWORD MATCHING (fallback sans LLM) =====
            else:
                logger.info(f"Using simple keyword matching (no LLM)")
                
                try:
                    if 'google' in message.lower():
                        url = 'https://www.google.com'
                    elif 'github' in message.lower():
                        url = 'https://github.com'
                    else:
                        import re
                        url_match = re.search(r'https?://[^\s]+', message)
                        if url_match:
                            url = url_match.group(0)
                        else:
                            response_message = f"🤖 '{message}'\n\n💡 Set OPENAI_API_KEY for intelligent planning!"
                            self.agent_busy = False
                            return {'type': 'agent_message', 'message': response_message}
                    
                    await self.page.goto(url, wait_until='networkidle', timeout=30000)
                    response_message = f"✅ Navigated to {url}"
                    
                except Exception as nav_error:
                    response_message = f"❌ {str(nav_error)}"
            
            self.agent_busy = False
            return {'type': 'agent_message', 'message': response_message}

        except Exception as e:
            logger.error(f"Error handling user message: {e}")
            self.agent_busy = False
            return {'type': 'error', 'error': str(e)}
    
    async def handle_action(self, action: str) -> Dict[str, Any]:
        """Exécuter une action dans l'environnement"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Environment not initialized'}
            
            logger.info(f"Executing action: {action}")
            # TODO: Exécuter l'action réelle
            
            return {'type': 'action_complete', 'data': {'status': 'success'}}
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_reset(self) -> Dict[str, Any]:
        """Réinitialiser l'environnement"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Environment not initialized'}
            
            logger.info("Resetting environment...")
            await self.page.goto('about:blank')
            
            return {'type': 'init_complete', 'data': {'reset': True}}
            
        except Exception as e:
            logger.error(f"Error resetting: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_pause_agent(self) -> Dict[str, Any]:
        """Mettre l'agent en pause et sauvegarder l'état"""
        try:
            logger.info("🖐️ Pausing agent...")
            
            # Stopper la boucle d'exécution si active
            self.agent_busy = False
            
            # Sauvegarder l'état avec l'agent hybride
            if self.use_hybrid and self.hybrid_agent:
                checkpoint = {
                    'url': self.page.url if self.page else None,
                    'current_plan': self.hybrid_agent.current_plan,
                    'action_history': self.hybrid_agent.action_history[-5:],  # Dernières 5 actions
                    'iteration': self.hybrid_agent.iteration
                }
                self.hybrid_agent.paused = True
                self.hybrid_agent.pause_checkpoint = checkpoint
                logger.info(f"Checkpoint saved at: {checkpoint['url']}")
            
            return {
                'type': 'agent_paused',
                'message': '✋ Agent paused - You have manual control'
            }
            
        except Exception as e:
            logger.error(f"Error pausing agent: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_resume_agent(self) -> Dict[str, Any]:
        """Reprendre l'exécution de l'agent après une pause"""
        try:
            logger.info("▶️ Resuming agent...")
            
            if not self.page:
                return {'type': 'error', 'error': 'Page not available'}
            
            # Récupérer observation fraîche
            if self.use_hybrid and self.hybrid_agent:
                self.hybrid_agent.paused = False
                
                # Obtenir l'observation actuelle (après intervention utilisateur)
                observation = await self.hybrid_agent.get_rich_observation(self.page)
                
                # Réanalyser la situation
                logger.info("🧠 Analyzing current state after manual intervention...")
                
                checkpoint = self.hybrid_agent.pause_checkpoint or {}
                user_task = checkpoint.get('current_plan', {}).get('user_task', 'Continue the task')
                
                # Créer un nouveau plan basé sur l'état actuel
                new_plan = await self.hybrid_agent.create_plan(
                    user_task=user_task,
                    observation=observation
                )
                
                # Ajouter contexte de la pause
                self.hybrid_agent.execution_history.append(
                    f"[PAUSE] User took manual control. Resumed at {observation.url}"
                )
                
                self.hybrid_agent.current_plan = new_plan
                
                logger.info(f"✓ New plan created with {len(new_plan.proposed_actions)} actions")
                
                return {
                    'type': 'agent_resumed',
                    'message': f"▶️ Agent resumed. New plan: {len(new_plan.proposed_actions)} actions to execute."
                }
            
            return {
                'type': 'agent_resumed',
                'message': '▶️ Agent resumed'
            }
            
        except Exception as e:
            logger.error(f"Error resuming agent: {e}")
            return {'type': 'error', 'error': str(e)}
    
    # ===== WORKFLOW RECORDING HANDLERS =====
    
    async def handle_start_recording(self) -> Dict[str, Any]:
        """Démarrer l'enregistrement d'un workflow"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Page not initialized'}
            
            if self.is_recording:
                return {'type': 'error', 'error': 'Already recording'}
            
            # Créer un nouveau recorder
            self.workflow_recorder = WorkflowRecorder(self.page)
            await self.workflow_recorder.start_recording()
            
            self.is_recording = True
            logger.info("🎬 Workflow recording started")
            
            return {
                'type': 'recording_started',
                'message': '🎬 Recording started'
            }
                
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_stop_recording(self, workflow_name: str = None, captured_actions: List[Dict] = None) -> Dict[str, Any]:
        """Arrêter l'enregistrement et sauvegarder le workflow"""
        try:
            if not self.is_recording or not self.workflow_recorder:
                return {'type': 'error', 'error': 'Not recording'}
            
            # Arrêter l'enregistrement
            workflow = await self.workflow_recorder.stop_recording()
            
            # NOUVEAU: Si des actions ont été capturées depuis le BrowserView (Electron),
            # les fusionner avec celles capturées par Playwright
            if captured_actions:
                logger.info(f"📦 Merging {len(captured_actions)} actions from BrowserView")
                
                # Fusionner et trier par timestamp
                all_actions = workflow.get('actions', []) + captured_actions
                all_actions.sort(key=lambda x: x.get('timestamp', 0))
                
                workflow['actions'] = all_actions
                logger.info(f"✅ Total actions after merge: {len(all_actions)}")
            
            # Appliquer le nom si fourni
            if workflow_name:
                workflow['name'] = workflow_name
            
            # Sauvegarder dans le storage
            workflow_id = self.workflow_storage.save(workflow)
            
            self.is_recording = False
            self.workflow_recorder = None
            
            logger.info(f"⏹️ Workflow saved: {workflow_id}")
            
            return {
                'type': 'recording_stopped',
                'data': {
                    'workflow_id': workflow_id,
                    'name': workflow.get('name'),
                    'action_count': len(workflow.get('actions', [])),
                    'duration': workflow.get('duration')
                }
            }
                
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.is_recording = False
            self.workflow_recorder = None
            return {'type': 'error', 'error': str(e)}
    
    async def handle_list_workflows(self) -> Dict[str, Any]:
        """Lister tous les workflows enregistrés"""
        try:
            workflows = self.workflow_storage.list_all()
            
            logger.info(f"📋 Listing {len(workflows)} workflows")
            
            return {
                'type': 'workflows_list',
                'data': {'workflows': workflows}
            }
            
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Obtenir un workflow complet par son ID"""
        try:
            if not workflow_id:
                return {'type': 'error', 'error': 'Missing workflow_id'}
            
            workflow = self.workflow_storage.load(workflow_id)
            
            return {
                'type': 'workflow_data',
                'data': {'workflow': workflow}
            }
            
        except FileNotFoundError:
            return {'type': 'error', 'error': f'Workflow not found: {workflow_id}'}
        except Exception as e:
            logger.error(f"Error getting workflow: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_play_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Rejouer un workflow enregistré"""
        try:
            if not self.page:
                return {'type': 'error', 'error': 'Page not initialized'}
            
            if not workflow_id:
                return {'type': 'error', 'error': 'Missing workflow_id'}
            
            # Charger le workflow
            workflow = self.workflow_storage.load(workflow_id)
            
            logger.info(f"▶️ Playing workflow: {workflow.get('name')}")
            
            # Créer player et exécuter
            player = WorkflowPlayer(self.page)
            results = await player.play(workflow)
            
            return {
                'type': 'workflow_completed',
                'data': results
            }
            
        except FileNotFoundError:
            return {'type': 'error', 'error': f'Workflow not found: {workflow_id}'}
        except Exception as e:
            logger.error(f"Error playing workflow: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Supprimer un workflow"""
        try:
            if not workflow_id:
                return {'type': 'error', 'error': 'Missing workflow_id'}
            
            success = self.workflow_storage.delete(workflow_id)
            
            return {
                'type': 'workflow_deleted',
                'data': {'workflow_id': workflow_id, 'success': success}
            }
            
        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            return {'type': 'error', 'error': str(e)}
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Gérer une connexion client"""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    logger.debug(f"Received message type: {msg_type}")
                    
                    # IMPORTANT: Si c'est un user_message, vérifier si c'est un message JSON (workflow commands)
                    if msg_type == 'user_message':
                        user_msg = data.get('message', '')
                        # Essayer de parser comme JSON
                        try:
                            parsed_msg = json.loads(user_msg)
                            if isinstance(parsed_msg, dict) and 'type' in parsed_msg:
                                # C'est un message structuré (workflow command), router vers le bon handler
                                msg_type = parsed_msg.get('type')
                                data = parsed_msg  # Remplacer data par le message parsé
                                logger.info(f"📦 Parsed structured message: {msg_type}")
                        except (json.JSONDecodeError, TypeError):
                            # Pas du JSON, c'est un vrai message utilisateur
                            pass
                    
                    # Router les messages
                    if msg_type == 'init':
                        response = await self.initialize_env(data.get('config', {}))
                    elif msg_type == 'user_message':
                        response = await self.handle_user_message(data.get('message', ''))
                    elif msg_type == 'action':
                        response = await self.handle_action(data.get('action', ''))
                    elif msg_type == 'reset':
                        response = await self.handle_reset()
                    elif msg_type == 'pause_agent':
                        response = await self.handle_pause_agent()
                    elif msg_type == 'resume_agent':
                        response = await self.handle_resume_agent()
                    # NOUVEAU: Workflow handlers
                    elif msg_type == 'start_recording':
                        response = await self.handle_start_recording()
                    elif msg_type == 'stop_recording':
                        workflow_name = data.get('workflow_name')
                        captured_actions = data.get('captured_actions', [])
                        response = await self.handle_stop_recording(workflow_name, captured_actions)
                    elif msg_type == 'list_workflows':
                        response = await self.handle_list_workflows()
                    elif msg_type == 'get_workflow':
                        workflow_id = data.get('workflow_id')
                        response = await self.handle_get_workflow(workflow_id)
                    elif msg_type == 'play_workflow':
                        workflow_id = data.get('workflow_id')
                        response = await self.handle_play_workflow(workflow_id)
                    elif msg_type == 'delete_workflow':
                        workflow_id = data.get('workflow_id')
                        response = await self.handle_delete_workflow(workflow_id)
                    else:
                        response = {'type': 'error', 'error': f'Unknown message type: {msg_type}'}
                    
                    # Envoyer la réponse
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    await websocket.send(json.dumps({'type': 'error', 'error': 'Invalid JSON'}))
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await websocket.send(json.dumps({'type': 'error', 'error': str(e)}))
        
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected: {client_id}")
            
            # Nettoyer
            if not self.clients and self.browser:
                logger.info("No more clients, closing browser")
                self.stop_screenshot_streaming()
                await self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
    
    async def broadcast(self, message: Dict[str, Any]):
        """Envoyer un message à tous les clients"""
        if self.clients:
            msg_json = json.dumps(message)
            await asyncio.gather(
                *[client.send(msg_json) for client in self.clients],
                return_exceptions=True
            )
    
    async def screenshot_streaming_loop(self):
        """Boucle de streaming de screenshots"""
        logger.info("🎬 Screenshot streaming started")
        
        while self.streaming_active and self.page:
            try:
                # Prendre un screenshot
                screenshot_bytes = await self.page.screenshot(type='png')
                
                # Convertir en base64
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Envoyer à tous les clients
                await self.broadcast({
                    'type': 'screenshot',
                    'data': screenshot_base64
                })
                
                # Attendre avant le prochain screenshot (5 FPS = 200ms)
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Screenshot streaming error: {e}")
                await asyncio.sleep(1)
        
        logger.info("🛑 Screenshot streaming stopped")
    
    def start_screenshot_streaming(self):
        """Démarrer le streaming de screenshots"""
        if not self.streaming_active:
            self.streaming_active = True
            self.screenshot_task = asyncio.create_task(self.screenshot_streaming_loop())
            logger.info("✅ Screenshot streaming task created")
    
    def stop_screenshot_streaming(self):
        """Arrêter le streaming de screenshots"""
        self.streaming_active = False
        if self.screenshot_task:
            self.screenshot_task.cancel()
            self.screenshot_task = None
            logger.info("🛑 Screenshot streaming stopped")
    
    async def start(self):
        """Démarrer le serveur WebSocket"""
        logger.info(f"Starting WebSocket server on port {self.ws_port}")
        logger.info(f"CDP port: {self.cdp_port}")
        
        async with serve(self.handle_client, "localhost", self.ws_port):
            logger.info(f"Server started on ws://localhost:{self.ws_port}")
            await asyncio.Future()  # Run forever


def main():
    parser = argparse.ArgumentParser(description='BrowserGym WebSocket Server')
    parser.add_argument('--cdp-port', type=int, default=9222, help='CDP port')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    server = BrowserGymServer(cdp_port=args.cdp_port, ws_port=args.ws_port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == '__main__':
    main()
