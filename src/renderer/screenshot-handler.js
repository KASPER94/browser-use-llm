// screenshot-handler.js - Affiche les screenshots reçus du serveur Python

(function() {
  console.log('📸 Screenshot handler initializing...');
  
  const screenshotImg = document.getElementById('browser-screenshot');
  const loadingMessage = document.getElementById('loading-message');
  const screenshotDisplay = document.getElementById('screenshot-display'); // Correction du nom
  
  if (!screenshotImg || !loadingMessage || !screenshotDisplay) {
    console.error('Screenshot elements not found!');
    return;
  }

  // NOUVEAU : Fonctions pour contrôler la visibilité du screenshot
  window.screenshotHandler = {
    hide: () => {
      screenshotDisplay.style.display = 'none';
      console.log('📸 Screenshot hidden (interactive mode)');
    },
    show: () => {
      screenshotDisplay.style.display = 'flex'; // Flex pour garder le layout
      console.log('📸 Screenshot visible (agent mode)');
    }
  };

  // Écouter les screenshots via window.electronAPI
  if (window.electronAPI && window.electronAPI.onPythonMessage) {
    window.electronAPI.onPythonMessage((data) => {
      if (data.type === 'screenshot') {
        // Afficher le screenshot
        const base64Image = data.data;
        screenshotImg.src = `data:image/png;base64,${base64Image}`;
        screenshotImg.style.display = 'block';
        loadingMessage.style.display = 'none';
        
        console.log('📸 Screenshot updated');
      }
    });
    
    console.log('✅ Screenshot handler ready');
  } else {
    console.error('electronAPI not available for screenshots!');
  }
})();

