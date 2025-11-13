// preload.js - Script de préchargement (sécurité)
const { contextBridge, ipcRenderer } = require('electron');

// Exposer une API sécurisée à l'UI React
contextBridge.exposeInMainWorld('electronAPI', {
  // Envoyer un message utilisateur
  sendUserMessage: (message) => {
    ipcRenderer.send('send-user-message', message);
  },

  // Exécuter une action
  executeAction: (action) => {
    ipcRenderer.send('execute-action', action);
  },

  // Réinitialiser l'environnement
  resetEnvironment: () => {
    ipcRenderer.send('reset-environment');
  },

  // NOUVEAU : Activer le mode interactif (BrowserView)
  enableInteractiveMode: () => {
    return ipcRenderer.invoke('enable-interactive-mode');
  },

  // NOUVEAU : Désactiver le mode interactif
  disableInteractiveMode: () => {
    return ipcRenderer.invoke('disable-interactive-mode');
  },

  // NOUVEAU : Activer le mode recording (BrowserView pour workflow)
  enableRecordingMode: () => {
    return ipcRenderer.invoke('enable-recording-mode');
  },

  // NOUVEAU : Désactiver le mode recording
  disableRecordingMode: () => {
    return ipcRenderer.invoke('disable-recording-mode');
  },

  // Écouter les messages du serveur Python
  onPythonMessage: (callback) => {
    ipcRenderer.on('python-message', (event, data) => {
      callback(data);
    });
  },

  // Écouter le statut WebSocket
  onWebSocketStatus: (callback) => {
    ipcRenderer.on('websocket-status', (event, status) => {
      callback(status);
    });
  },

  // Nettoyer les listeners
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('python-message');
    ipcRenderer.removeAllListeners('websocket-status');
    ipcRenderer.removeAllListeners('reset-environment');
  },
  
  // NOUVEAU: Récupérer les actions capturées
  getCapturedActions: () => ipcRenderer.invoke('get-captured-actions'),
});

