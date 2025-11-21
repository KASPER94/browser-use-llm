// main.js - SCREENSHOT STREAMING ARCHITECTURE + INTERACTIVE BROWSERVIEW
const { app, BrowserWindow, BrowserView, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const WebSocket = require('ws');

let mainWindow; // Fenêtre VISIBLE (chat + screenshot display)
let hiddenWindow; // Fenêtre CACHÉE (Playwright navigue ici)
let interactiveBrowserView = null; // BrowserView pour mode manuel
let pythonProcess;
let wsClient;

// NOUVEAU: Buffer pour stocker les actions capturées en temps réel
let capturedActionsBuffer = [];

// Configuration
const CONFIG = {
  WINDOW_WIDTH: 1600,
  WINDOW_HEIGHT: 1000,
  CDP_PORT: 9222,
  WS_PORT: 8765,
  PYTHON_PATH: process.env.PYTHON_PATH || 'python3',
  PYTHON_SERVER_SCRIPT: path.join(__dirname, 'python', 'browsergym_server.py'),
};

/**
 * Créer la fenêtre CACHÉE (pour Playwright)
 */
async function createHiddenWindow() {
  hiddenWindow = new BrowserWindow({
    width: 1280,
    height: 720,
    show: false, // CACHÉE !
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    title: 'BrowserGym - Hidden Browser',
  });

  await hiddenWindow.loadURL('about:blank');
  console.log('Hidden window created (offscreen for Playwright)');
}

/**
 * Créer la fenêtre VISIBLE (chat + screenshot display)
 */
async function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: CONFIG.WINDOW_WIDTH,
    height: CONFIG.WINDOW_HEIGHT,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    title: 'BrowserGym',
    backgroundColor: '#1a1a1a',
    show: false,
  });

  // Charger l'interface (maintenant avec screenshot display)
  await mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  console.log('Main window loaded with screenshot streaming');

  mainWindow.show();
  console.log('Window shown');

  // Ouvrir DevTools en mode développement
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }
}

/**
 * Lancer le serveur Python BrowserGym
 */
async function startPythonServer(cdpPort) {
  return new Promise((resolve, reject) => {
    const pythonPath = CONFIG.PYTHON_PATH;
    const serverScript = CONFIG.PYTHON_SERVER_SCRIPT;

    console.log('Starting Python server...');
    console.log(`Python: ${pythonPath}`);
    console.log(`Script: ${serverScript}`);
    console.log(`CDP Port: ${cdpPort}`);

    pythonProcess = spawn(pythonPath, [serverScript, `--cdp-port=${cdpPort}`, `--ws-port=${CONFIG.WS_PORT}`]);

    let resolved = false;

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(`[Python] ${output}`);
      if (output.includes(`Server started`) && !resolved) {
        resolved = true;
        resolve();
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString();
      console.error(`[Python Error] ${output}`);
      // IMPORTANT : Le serveur Python log sur stderr, donc checker ici aussi
      if (output.includes(`Server started`) && !resolved) {
        resolved = true;
        resolve();
      }
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python process exited with code ${code}`);
      if (code !== 0 && !app.isQuitting && !resolved) {
        reject(new Error(`Python server exited with code ${code}`));
      }
    });

    pythonProcess.on('error', (err) => {
      console.error(`Failed to start Python process: ${err.message}`);
      if (!resolved) {
        reject(err);
      }
    });
  });
}

/**
 * Connecter au serveur WebSocket Python
 */
function connectToWebSocketServer() {
  console.log('connectToWebSocketServer called!');
  const wsUrl = `ws://localhost:${CONFIG.WS_PORT}`;
  console.log(`Creating WebSocket connection to: ${wsUrl}`);
  
  try {
    wsClient = new WebSocket(wsUrl);
    console.log('WebSocket object created');

    wsClient.onopen = () => {
      console.log('WebSocket connected!');
      if (mainWindow) {
        mainWindow.webContents.send('websocket-status', 'connected');
        // Envoyer un message d'initialisation au serveur Python
        wsClient.send(JSON.stringify({ type: 'init', config: { viewport: { width: 1024, height: 768 } } }));
      }
    };

    wsClient.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received from Python:', data.type);
      if (mainWindow) {
        mainWindow.webContents.send('python-message', data);
      }
    };

    wsClient.onclose = () => {
      console.log('WebSocket disconnected');
      if (mainWindow) {
        mainWindow.webContents.send('websocket-status', 'disconnected');
      }
    };

    wsClient.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (mainWindow) {
        mainWindow.webContents.send('websocket-status', 'disconnected');
      }
    };
  } catch (err) {
    console.error('Exception creating WebSocket:', err);
  }
}

// IPC pour envoyer des messages au serveur Python
ipcMain.on('send-user-message', (event, message) => {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ type: 'user_message', message }));
  } else {
    console.error('WebSocket not open, cannot send message.');
    if (mainWindow) {
      mainWindow.webContents.send('python-message', { type: 'error', error: 'WebSocket not open.' });
    }
  }
});

ipcMain.on('reset-environment', () => {
  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(JSON.stringify({ type: 'reset' }));
  } else {
    console.error('WebSocket not open, cannot reset environment.');
    if (mainWindow) {
      mainWindow.webContents.send('python-message', { type: 'error', error: 'WebSocket not open.' });
    }
  }
});

// ===== NOUVEAU : HANDLERS POUR MODE INTERACTIF =====

/**
 * Activer le mode interactif : créer BrowserView
 */
ipcMain.handle('enable-interactive-mode', async (event) => {
  try {
    console.log('🖐️ Enabling interactive mode...');
    
    if (!hiddenWindow || !mainWindow) {
      return { success: false, error: 'Windows not initialized' };
    }
    
    // Obtenir l'URL actuelle de la fenêtre cachée
    const currentUrl = hiddenWindow.webContents.getURL();
    console.log(`Current URL: ${currentUrl}`);
    
    // Créer le BrowserView s'il n'existe pas déjà
    if (!interactiveBrowserView) {
      interactiveBrowserView = new BrowserView({
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          sandbox: true,
        },
      });
      
      console.log('BrowserView created');
    }
    
    // Attacher le BrowserView à la fenêtre principale
    mainWindow.setBrowserView(interactiveBrowserView);
    
    // Calculer les dimensions (moitié droite de la fenêtre)
    const bounds = mainWindow.getBounds();
    const halfWidth = Math.floor(bounds.width / 2);
    
    interactiveBrowserView.setBounds({
      x: halfWidth,
      y: 0,
      width: halfWidth,
      height: bounds.height,
    });
    
    console.log(`BrowserView bounds: x=${halfWidth}, y=0, w=${halfWidth}, h=${bounds.height}`);
    
    // Charger l'URL actuelle
    if (currentUrl && currentUrl !== 'about:blank') {
      await interactiveBrowserView.webContents.loadURL(currentUrl);
      console.log(`✓ BrowserView loaded: ${currentUrl}`);
    } else {
      await interactiveBrowserView.webContents.loadURL('about:blank');
      console.log('✓ BrowserView loaded: about:blank');
    }
    
    // Auto-resize sur changement de taille de fenêtre
    mainWindow.on('resize', updateBrowserViewBounds);
    
    return { success: true, url: currentUrl };
    
  } catch (error) {
    console.error('Error enabling interactive mode:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Désactiver le mode interactif : retirer BrowserView
 */
ipcMain.handle('disable-interactive-mode', async (event) => {
  try {
    console.log('▶️ Disabling interactive mode...');
    
    if (interactiveBrowserView && mainWindow) {
      // Obtenir l'URL finale du BrowserView (après modifications utilisateur)
      const finalUrl = interactiveBrowserView.webContents.getURL();
      console.log(`Final URL in BrowserView: ${finalUrl}`);
      
      // Synchroniser l'URL avec hiddenWindow (pour que Playwright continue là où l'utilisateur était)
      if (hiddenWindow && finalUrl && finalUrl !== 'about:blank') {
        try {
          await hiddenWindow.webContents.loadURL(finalUrl);
          console.log(`✓ hiddenWindow synced to: ${finalUrl}`);
        } catch (err) {
          console.error('Error syncing URL to hiddenWindow:', err.message);
        }
      }
      
      // Retirer le BrowserView
      mainWindow.setBrowserView(null);
      
      // Fermer le webContents (libérer les ressources)
      if (!interactiveBrowserView.webContents.isDestroyed()) {
        interactiveBrowserView.webContents.close();
      }
      
      interactiveBrowserView = null;
      
      // Retirer l'event listener resize
      mainWindow.removeListener('resize', updateBrowserViewBounds);
      
      console.log('✓ Interactive mode disabled');
      
      return { success: true, finalUrl };
    }
    
    return { success: true };
    
  } catch (error) {
    console.error('Error disabling interactive mode:', error);
    return { success: false, error: error.message };
  }
});

/**
 * NOUVEAU: Activer le mode recording : ouvrir BrowserView pour enregistrer
 */
ipcMain.handle('enable-recording-mode', async (event) => {
  try {
    console.log('🎬 Enabling recording mode...');
    
    // NOUVEAU: Vider le buffer au début de l'enregistrement
    capturedActionsBuffer = [];
    console.log('🗑️ Cleared action buffer for new recording');
    
    if (!hiddenWindow || !mainWindow) {
      return { success: false, error: 'Windows not initialized' };
    }
    
    // Créer un BrowserView dédié pour le recording
    if (!interactiveBrowserView) {
      interactiveBrowserView = new BrowserView({
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: false, // TEMPORAIRE: Désactiver pour permettre capture
          sandbox: false, // TEMPORAIRE: Désactiver pour permettre capture
        },
      });
      
      console.log('BrowserView created for recording');
    }
    
    // Attacher le BrowserView à la fenêtre principale
    mainWindow.setBrowserView(interactiveBrowserView);
    
    // Calculer les dimensions (moitié droite de la fenêtre)
    const bounds = mainWindow.getBounds();
    const halfWidth = Math.floor(bounds.width / 2);
    
    interactiveBrowserView.setBounds({
      x: halfWidth,
      y: 0,
      width: halfWidth,
      height: bounds.height,
    });
    
    console.log(`BrowserView bounds: x=${halfWidth}, y=0, w=${halfWidth}, h=${bounds.height}`);
    
    // Charger une page de départ (about:blank ou dernière URL connue)
    const startUrl = hiddenWindow.webContents.getURL();
    const urlToLoad = (startUrl && startUrl !== 'about:blank') ? startUrl : 'https://www.duckduckgo.com';
    
    // Attendre que la page soit complètement chargée avant d'injecter le script
    interactiveBrowserView.webContents.once('did-finish-load', async () => {
      try {
        console.log('📄 Page loaded, injecting capture script...');
        
        await interactiveBrowserView.webContents.executeJavaScript(`
          // Réinitialiser ou créer le tableau d'actions
          if (!window.__workflowActions) {
            window.__workflowActions = [];
            console.log('✅ Initialized window.__workflowActions');
          }
          
          // Helper: générer selector robuste
          function getSelector(element) {
            if (!element) return 'unknown';
            
            // Priorité 1: ID (le plus stable)
            if (element.id) return '#' + element.id;
            
            // Priorité 2: Attribut name pour les inputs
            if (element.name) return \`[name="\${element.name}"]\`;
            
            // Priorité 3: data-testid ou data-* attributes
            if (element.dataset) {
              if (element.dataset.testid) return \`[data-testid="\${element.dataset.testid}"]\`;
              const dataKeys = Object.keys(element.dataset);
              if (dataKeys.length > 0) {
                const firstKey = dataKeys[0];
                return \`[data-\${firstKey}="\${element.dataset[firstKey]}"]\`;
              }
            }
            
            // Priorité 4: Attributs ARIA
            if (element.getAttribute('aria-label')) {
              return \`[aria-label="\${element.getAttribute('aria-label')}"]\`;
            }
            if (element.getAttribute('role')) {
              const role = element.getAttribute('role');
              const tag = element.tagName.toLowerCase();
              return \`\${tag}[role="\${role}"]\`;
            }
            
            const tag = element.tagName ? element.tagName.toLowerCase() : 'unknown';
            
            // Priorité 5: Classes CSS (en filtrant les classes dynamiques/hachées)
            if (element.className && typeof element.className === 'string') {
              const classes = element.className.trim().split(/\s+/).filter(cls => {
                // Filtrer les classes qui semblent dynamiques (contiennent des hash)
                // Ex: EKtkFWMYpwzMKOYr0GYm, LQVY1Jpkk8nyJ6HBWKAk
                return cls.length < 30 && // Pas trop longues
                       !/^[A-Z][a-z0-9]{15,}/.test(cls) && // Pas de pattern hash type React
                       !/^[a-f0-9]{8,}/.test(cls); // Pas de hash hexadécimal
              });
              
              if (classes.length > 0) {
                return tag + '.' + classes.join('.');
              }
            }
            
            // Priorité 6: Full Path (Hierarchy) - NOUVEAU: Fallback robuste
            // Si on n'a rien trouvé de précis, on construit un chemin relatif
            try {
              let path = tag;
              let current = element;
              while (current.parentElement && current.parentElement !== document.body) {
                current = current.parentElement;
                const parentTag = current.tagName.toLowerCase();
                const siblings = Array.from(current.children);
                const index = siblings.indexOf(element);
                
                // Ajouter index si nécessaire
                const sameTagSiblings = siblings.filter(s => s.tagName.toLowerCase() === element.tagName.toLowerCase());
                if (sameTagSiblings.length > 1) {
                   const sameTagIndex = sameTagSiblings.indexOf(element) + 1; // nth-of-type est 1-based
                   path = \`\${parentTag} > \${tag}:nth-of-type(\${sameTagIndex})\`;
                } else {
                   path = \`\${parentTag} > \${tag}\`;
                }
                
                // Si le parent a un ID, on s'arrête là
                if (current.id) {
                   path = \`#\${current.id} > \${path}\`;
                   return path;
                }
                
                // On remonte juste d'un niveau pour ne pas faire des sélecteurs trop longs
                break; 
              }
              return path;
            } catch (e) {
              return tag;
            }
          }
          
          // Helper: extraire informations contextuelles pour un élément
          function getElementContext(element) {
            const context = {};
            
            // Texte visible (limité à 100 caractères)
            const text = (element.innerText || element.textContent || '').trim();
            if (text) {
              context.text = text.substring(0, 100);
            }
            
            // Position dans une liste (si l'élément est dans une liste)
            const parent = element.parentElement;
            if (parent) {
              const siblings = Array.from(parent.children);
              const index = siblings.indexOf(element);
              if (index > 0 && siblings.length > 1) {
                context.index = index;
                context.totalSiblings = siblings.length;
              }
            }
            
            // Attributs ARIA
            if (element.getAttribute('aria-label')) {
              context.ariaLabel = element.getAttribute('aria-label');
            }
            if (element.getAttribute('role')) {
              context.role = element.getAttribute('role');
            }
            
            // Href pour les liens
            if (element.href) {
              context.href = element.href;
            }
            
            return context;
          }
          
          // Fonction pour logger (utilisée pour envoyer au main process)
          function logAction(action) {
            // Stocker dans le tableau local
            window.__workflowActions.push(action);
            
            // IMPORTANT: Log avec un préfixe spécial pour que le main process puisse le détecter
            console.log('[WORKFLOW_ACTION]', JSON.stringify(action));
            
            // Log visible pour debug
            const msg = \`📝 [CAPTURE] \${action.type}: \${action.selector} (total: \${window.__workflowActions.length})\`;
            console.log(msg);
            document.title = '[LOG] ' + msg;
          }
          
          // Capturer les CLICS (phase de capture)
          document.addEventListener('click', (e) => {
            try {
              // NOUVEAU: Capturer la position de scroll AVANT le clic (si scrollé)
              const scrollX = window.scrollX || window.pageXOffset || 0;
              const scrollY = window.scrollY || window.pageYOffset || 0;
              
              // Si la page est scrollée, enregistrer la position
              if (scrollX > 0 || scrollY > 0) {
                // Vérifier si on n'a pas déjà capturé cette position récemment
                if (!window.__lastScrollPosition || 
                    window.__lastScrollPosition.x !== scrollX || 
                    window.__lastScrollPosition.y !== scrollY) {
                  
                  window.__lastScrollPosition = { x: scrollX, y: scrollY };
                  
                  logAction({
                    type: 'scroll',
                    x: scrollX,
                    y: scrollY,
                    timestamp: Date.now()
                  });
                  
                  console.log(\`[LOG] 📜 Captured scroll before click: x=\${scrollX}, y=\${scrollY}\`);
                }
              }
              
              // Puis capturer le clic normalement
              const selector = getSelector(e.target);
              const context = getElementContext(e.target);
              const action = {
                type: 'click',
                selector: selector,
                context: context, // Ajouter les informations contextuelles
                timestamp: Date.now()
              };
              logAction(action);
            } catch (err) {
              console.log('[LOG] ❌ Click capture error: ' + err.message);
            }
          }, true); // true = capture phase
          
          // Capturer les SAISIES
          document.addEventListener('input', (e) => {
            try {
              if (e.target && (e.target.matches('input') || e.target.matches('textarea'))) {
                const selector = getSelector(e.target);
                const action = {
                  type: 'fill',
                  selector: selector,
                  value: e.target.value,
                  timestamp: Date.now()
                };
                logAction(action);
              }
            } catch (err) {
              console.log('[LOG] ❌ Fill capture error: ' + err.message);
            }
          }, true);
          
          // Capturer les SCROLL (avec debounce pour éviter trop d'événements)
          let scrollTimeout;
          document.addEventListener('scroll', (e) => {
            try {
              clearTimeout(scrollTimeout);
              scrollTimeout = setTimeout(() => {
                const action = {
                  type: 'scroll',
                  x: window.scrollX || window.pageXOffset || 0,
                  y: window.scrollY || window.pageYOffset || 0,
                  timestamp: Date.now()
                };
                logAction(action);
              }, 300); // Debounce de 300ms
            } catch (err) {
              console.log('[LOG] ❌ Scroll capture error: ' + err.message);
            }
          }, true);
          
          // Log de confirmation
          console.log('[LOG] ✅ Workflow capture script injected and ready!');
          true; // Retourner true pour confirmer l'exécution
        `);
        
        console.log('✅ Capture script injected into BrowserView');
      } catch (err) {
        console.error('Failed to inject capture script:', err);
      }
    });
    
    await interactiveBrowserView.webContents.loadURL(urlToLoad);
    console.log(`✓ BrowserView loaded for recording: ${urlToLoad}`);
    
    // Synchroniser avec hiddenWindow pour que Playwright puisse capturer
    // On charge aussi la même URL dans hiddenWindow
    try {
      await hiddenWindow.webContents.loadURL(urlToLoad);
      console.log(`✓ hiddenWindow synced to: ${urlToLoad}`);
    } catch (err) {
      console.warn('Could not sync hiddenWindow:', err.message);
    }
    
    // IMPORTANT: Synchroniser les navigations entre BrowserView et hiddenWindow
    // Quand l'utilisateur navigue dans le BrowserView, on met à jour hiddenWindow
    const navigationHandler = async (details) => {
      const newUrl = details.url;
      console.log(`📍 User navigated to: ${newUrl}`);
      
      // Synchroniser avec hiddenWindow
      try {
        if (hiddenWindow && !hiddenWindow.isDestroyed()) {
          await hiddenWindow.webContents.loadURL(newUrl);
          console.log(`✓ hiddenWindow synced to: ${newUrl}`);
        }
      } catch (err) {
        console.warn('Could not sync navigation:', err.message);
      }
    };
    
    // Ré-injecter le script APRÈS chaque chargement de page (pas immédiatement après navigation)
    const reInjectScript = async () => {
      try {
        console.log('📄 Page navigation complete, re-injecting capture script...');
        
        await interactiveBrowserView.webContents.executeJavaScript(`
          // Préserver les actions existantes
          window.__workflowActions = window.__workflowActions || [];
          
          function getSelector(element) {
            if (!element) return 'unknown';
            
            // Priorité 1: ID (le plus stable)
            if (element.id) return '#' + element.id;
            
            // Priorité 2: Attribut name pour les inputs
            if (element.name) return \`[name="\${element.name}"]\`;
            
            // Priorité 3: data-testid ou data-* attributes
            if (element.dataset) {
              if (element.dataset.testid) return \`[data-testid="\${element.dataset.testid}"]\`;
              const dataKeys = Object.keys(element.dataset);
              if (dataKeys.length > 0) {
                const firstKey = dataKeys[0];
                return \`[data-\${firstKey}="\${element.dataset[firstKey]}"]\`;
              }
            }
            
            // Priorité 4: Attributs ARIA
            if (element.getAttribute('aria-label')) {
              return \`[aria-label="\${element.getAttribute('aria-label')}"]\`;
            }
            if (element.getAttribute('role')) {
              const role = element.getAttribute('role');
              const tag = element.tagName.toLowerCase();
              return \`\${tag}[role="\${role}"]\`;
            }
            
            const tag = element.tagName ? element.tagName.toLowerCase() : 'unknown';
            
            // Priorité 5: Classes CSS (en filtrant les classes dynamiques/hachées)
            if (element.className && typeof element.className === 'string') {
              const classes = element.className.trim().split(/\s+/).filter(cls => {
                // Filtrer les classes qui semblent dynamiques (contiennent des hash)
                return cls.length < 30 && 
                       !/^[A-Z][a-z0-9]{15,}/.test(cls) && 
                       !/^[a-f0-9]{8,}/.test(cls);
              });
              
              if (classes.length > 0) {
                return tag + '.' + classes.join('.');
              }
            }
            
            // Priorité 6: Full Path (Hierarchy) - NOUVEAU: Fallback robuste
            try {
              let path = tag;
              let current = element;
              while (current.parentElement && current.parentElement !== document.body) {
                current = current.parentElement;
                const parentTag = current.tagName.toLowerCase();
                const siblings = Array.from(current.children);
                const index = siblings.indexOf(element);
                
                // Ajouter index si nécessaire
                const sameTagSiblings = siblings.filter(s => s.tagName.toLowerCase() === element.tagName.toLowerCase());
                if (sameTagSiblings.length > 1) {
                   const sameTagIndex = sameTagSiblings.indexOf(element) + 1; // nth-of-type est 1-based
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
          
          function getElementContext(element) {
            const context = {};
            
            const text = (element.innerText || element.textContent || '').trim();
            if (text) {
              context.text = text.substring(0, 100);
            }
            
            const parent = element.parentElement;
            if (parent) {
              const siblings = Array.from(parent.children);
              const index = siblings.indexOf(element);
              if (index > 0 && siblings.length > 1) {
                context.index = index;
                context.totalSiblings = siblings.length;
              }
            }
            
            if (element.getAttribute('aria-label')) {
              context.ariaLabel = element.getAttribute('aria-label');
            }
            if (element.getAttribute('role')) {
              context.role = element.getAttribute('role');
            }
            
            if (element.href) {
              context.href = element.href;
            }
            
            return context;
          }
          
          function logAction(action) {
            window.__workflowActions.push(action);
            console.log('[WORKFLOW_ACTION]', JSON.stringify(action));
            const msg = \`📝 [CAPTURE] \${action.type}: \${action.selector} (total: \${window.__workflowActions.length})\`;
            console.log(msg);
            document.title = '[LOG] ' + msg;
          }
          
          // Éviter de rattacher plusieurs fois les mêmes listeners
          if (!window.__captureListenersAttached) {
            document.addEventListener('click', (e) => {
              try {
                // NOUVEAU: Capturer la position de scroll AVANT le clic (si scrollé)
                const scrollX = window.scrollX || window.pageXOffset || 0;
                const scrollY = window.scrollY || window.pageYOffset || 0;
                
                // Si la page est scrollée, enregistrer la position
                if (scrollX > 0 || scrollY > 0) {
                  if (!window.__lastScrollPosition || 
                      window.__lastScrollPosition.x !== scrollX || 
                      window.__lastScrollPosition.y !== scrollY) {
                    
                    window.__lastScrollPosition = { x: scrollX, y: scrollY };
                    
                    logAction({
                      type: 'scroll',
                      x: scrollX,
                      y: scrollY,
                      timestamp: Date.now()
                    });
                    
                    console.log(\`[LOG] 📜 Captured scroll before click: x=\${scrollX}, y=\${scrollY}\`);
                  }
                }
                
                // Puis capturer le clic
                const selector = getSelector(e.target);
                const context = getElementContext(e.target);
                logAction({
                  type: 'click',
                  selector: selector,
                  context: context,
                  timestamp: Date.now()
                });
              } catch (err) {
                console.log('[LOG] ❌ Click error: ' + err.message);
              }
            }, true);
            
            document.addEventListener('input', (e) => {
              try {
                if (e.target && (e.target.matches('input') || e.target.matches('textarea'))) {
                  const selector = getSelector(e.target);
                  logAction({
                    type: 'fill',
                    selector: selector,
                    value: e.target.value,
                    timestamp: Date.now()
                  });
                }
              } catch (err) {
                console.log('[LOG] ❌ Fill error: ' + err.message);
              }
            }, true);
            
            let scrollTimeout;
            document.addEventListener('scroll', (e) => {
              try {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                  logAction({
                    type: 'scroll',
                    x: window.scrollX || window.pageXOffset || 0,
                    y: window.scrollY || window.pageYOffset || 0,
                    timestamp: Date.now()
                  });
                }, 300);
              } catch (err) {
                console.log('[LOG] ❌ Scroll error: ' + err.message);
              }
            }, true);
            
            window.__captureListenersAttached = true;
            console.log('[LOG] ✅ Capture script re-injected after navigation');
          } else {
            console.log('[LOG] ⚠️ Listeners already attached, skipping');
          }
          true;
        `);
      } catch (err) {
        console.warn('Could not re-inject capture script:', err.message);
      }
    };
    
    interactiveBrowserView.webContents.on('did-navigate', navigationHandler);
    interactiveBrowserView.webContents.on('did-navigate-in-page', navigationHandler);
    interactiveBrowserView.webContents.on('did-finish-load', reInjectScript);
    
    // NOUVEAU: Capturer les messages console pour récupérer les actions en temps réel
    interactiveBrowserView.webContents.on('console-message', (event, level, message, line, sourceId) => {
      // Détecter les messages d'action
      if (message.startsWith('[WORKFLOW_ACTION]')) {
        try {
          const jsonStr = message.replace('[WORKFLOW_ACTION] ', '');
          const action = JSON.parse(jsonStr);
          capturedActionsBuffer.push(action);
          console.log(`[CAPTURED] ${action.type}: ${action.selector} (buffer: ${capturedActionsBuffer.length})`);
        } catch (err) {
          console.error('Failed to parse workflow action:', err);
        }
      }
    });
    
    // Logger les changements de titre (qui contiennent nos logs de capture)
    interactiveBrowserView.webContents.on('page-title-updated', (event, title) => {
      if (title.startsWith('[LOG]')) {
        console.log(`[BrowserView] ${title.replace('[LOG] ', '')}`);
      }
    });
    
    // Stocker les handlers pour cleanup
    interactiveBrowserView._navigationHandler = navigationHandler;
    interactiveBrowserView._reInjectScript = reInjectScript;
    
    // Auto-resize sur changement de taille de fenêtre
    mainWindow.on('resize', updateBrowserViewBounds);
    
    return { success: true, url: urlToLoad };
    
  } catch (error) {
    console.error('Error enabling recording mode:', error);
    return { success: false, error: error.message };
  }
});

/**
 * NOUVEAU: Récupérer les actions capturées dans le BrowserView
 */
ipcMain.handle('get-captured-actions', async (event) => {
  try {
    // NOUVEAU: Retourner les actions du buffer (capturées en temps réel via console-message)
    const actions = [...capturedActionsBuffer]; // Copie du buffer
    
    console.log(`✅ Retrieved ${actions.length} captured actions from buffer (real-time)`);
    
    // Vider le buffer pour le prochain enregistrement
    capturedActionsBuffer = [];
    
    return { success: true, actions };
    
  } catch (error) {
    console.error('Error getting captured actions:', error);
    return { success: false, actions: [], error: error.message };
  }
});

/**
 * NOUVEAU: Désactiver le mode recording : fermer BrowserView
 */
ipcMain.handle('disable-recording-mode', async (event) => {
  try {
    console.log('⏹️ Disabling recording mode...');
    
    if (interactiveBrowserView && mainWindow) {
      // Obtenir l'URL finale (pour info uniquement, le workflow est déjà enregistré)
      const finalUrl = interactiveBrowserView.webContents.getURL();
      console.log(`Final URL after recording: ${finalUrl}`);
      
      // Retirer les event listeners
      if (interactiveBrowserView._navigationHandler) {
        interactiveBrowserView.webContents.removeListener('did-navigate', interactiveBrowserView._navigationHandler);
        interactiveBrowserView.webContents.removeListener('did-navigate-in-page', interactiveBrowserView._navigationHandler);
        delete interactiveBrowserView._navigationHandler;
      }
      if (interactiveBrowserView._reInjectScript) {
        interactiveBrowserView.webContents.removeListener('did-finish-load', interactiveBrowserView._reInjectScript);
        delete interactiveBrowserView._reInjectScript;
      }
      
      // Retirer le BrowserView
      mainWindow.setBrowserView(null);
      
      // Fermer le webContents
      if (!interactiveBrowserView.webContents.isDestroyed()) {
        interactiveBrowserView.webContents.close();
      }
      
      interactiveBrowserView = null;
      
      // Retirer l'event listener resize
      mainWindow.removeListener('resize', updateBrowserViewBounds);
      
      console.log('✓ Recording mode disabled');
      
      return { success: true, finalUrl };
    }
    
    return { success: true };
    
  } catch (error) {
    console.error('Error disabling recording mode:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Mettre à jour les dimensions du BrowserView sur resize
 */
function updateBrowserViewBounds() {
  if (interactiveBrowserView && mainWindow) {
    const bounds = mainWindow.getBounds();
    const halfWidth = Math.floor(bounds.width / 2);
    
    interactiveBrowserView.setBounds({
      x: halfWidth,
      y: 0,
      width: halfWidth,
      height: bounds.height,
    });
  }
}

// Activer le CDP
app.commandLine.appendSwitch('remote-debugging-port', String(CONFIG.CDP_PORT));

app.whenReady().then(async () => {
  try {
    console.log('App ready, creating windows...');
    
    // 1. Créer la fenêtre CACHÉE pour Playwright
    await createHiddenWindow();
    
    // 2. Créer la fenêtre VISIBLE pour l'UI
    await createMainWindow();
    
    console.log(`CDP enabled on port: ${CONFIG.CDP_PORT}`);
    
    // 3. Lancer le serveur Python
    console.log('About to start Python server...');
    await startPythonServer(CONFIG.CDP_PORT);
    console.log('Python server started successfully!');
    
    // 4. Connecter au serveur Python via WebSocket
    console.log('Setting timeout for WebSocket connection...');
    setTimeout(() => {
      console.log('Timeout triggered! Connecting to WebSocket server:', `ws://localhost:${CONFIG.WS_PORT}`);
      try {
        connectToWebSocketServer();
        console.log('WebSocket connection initiated');
      } catch (err) {
        console.error('Error calling connectToWebSocketServer:', err);
      }
    }, 2000);
    console.log('setTimeout registered');
    
  } catch (error) {
    console.error('Startup error:', error);
  }
}).catch(console.error);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createHiddenWindow();
    createMainWindow();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (pythonProcess) {
    console.log('Killing Python server...');
    pythonProcess.kill();
    pythonProcess = null;
  }
  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }
});
