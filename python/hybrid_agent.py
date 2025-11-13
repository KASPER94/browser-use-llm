#!/usr/bin/env python3
"""
Agent hybride BrowserGym + BrowserOS
Combine les observations riches de BrowserGym avec le planning de BrowserOS
"""

import logging
import openai
import base64
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from browsergym.core.action.highlevel import HighLevelActionSet
    BROWSERGYM_AVAILABLE = True
except ImportError:
    BROWSERGYM_AVAILABLE = False


@dataclass
class RichObservation:
    """Observation riche à la BrowserGym"""
    screenshot_base64: Optional[str] = None
    url: str = ""
    title: str = ""
    axtree_summary: Optional[str] = None
    visible_elements: List[Dict] = None
    last_action: Optional[str] = None
    last_action_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'title': self.title,
            'has_screenshot': bool(self.screenshot_base64),
            'axtree_summary': self.axtree_summary,
            'elements_count': len(self.visible_elements) if self.visible_elements else 0,
            'last_action': self.last_action,
            'last_error': self.last_action_error
        }


@dataclass
class ExecutionPlan:
    """Plan d'exécution multi-étapes à la BrowserOS"""
    user_task: str
    execution_history: str
    current_state: str
    challenges_identified: str
    step_by_step_reasoning: str
    proposed_actions: List[Dict[str, str]]  # [{action: str, reasoning: str}]
    task_complete: bool = False
    final_answer: str = ""


class HybridBrowserAgent:
    """
    Agent hybride combinant :
    - Observations riches (BrowserGym) : screenshot, AXTree, DOM
    - Planning multi-étapes (BrowserOS) : Plan → Execute → Validate → Replan
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", max_iterations: int = 30):
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.openai_client = openai.OpenAI()
        
        # État de l'agent
        self.current_plan: Optional[ExecutionPlan] = None
        self.execution_history: List[str] = []
        self.action_history: List[Dict] = []
        self.iteration = 0
        
        # NOUVEAU: Support pause/resume
        self.paused: bool = False
        self.pause_checkpoint: Optional[Dict] = None
        
        # Configuration
        self.PLAN_EVERY_N_STEPS = 5
        self.VALIDATE_EVERY_N_STEPS = 3
        
        if BROWSERGYM_AVAILABLE:
            self.action_set = HighLevelActionSet(
                subsets=["chat", "tab", "nav", "bid"],
                strict=False,
                multiaction=False,
                demo_mode="off"
            )
        
        logger.info(f"HybridBrowserAgent initialized with {model_name}")
    
    async def get_rich_observation(self, page) -> RichObservation:
        """
        Obtenir une observation riche à la BrowserGym
        """
        obs = RichObservation()
        
        try:
            # Screenshot
            screenshot_bytes = await page.screenshot(type='png')
            obs.screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # URL et titre
            obs.url = page.url
            obs.title = await page.title()
            
            # AXTree summary (simplified)
            # TODO: Implémenter extraction AXTree complète si besoin
            obs.axtree_summary = f"Page: {obs.title} at {obs.url}"
            
            # Éléments visibles (simplified)
            # TODO: Extraire les éléments interactifs
            obs.visible_elements = []
            
            # Historique
            if self.action_history:
                last = self.action_history[-1]
                obs.last_action = last.get('action')
                obs.last_action_error = last.get('error')
            
        except Exception as e:
            logger.error(f"Error getting observation: {e}")
        
        return obs
    
    async def create_plan(self, user_task: str, observation: RichObservation) -> ExecutionPlan:
        """
        Créer un plan multi-étapes avec raisonnement à la BrowserOS
        """
        logger.info("🧠 Creating multi-step plan...")
        
        # Construire le contexte
        history_summary = "\n".join(self.execution_history[-10:]) if self.execution_history else "No previous actions"
        
        challenges = []
        if observation.last_action_error:
            challenges.append(f"Last action failed: {observation.last_action_error}")
        if self.iteration > 10:
            challenges.append(f"Already {self.iteration} iterations, need to be efficient")
        challenges_text = "\n".join(challenges) if challenges else "No major challenges identified"
        
        # Prompt de planning (inspiré de BrowserOS)
        system_prompt = """You are an expert web automation planner.

Your role is to:
1. Analyze the current browser state
2. Think step-by-step about how to accomplish the user's goal
3. Create a concrete 3-5 step plan
4. Identify potential obstacles

Response format (JSON):
{
  "user_task": "Restate the user's request",
  "execution_history": "What has been tried so far",
  "current_state": "Current page and visible elements",
  "challenges_identified": "Obstacles or errors encountered",
  "step_by_step_reasoning": "Detailed thinking process",
  "proposed_actions": [
    {"action": "goto(url)", "reasoning": "Why this step"},
    {"action": "fill('search', 'query')", "reasoning": "Why this step"}
  ],
  "task_complete": false,
  "final_answer": ""
}

Available actions:
- goto(url): Navigate to URL
- fill(element_desc, text): Fill input field
- click(element_desc): Click element
- send_msg_to_user(message): Send message to user
- done(summary): Mark task complete
"""
        
        user_prompt = f"""Task: {user_task}

Current State:
- URL: {observation.url}
- Title: {observation.title}
- Has screenshot: {bool(observation.screenshot_base64)}

Execution History:
{history_summary}

Challenges:
{challenges_text}

Create a detailed plan to accomplish this task."""
        
        try:
            # Appel OpenAI avec vision si screenshot disponible
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt}
                ]}
            ]
            
            # Ajouter screenshot si disponible
            if observation.screenshot_base64:
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{observation.screenshot_base64}",
                        "detail": "low"  # ou "high" pour plus de détails
                    }
                })
            
            response = self.openai_client.chat.completions.create(
                model=self.model_name if "vision" in self.model_name or "gpt-4" in self.model_name else "gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            plan_data = json.loads(response.choices[0].message.content)
            
            plan = ExecutionPlan(
                user_task=plan_data.get('user_task', user_task),
                execution_history=plan_data.get('execution_history', ''),
                current_state=plan_data.get('current_state', ''),
                challenges_identified=plan_data.get('challenges_identified', ''),
                step_by_step_reasoning=plan_data.get('step_by_step_reasoning', ''),
                proposed_actions=plan_data.get('proposed_actions', []),
                task_complete=plan_data.get('task_complete', False),
                final_answer=plan_data.get('final_answer', '')
            )
            
            logger.info(f"✅ Plan created with {len(plan.proposed_actions)} actions")
            logger.info(f"Reasoning: {plan.step_by_step_reasoning[:200]}...")
            
            return plan
            
        except Exception as e:
            logger.error(f"Planning error: {e}")
            # Fallback plan simple
            return ExecutionPlan(
                user_task=user_task,
                execution_history="",
                current_state=f"At {observation.url}",
                challenges_identified=str(e),
                step_by_step_reasoning="Fallback: simple navigation",
                proposed_actions=[{
                    "action": f"goto('{observation.url}')",
                    "reasoning": "Fallback action"
                }],
                task_complete=False
            )
    
    async def validate_progress(self, user_task: str, observation: RichObservation) -> Dict[str, Any]:
        """
        Valider la progression vers l'objectif
        """
        logger.info("🔍 Validating progress...")
        
        try:
            prompt = f"""Task: {user_task}

Current State:
- URL: {observation.url}
- Title: {observation.title}

Is the task complete? Respond with JSON:
{{
  "is_complete": true/false,
  "progress_percentage": 0-100,
  "next_needed": "What still needs to be done"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            validation = json.loads(response.choices[0].message.content)
            logger.info(f"Progress: {validation.get('progress_percentage', 0)}%")
            
            return validation
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {"is_complete": False, "progress_percentage": 0, "next_needed": "Continue"}
    
    def detect_loop(self) -> bool:
        """
        Détecter si l'agent est coincé dans une boucle
        """
        if len(self.action_history) < 4:
            return False
        
        # Vérifier les 4 dernières actions
        recent = [a.get('action') for a in self.action_history[-4:]]
        
        # Si 3 actions identiques consécutives
        if len(set(recent[-3:])) == 1:
            logger.warning("⚠️ Loop detected: same action repeated 3 times")
            return True
        
        return False
    
    def should_replan(self, observation: RichObservation) -> bool:
        """
        Décider si il faut re-planifier
        """
        # Replan si erreur
        if observation.last_action_error:
            return True
        
        # Replan si boucle détectée
        if self.detect_loop():
            return True
        
        # Replan tous les N steps
        if self.iteration % self.PLAN_EVERY_N_STEPS == 0:
            return True
        
        # Replan si plus d'actions dans le plan
        if not self.current_plan or not self.current_plan.proposed_actions:
            return True
        
        return False

