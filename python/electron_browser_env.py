#!/usr/bin/env python3
"""
Adaptateur BrowserGym pour mode Electron/CDP
Permet de connecter Playwright au BrowserView Electron via async API
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from browsergym.core.env import BrowserEnv
from browsergym.core.task import AbstractBrowserTask

logger = logging.getLogger(__name__)


async def connect_to_electron_browser_async(cdp_endpoint: str):
    """
    SCREENSHOT STREAMING : Connexion à la fenêtre CACHÉE (hiddenWindow)
    pour prendre des screenshots sans capturer l'UI React
    """
    import playwright.async_api
    
    playwright_instance = await playwright.async_api.async_playwright().start()
    
    try:
        # Se connecter via CDP
        browser = await playwright_instance.chromium.connect_over_cdp(cdp_endpoint)
        logger.info(f"Connected to Electron browser, contexts: {len(browser.contexts)}")
        
        # Utiliser le contexte existant
        if browser.contexts:
            context = browser.contexts[0]
            logger.info(f"Using existing context with {len(context.pages)} pages")
            
            # IMPORTANT : Trouver la fenêtre CACHÉE (hiddenWindow)
            # C'est celle avec 'about:blank' ou la DEUXIÈME page créée
            hidden_page = None
            
            for page in context.pages:
                logger.info(f"Found page: {page.url}")
                # La fenêtre cachée a 'about:blank' au démarrage
                if 'about:blank' in page.url or page.url == 'about:blank':
                    hidden_page = page
                    logger.info(f"✓ Found hidden window: {page.url}")
                    break
            
            # Si pas trouvé par URL, prendre la DERNIÈRE page (hiddenWindow créée en dernier)
            if not hidden_page and len(context.pages) > 1:
                hidden_page = context.pages[-1]
                logger.info(f"✓ Using last page as hidden window: {hidden_page.url}")
            elif not hidden_page:
                # Fallback : première page
                hidden_page = context.pages[0]
                logger.warning(f"⚠️ Using first page (might include React UI): {hidden_page.url}")
            
            logger.info("✓ Ready - waiting for user commands")
            return browser, context, hidden_page
            
        else:
            logger.error("No existing context found!")
            raise Exception("No browser context available")
        
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        raise


def connect_to_electron_browser_sync(cdp_endpoint: str):
    """
    Wrapper synchrone pour la connexion async
    À appeler depuis un contexte NON-asyncio
    """
    try:
        # Créer une nouvelle event loop pour la connexion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(connect_to_electron_browser_async(cdp_endpoint))
        
        return result
        
    except Exception as e:
        logger.error(f"Sync wrapper error: {e}")
        raise
    finally:
        loop.close()


class DummyTask(AbstractBrowserTask):
    """Tâche factice pour le mode Electron"""
    
    def __init__(self, seed=None):
        super().__init__(seed)
    
    @classmethod
    def get_task_id(cls):
        return "electron_dummy_task"
    
    def setup(self, page):
        pass
    
    def teardown(self):
        pass
    
    def validate(self, page, chat_messages):
        return 0.0, False, "", {}

