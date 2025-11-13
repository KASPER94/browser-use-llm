#!/usr/bin/env python3
"""
Adaptateur DemoAgent pour Electron + Screenshot Streaming
Version simplifiée du DemoAgent pour fonctionner avec l'architecture Electron
"""

import logging
import openai
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from browsergym.core.action.highlevel import HighLevelActionSet
    BROWSERGYM_AVAILABLE = True
except ImportError:
    BROWSERGYM_AVAILABLE = False
    logger.warning("BrowserGym not available")


class ElectronDemoAgent:
    """
    Agent LLM simplifié pour Electron
    Utilise OpenAI pour interpréter les commandes utilisateur
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.openai_client = openai.OpenAI()
        self.action_history = []
        
        if BROWSERGYM_AVAILABLE:
            self.action_set = HighLevelActionSet(
                subsets=["chat", "tab", "nav", "bid"],
                strict=False,
                multiaction=False,
                demo_mode="off",  # Pas d'effets visuels (on a déjà les screenshots)
            )
        else:
            self.action_set = None
        
        logger.info(f"ElectronDemoAgent initialized with model: {model_name}")
    
    def get_action_from_message(self, user_message: str, page_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Interpréter un message utilisateur et retourner l'action à exécuter
        
        Args:
            user_message: Le message de l'utilisateur
            page_info: Informations sur la page actuelle (URL, titre, etc.)
        
        Returns:
            Dict avec 'action' (str) et 'reasoning' (str)
        """
        try:
            # Construire le prompt
            system_prompt = """You are a web browser automation assistant.
Your role is to interpret user commands and convert them into browser actions.

Available actions:
- goto("url") - Navigate to a URL
- click("element_description") - Click on an element
- fill("input_description", "text") - Fill a form field
- send_msg_to_user("message") - Send a message to the user

Examples:
User: "go to google"
Action: goto("https://www.google.com")

User: "search for python tutorials"
Action: goto("https://www.google.com/search?q=python+tutorials")

User: "click on the first link"
Action: click("first search result link")

Respond with ONLY the action in the format above, nothing else.
"""
            
            user_prompt = f"User command: {user_message}"
            
            if page_info:
                user_prompt += f"\nCurrent page: {page_info.get('url', 'unknown')}"
                if page_info.get('title'):
                    user_prompt += f"\nPage title: {page_info['title']}"
            
            # Appel à l'API OpenAI
            logger.info(f"Calling OpenAI API with: {user_message}")
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            action = response.choices[0].message.content.strip()
            self.action_history.append({
                'user_message': user_message,
                'action': action
            })
            
            logger.info(f"LLM returned action: {action}")
            
            return {
                'action': action,
                'reasoning': f"Interpreted '{user_message}' as: {action}"
            }
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                'action': None,
                'error': f"LLM error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error getting action: {e}")
            return {
                'action': None,
                'error': f"Error: {str(e)}"
            }
    
    def parse_action(self, action_str: str) -> Dict[str, Any]:
        """
        Parser l'action retournée par le LLM
        
        Returns:
            Dict avec 'type' et 'params'
        """
        import re
        
        # goto("url")
        goto_match = re.match(r'goto\(["\'](.+?)["\']\)', action_str)
        if goto_match:
            return {
                'type': 'goto',
                'url': goto_match.group(1)
            }
        
        # click("element")
        click_match = re.match(r'click\(["\'](.+?)["\']\)', action_str)
        if click_match:
            return {
                'type': 'click',
                'element': click_match.group(1)
            }
        
        # fill("input", "text")
        fill_match = re.match(r'fill\(["\'](.+?)["\']\s*,\s*["\'](.+?)["\']\)', action_str)
        if fill_match:
            return {
                'type': 'fill',
                'element': fill_match.group(1),
                'text': fill_match.group(2)
            }
        
        # send_msg_to_user("message")
        msg_match = re.match(r'send_msg_to_user\(["\'](.+?)["\']\)', action_str)
        if msg_match:
            return {
                'type': 'message',
                'content': msg_match.group(1)
            }
        
        # Fallback : essayer d'extraire une URL directement
        url_match = re.search(r'https?://[^\s\)"\']+', action_str)
        if url_match:
            return {
                'type': 'goto',
                'url': url_match.group(0)
            }
        
        return {
            'type': 'unknown',
            'raw': action_str
        }

