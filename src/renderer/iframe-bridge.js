// iframe-bridge.js - Communication entre page principale et iframe chat
// Ce script s'exécute dans la PAGE PRINCIPALE et fait le pont avec l'iframe

(function() {
  console.log('🌉 Iframe bridge initializing...');
  
  // Attendre que l'iframe soit chargée
  window.addEventListener('DOMContentLoaded', () => {
    const chatIframe = document.getElementById('chat-iframe');
    
    if (!chatIframe) {
      console.error('Chat iframe not found!');
      return;
    }

    console.log('📡 Chat iframe found, setting up communication bridge');

    // Transférer les événements du main process vers l'iframe
    if (window.electronAPI) {
      // WebSocket status
      window.electronAPI.onWebSocketStatus((status) => {
        console.log('📨 Forwarding WebSocket status to iframe:', status);
        chatIframe.contentWindow.postMessage({
          type: 'websocket-status',
          status: status
        }, '*');
      });

      // Python messages
      window.electronAPI.onPythonMessage((data) => {
        console.log('📨 Forwarding Python message to iframe:', data.type);
        chatIframe.contentWindow.postMessage({
          type: 'python-message',
          data: data
        }, '*');
      });
    }

    // Écouter les messages de l'iframe et les transférer au main process
    window.addEventListener('message', (event) => {
      if (event.source !== chatIframe.contentWindow) return;

      const { type, payload } = event.data;
      console.log('📥 Received from iframe:', type);

      if (type === 'send-user-message' && window.electronAPI) {
        window.electronAPI.sendUserMessage(payload);
      } else if (type === 'reset-environment' && window.electronAPI) {
        window.electronAPI.resetEnvironment();
      }
    });

    console.log('✅ Iframe bridge ready');
  });
})();

