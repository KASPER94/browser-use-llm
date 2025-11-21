import base64
import logging
import os
import json
import aiohttp
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class VLMService:
    """
    Service pour interagir avec un Vision Language Model via API compatible OpenAI.
    Utilise les variables d'environnement VLM_URL et VLM_MODEL.
    """
    
    def __init__(self):
        self.api_url = os.getenv("VLM_URL", "http://localhost:8000/v1/chat/completions")
        self.model = os.getenv("VLM_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY", "dummy") # Clé dummy si self-hosted
        
        # Si l'URL ne contient pas le endpoint, on l'ajoute (supposition courante)
        if "chat/completions" not in self.api_url and not self.api_url.endswith("/"):
            self.api_url = f"{self.api_url}/v1/chat/completions"
            
        self.enabled = bool(os.getenv("VLM_URL") or os.getenv("OPENAI_API_KEY"))
        
        if self.enabled:
            logger.info(f"👁️ VLMService initialized with URL: {self.api_url}, Model: {self.model}")
        else:
            logger.warning("⚠️ VLMService disabled: VLM_URL or OPENAI_API_KEY not set")

    async def _call_vlm_api(self, prompt: str, screenshot_base64: str) -> Optional[str]:
        """Appel générique à l'API VLM"""
        if not self.enabled:
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.1
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ VLM API Error {response.status}: {error_text}")
                        return None
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    return content

        except Exception as e:
            logger.error(f"❌ VLM Request Exception: {e}")
            return None

    async def get_element_coordinates(self, screenshot_base64: str, element_description: str) -> Optional[Tuple[int, int]]:
        """
        Demande au VLM les coordonnées (x, y) d'un élément.
        Retour attendu du VLM: JSON {"x": 100, "y": 200}
        """
        prompt = f"""
        Look at this screenshot of a web page. I need to find the center coordinates (x, y) of the following element:
        "{element_description}"

        Return ONLY a JSON object with the coordinates, like this: {{"x": 150, "y": 300}}.
        If the element is not visible or cannot be found, return {{"error": "not found"}}.
        DO NOT write any other text or explanation. Just the JSON.
        """
        
        response_text = await self._call_vlm_api(prompt, screenshot_base64)
        
        if not response_text:
            return None
            
        try:
            # Nettoyage basique au cas où le modèle est bavard (markdown code blocks)
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Chercher le premier { et le dernier }
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]
            
            data = json.loads(clean_text)
            
            if "error" in data:
                logger.warning(f"👁️ VLM could not find element: {data['error']}")
                return None
                
            if "x" in data and "y" in data:
                return (int(data["x"]), int(data["y"]))
                
        except json.JSONDecodeError:
            logger.error(f"❌ Failed to parse VLM response as JSON: {response_text}")
        except Exception as e:
            logger.error(f"❌ Error processing VLM response: {e}")
            
        return None

    async def validate_state(self, screenshot_base64: str, expectation: str) -> bool:
        """
        Vérifie si l'état visuel correspond à l'attente (YES/NO).
        """
        prompt = f"""
        Look at this screenshot. Does it satisfy the following condition?
        Condition: "{expectation}"

        Reply with exactly one word: "YES" if the condition is met, "NO" otherwise.
        """
        
        response_text = await self._call_vlm_api(prompt, screenshot_base64)
        
        if not response_text:
            # En cas d'erreur VLM, on assume le succès pour ne pas bloquer le workflow (fail open)
            # ou fail close selon la criticité. Ici "fail open" pour l'UX.
            logger.warning("⚠️ VLM validation failed (network/api), assuming success.")
            return True
            
        answer = response_text.strip().upper()
        logger.info(f"👁️ VLM Validation: {answer} (Expectation: {expectation})")
        
        return "YES" in answer
