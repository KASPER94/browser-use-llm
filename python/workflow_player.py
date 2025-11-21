#!/usr/bin/env python3
"""
WorkflowPlayer - Rejoue un workflow enregistré
MVP: goto, click, fill (pas de variables pour l'instant)
"""

import asyncio
import logging
import base64
from typing import Dict, Any, Optional
from playwright.async_api import Page

# Eviter l'import circulaire si VLMService est dans un autre fichier,
# mais ici on importe juste pour le type hint ou on utilise Any
try:
    from vlm_service import VLMService
except ImportError:
    VLMService = Any

logger = logging.getLogger(__name__)


class WorkflowPlayer:
    """
    Rejoue un workflow enregistré
    MVP: goto, click, fill (pas de variables pour l'instant)
    """
    
    def __init__(self, page: Page, vlm_service: Optional[VLMService] = None):
        self.page = page
        self.vlm_service = vlm_service
    
    async def play(self, workflow: Dict[str, Any], variables: Dict[str, str] = None) -> Dict[str, Any]:
        """Rejouer un workflow complet"""
        workflow_name = workflow.get('name', 'Unknown')
        actions = workflow.get('actions', [])
        variables = variables or {}
        
        logger.info(f"▶️ Playing workflow: {workflow_name} ({len(actions)} actions)")
        if variables:
            logger.info(f"  Variables provided: {', '.join(variables.keys())}")
        
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
                
                # NOUVEAU: Attendre que la page soit stable avant chaque action
                await self._wait_for_page_ready()
                
                if action_type == 'goto':
                    await self._execute_goto(action, variables)
                
                elif action_type == 'click':
                    await self._execute_click(action)
                
                elif action_type == 'fill':
                    await self._execute_fill(action, variables)
                
                elif action_type == 'scroll':
                    await self._execute_scroll(action)
                
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                
                results['actions_executed'] += 1
                
                # NOUVEAU: Attendre après l'action (laisser le temps à la page de réagir)
                await asyncio.sleep(0.8)  # Augmenté de 0.5 à 0.8
            
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
    
    async def _wait_for_page_ready(self):
        """Attendre que la page soit prête avant d'exécuter une action"""
        try:
            # Attendre que la page soit en état stable (pas de requêtes réseau en cours)
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except Exception as e:
            # Si timeout, continuer quand même (certaines pages ont toujours des requêtes)
            logger.debug(f"networkidle timeout (OK): {e}")
            pass
    
    async def _execute_goto(self, action: Dict[str, Any], variables: Dict[str, str]):
        """Exécuter une navigation"""
        url = action.get('url')
        
        if not url:
            raise ValueError("Missing URL for goto action")
        
        # Substitution de variables
        url = self._substitute_variables(url, variables)
        
        await self.page.goto(url, wait_until='networkidle', timeout=30000)
        logger.info(f"  → Navigated to: {url}")
    
    def _substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Remplacer les variables ${VAR} par leur valeur"""
        if not text or not variables:
            return text
            
        result = text
        for key, value in variables.items():
            # Format standard ${VAR}
            result = result.replace(f"${{{key}}}", value)
            # Format simplifié $VAR (optionnel, mais pratique)
            # result = result.replace(f"${key}", value)
            
        return result

    async def _execute_click(self, action: Dict[str, Any]):
        """
        Exécuter un clic avec fallback intelligent
        Utilise le contexte (texte, href, aria-label, index) si le sélecteur CSS échoue
        """
        selector = action.get('selector')
        context = action.get('context', {})
        
        if not selector:
            raise ValueError("Missing selector for click action")
        
        logger.info(f"  📋 Click action details:")
        logger.info(f"     selector: {selector}")
        logger.info(f"     context: {context}")
        
        # NOUVEAU: Pour les liens, prioriser le texte visible et href
        if context.get('href') or context.get('text'):
            text = context.get('text', '')
            href = context.get('href', '')
            
            # Stratégie spéciale pour les résultats de recherche (comme DuckDuckGo)
            # 1. Chercher un lien qui contient le texte ET pointe vers le bon domaine
            try:
                # Extraire le domaine du href
                from urllib.parse import urlparse
                expected_domain = ''
                if href:
                    expected_domain = urlparse(href).netloc
                
                # Chercher tous les liens visibles
                links = await self.page.locator('a:visible').all()
                
                logger.info(f"  🔍 Smart link matching:")
                logger.info(f"     Expected text: '{text[:50]}'")
                logger.info(f"     Expected domain: '{expected_domain}'")
                logger.info(f"     Expected href: '{href[:80]}'")
                logger.info(f"     Found {len(links)} visible links on page")
                
                best_match = None
                best_score = 0
                all_candidates = []
                
                for idx, link in enumerate(links):
                    try:
                        link_text = await link.inner_text()
                        link_href = await link.get_attribute('href')
                        
                        if not link_href:
                            continue
                        
                        # Calculer un score de correspondance
                        score = 0
                        score_details = []
                        
                        # Le texte correspond (substring ou similaire)
                        text_lower = text.lower()
                        link_text_lower = link_text.lower()
                        
                        if text_lower and link_text_lower:
                            # Correspondance exacte
                            if text_lower == link_text_lower:
                                score += 100
                                score_details.append("text_exact=100")
                            # Le texte attendu est dans le lien
                            elif text_lower in link_text_lower:
                                score += 70
                                score_details.append("text_contains=70")
                            # Le lien contient des mots du texte attendu
                            elif link_text_lower in text_lower:
                                score += 50
                                score_details.append("text_partial=50")
                            # Au moins un mot en commun
                            else:
                                text_words = set(text_lower.split())
                                link_words = set(link_text_lower.split())
                                common_words = text_words & link_words
                                if common_words:
                                    score += len(common_words) * 10
                                    score_details.append(f"common_words={len(common_words) * 10}")
                        
                        # Le domaine correspond exactement
                        link_domain = ''
                        if link_href.startswith('http'):
                            link_domain = urlparse(link_href).netloc
                        
                        if expected_domain and link_domain:
                            if link_domain == expected_domain:
                                score += 100
                                score_details.append("domain_exact=100")
                            # Même domaine principal (ex: www.site.com vs site.com)
                            elif expected_domain.replace('www.', '') == link_domain.replace('www.', ''):
                                score += 90
                                score_details.append("domain_main=90")
                            # Sous-domaine du domaine attendu
                            elif link_domain.endswith('.' + expected_domain) or expected_domain.endswith('.' + link_domain):
                                score += 50
                                score_details.append("domain_related=50")
                        
                        # Le href correspond partiellement
                        if href and link_href:
                            if href == link_href:
                                score += 50
                                score_details.append("href_exact=50")
                            elif href in link_href or link_href in href:
                                score += 30
                                score_details.append("href_partial=30")
                        
                        # Sauvegarder pour logs
                        candidate_info = {
                            'index': idx,
                            'score': score,
                            'text': link_text[:50],
                            'href': link_href[:80],
                            'domain': link_domain,
                            'details': ', '.join(score_details)
                        }
                        all_candidates.append(candidate_info)
                        
                        if score > best_score:
                            best_score = score
                            best_match = link
                            logger.info(f"     💡 New best match (score={score}): {score_details}")
                            logger.info(f"        text: {link_text[:50]}")
                            logger.info(f"        href: {link_href[:80]}")
                    
                    except Exception as e:
                        continue
                
                # Log tous les candidats (top 5)
                logger.info(f"  📊 Top candidates:")
                sorted_candidates = sorted(all_candidates, key=lambda x: x['score'], reverse=True)
                for i, candidate in enumerate(sorted_candidates[:5]):
                    logger.info(f"     #{i+1} [score={candidate['score']:3d}] {candidate['text']}")
                    logger.info(f"         → {candidate['href']}")
                    if candidate['details']:
                        logger.info(f"         → {candidate['details']}")
                
                # NOUVEAU: Seuil abaissé à 50 (au lieu de 80)
                if best_match and best_score >= 50:
                    await best_match.click(timeout=5000)
                    logger.info(f"  ✅ Clicked best match (score={best_score})")
                    return
                
                logger.warning(f"  ⚠️ No good match found (best score={best_score}), trying fallback strategies...")
            
            except Exception as e:
                logger.warning(f"Smart link matching failed: {e}")
        
        # Stratégie 1: Sélecteur CSS direct
        try:
            element_count = await self.page.locator(selector).count()
            logger.info(f"  🎯 Strategy 1 (CSS selector): found {element_count} elements")
            if element_count > 0:
                # Si plusieurs éléments, utiliser le contexte pour choisir le bon
                if element_count > 1 and context.get('index') is not None:
                    index = context['index']
                    if index < element_count:
                        await self.page.locator(selector).nth(index).click(timeout=5000)
                        logger.info(f"  → Clicked: {selector}[{index}]")
                        return
                
                await self.page.click(selector, timeout=5000)
                logger.info(f"  → Clicked: {selector}")
                return
        except Exception as e1:
            logger.info(f"  ❌ Strategy 1 failed: {e1}")
        
        # Stratégie 2: Utiliser le href (pour les liens)
        if context.get('href'):
            try:
                href = context['href']
                logger.info(f"  🎯 Strategy 2 (href exact match)")
                await self.page.click(f'a[href="{href}"]', timeout=5000)
                logger.info(f"  → Clicked by href: {href}")
                return
            except Exception as e2:
                logger.info(f"  ❌ Strategy 2 failed: {e2}")
        
        # Stratégie 3: Utiliser aria-label
        if context.get('ariaLabel'):
            try:
                aria_label = context['ariaLabel']
                logger.info(f"  🎯 Strategy 3 (aria-label)")
                await self.page.click(f'[aria-label="{aria_label}"]', timeout=5000)
                logger.info(f"  → Clicked by aria-label: {aria_label}")
                return
            except Exception as e3:
                logger.info(f"  ❌ Strategy 3 failed: {e3}")
        
        # Stratégie 4: Utiliser le texte visible
        text = context.get('text', '').strip()
        if text:
            try:
                logger.info(f"  🎯 Strategy 4 (exact text match)")
                # Essayer avec le texte exact
                await self.page.get_by_text(text, exact=True).first.click(timeout=5000)
                logger.info(f"  → Clicked by text (exact): {text[:50]}")
                return
            except Exception as e4:
                logger.info(f"  ❌ Strategy 4 failed: {e4}")
                try:
                    logger.info(f"  🎯 Strategy 4b (partial text match)")
                    # Essayer avec substring
                    await self.page.get_by_text(text[:30]).first.click(timeout=5000)
                    logger.info(f"  → Clicked by text (partial): {text[:30]}")
                    return
                except Exception as e4b:
                    logger.info(f"  ❌ Strategy 4b failed: {e4b}")
        
        # Stratégie 5: Utiliser le role + index dans une liste
        if context.get('role') and context.get('index') is not None:
            try:
                role = context['role']
                index = context['index']
                logger.info(f"  🎯 Strategy 5 (role + index)")
                elements = await self.page.locator(f'[role="{role}"]').all()
                if 0 <= index < len(elements):
                    await elements[index].click(timeout=5000)
                    logger.info(f"  → Clicked by role+index: {role}[{index}]")
                    return
            except Exception as e5:
                logger.info(f"  ❌ Strategy 5 failed: {e5}")
        
        # Stratégie 6: Tag simple avec index
        if context.get('index') is not None:
            try:
                logger.info(f"  🎯 Strategy 6 (tag + index)")
                # Extraire le tag du sélecteur
                tag = selector.split('.')[0].split('#')[0].split('[')[0]
                if tag and tag != 'unknown':
                    index = context['index']
                    parent_elements = await self.page.locator(f'{tag}').all()
                    if 0 <= index < len(parent_elements):
                        await parent_elements[index].click(timeout=5000)
                        logger.info(f"  → Clicked by tag+index: {tag}[{index}]")
                        return
            except Exception as e6:
                logger.info(f"  ❌ Strategy 6 failed: {e6}")

        # Stratégie 7: VLM Visual Search (NOUVEAU)
        if self.vlm_service and self.vlm_service.enabled:
            try:
                logger.info(f"  🎯 Strategy 7 (VLM Visual Search)")
                
                # Prendre un screenshot pour le VLM
                screenshot_bytes = await self.page.screenshot(type='png')
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Construire une description de l'élément pour le VLM
                description = f"Element to click: {selector}"
                if context.get('text'):
                    description += f", text: '{context['text']}'"
                if context.get('ariaLabel'):
                    description += f", aria-label: '{context['ariaLabel']}'"
                if context.get('role'):
                    description += f", role: '{context['role']}'"
                
                logger.info(f"     Asking VLM to find: {description}")
                
                coords = await self.vlm_service.get_element_coordinates(screenshot_base64, description)
                
                if coords:
                    x, y = coords
                    await self.page.mouse.click(x, y)
                    logger.info(f"  ✅ VLM found element at ({x}, {y}) -> Clicked")
                    return
                else:
                     logger.info(f"  ❌ VLM could not find element")
                     
            except Exception as e7:
                logger.error(f"  ❌ Strategy 7 failed: {e7}")
        
        # Échec de toutes les stratégies
        logger.error(f"  ❌ ALL STRATEGIES FAILED")
        logger.error(f"     Selector: {selector}")
        logger.error(f"     Context: {context}")
        raise Exception(f"Could not find clickable element after trying all strategies")
    
    async def _execute_fill(self, action: Dict[str, Any], variables: Dict[str, str]):
        """Exécuter un remplissage de champ"""
        selector = action.get('selector')
        raw_value = action.get('value', '')
        
        if not selector:
            raise ValueError("Missing selector for fill action")
        
        # Substitution de variables
        value = self._substitute_variables(raw_value, variables)
        
        try:
            # Clear puis fill
            await self.page.fill(selector, '', timeout=5000)
            await self.page.fill(selector, value, timeout=5000)
            
            # Log masqué si c'est un password
            if 'password' in selector.lower():
                logger.info(f"  → Filled: {selector} (***)")
            else:
                display_value = value[:20] + '...' if len(value) > 20 else value
                logger.info(f"  → Filled: {selector} = '{display_value}'")
                
        except Exception as e:
            logger.info(f"  ❌ Fill failed: {e}")
            
            # Fallback VLM pour le fill
            if self.vlm_service and self.vlm_service.enabled:
                try:
                    logger.info(f"  🎯 Fill Strategy VLM (Visual Search)")
                    
                    # Prendre un screenshot pour le VLM
                    screenshot_bytes = await self.page.screenshot(type='png')
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    # Construire une description de l'élément pour le VLM
                    description = f"Input field to fill: {selector}"
                    # Pour un fill, on peut donner des indices supplémentaires si disponibles dans le contexte de l'action précédente (si on l'avait)
                    # Mais ici on n'a que le sélecteur.
                    
                    logger.info(f"     Asking VLM to find input: {description}")
                    
                    coords = await self.vlm_service.get_element_coordinates(screenshot_base64, description)
                    
                    if coords:
                        x, y = coords
                        # Cliquer pour focus
                        await self.page.mouse.click(x, y)
                        logger.info(f"  ✅ VLM found input at ({x}, {y}) -> Clicked (focus)")
                        
                        # Attendre un peu que le focus se fasse
                        await asyncio.sleep(0.5)
                        
                        # Typer au clavier
                        await self.page.keyboard.type(value)
                        
                        if 'password' in selector.lower():
                            logger.info(f"  → Typed via VLM (***)")
                        else:
                            display_value = value[:20] + '...' if len(value) > 20 else value
                            logger.info(f"  → Typed via VLM: '{display_value}'")
                        return
                    else:
                         logger.info(f"  ❌ VLM could not find input element")
                except Exception as vlm_e:
                    logger.error(f"  ❌ VLM Fill failed: {vlm_e}")
            
            # Si tout échoue, relancer l'exception originale
            raise e
    
    async def _execute_scroll(self, action: Dict[str, Any]):
        """Exécuter un scroll vers une position"""
        x = action.get('x', 0)
        y = action.get('y', 0)
        
        # Scroller vers la position
        await self.page.evaluate(f"window.scrollTo({x}, {y})")
        
        logger.info(f"  → Scrolled to: x={x}, y={y}")

