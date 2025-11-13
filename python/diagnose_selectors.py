#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier les sélecteurs DOM sur Google
"""

import asyncio
from playwright.async_api import async_playwright

async def diagnose_google():
    print("🔍 Diagnostic des sélecteurs Google...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("\n1️⃣ Navigation vers Google...")
        await page.goto('https://www.google.com', wait_until='networkidle')
        await asyncio.sleep(2)
        
        print("\n2️⃣ Recherche des champs input...")
        
        # Tous les inputs
        all_inputs = await page.locator('input').all()
        print(f"   ✓ Nombre total d'inputs: {len(all_inputs)}")
        
        for i, inp in enumerate(all_inputs[:10]):  # Limite à 10
            name = await inp.get_attribute('name')
            type_ = await inp.get_attribute('type')
            aria_label = await inp.get_attribute('aria-label')
            id_ = await inp.get_attribute('id')
            placeholder = await inp.get_attribute('placeholder')
            
            print(f"\n   Input #{i+1}:")
            print(f"     - name: {name}")
            print(f"     - type: {type_}")
            print(f"     - id: {id_}")
            print(f"     - aria-label: {aria_label}")
            print(f"     - placeholder: {placeholder}")
        
        print("\n3️⃣ Tests de sélecteurs...")
        
        selectors = [
            'input[name="q"]',
            'input[name=q]',
            'textarea[name="q"]',
            'input[type="search"]',
            'input[aria-label*="Search" i]',
            'input[aria-label*="Recherche" i]',
            'input[title*="Search" i]',
            '[name="q"]',
            '#APjFqb',  # Souvent l'ID de la search bar Google
        ]
        
        for selector in selectors:
            count = await page.locator(selector).count()
            visible = await page.locator(selector).first.is_visible() if count > 0 else False
            print(f"   {selector:40} → count={count}, visible={visible}")
        
        print("\n4️⃣ Screenshot de la page...")
        await page.screenshot(path='/tmp/google_diagnosis.png')
        print("   ✓ Screenshot sauvé: /tmp/google_diagnosis.png")
        
        print("\n5️⃣ HTML de la page (premiers 2000 chars)...")
        html = await page.content()
        print(html[:2000])
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(diagnose_google())

