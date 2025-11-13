    async def screenshot_streaming_loop(self):
        """Boucle de streaming de screenshots"""
        logger.info("🎬 Screenshot streaming started")
        
        while self.streaming_active and self.page:
            try:
                # Prendre un screenshot
                screenshot_bytes = await self.page.screenshot(type='png')
                
                # Convertir en base64
                import base64
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Envoyer à tous les clients
                await self.broadcast({
                    'type': 'screenshot',
                    'data': screenshot_base64
                })
                
                # Attendre avant le prochain screenshot (30 FPS = ~33ms, 10 FPS = 100ms)
                await asyncio.sleep(0.2)  # 5 FPS pour commencer
                
            except Exception as e:
                logger.error(f"Screenshot streaming error: {e}")
                await asyncio.sleep(1)  # Attendre plus longtemps en cas d'erreur
        
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

