// inject_navigation.js
// Script à injecter pour créer un iframe de navigation dans #browser-content

(function() {
  const browserDiv = document.querySelector('#browser-content');
  if (!browserDiv) {
    console.error('No #browser-content div found!');
    return;
  }

  // Créer un iframe pour la navigation
  const navFrame = document.createElement('iframe');
  navFrame.id = 'navigation-frame';
  navFrame.style.width = '100%';
  navFrame.style.height = '100%';
  navFrame.style.border = 'none';
  navFrame.src = 'about:blank';

  browserDiv.appendChild(navFrame);

  console.log('Navigation iframe created in #browser-content');
})();

