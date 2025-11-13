// src/renderer/hooks/useBrowserGym.ts
import { useState, useEffect, useCallback } from 'react';
import { Message, BrowserGymStatus, PythonMessage } from '../types';

export type ControlMode = 'agent' | 'manual';

export function useBrowserGym() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<BrowserGymStatus>({
    websocket: 'disconnected',
    agent: 'idle',
    environment: 'not_initialized',
  });
  const [cdpPort] = useState<number>(9222);
  const [isAgentBusy, setIsAgentBusy] = useState<boolean>(false);
  const [controlMode, setControlMode] = useState<ControlMode>('agent'); // NOUVEAU

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    addMessage({
      role: 'system',
      content,
      timestamp: Date.now(),
    });
  }, [addMessage]);

  useEffect(() => {
    // Écouter les messages du serveur Python
    window.electronAPI.onPythonMessage((data: PythonMessage) => {
      console.log('Received Python message:', data);

      // Ignorer les screenshots (gérés par screenshot-handler.js)
      if (data.type === 'screenshot') {
        return;
      }

      switch (data.type) {
        case 'init_complete':
          setStatus(prev => ({ ...prev, environment: 'ready' }));
          addSystemMessage('Environment initialized successfully');
          setIsAgentBusy(false);
          break;

        case 'agent_message':
          if (data.message) {
            addMessage({
              role: 'assistant',
              content: data.message,
              timestamp: Date.now(),
            });
            setIsAgentBusy(false);
            setStatus(prev => ({ ...prev, agent: 'idle' })); // IMPORTANT : remettre à idle !
          }
          break;
        
        case 'agent_paused':
          // NOUVEAU: Agent mis en pause
          setIsAgentBusy(false);
          setStatus(prev => ({ ...prev, agent: 'paused' }));
          addSystemMessage('✋ Agent paused - You have control');
          break;
        
        case 'agent_resumed':
          // NOUVEAU: Agent a repris
          setIsAgentBusy(true);
          setStatus(prev => ({ ...prev, agent: 'executing' }));
          addSystemMessage('▶️ Agent resumed execution');
          break;

        case 'observation':
          console.log('Observation:', data.data);
          setIsAgentBusy(false);
          break;

        case 'error':
          addMessage({
            role: 'error',
            content: data.error || 'Unknown error',
            timestamp: Date.now(),
          });
          setStatus(prev => ({ ...prev, agent: 'idle' })); // Remettre à idle aussi en cas d'erreur
          setIsAgentBusy(false);
          break;

        case 'status':
          if (data.data?.agent_status) {
            setStatus(prev => ({ ...prev, agent: data.data.agent_status }));
          }
          break;
      }
    });

    // Écouter le statut WebSocket
    window.electronAPI.onWebSocketStatus((wsStatus: string) => {
      console.log('WebSocket status:', wsStatus);
      setStatus(prev => ({
        ...prev,
        websocket: wsStatus as 'connected' | 'disconnected',
      }));

      if (wsStatus === 'connected') {
        addSystemMessage('Connected to BrowserGym server');
      } else {
        addSystemMessage('Disconnected from server');
      }
    });

    // Nettoyer les listeners au démontage
    return () => {
      window.electronAPI.removeAllListeners();
    };
  }, [addMessage, addSystemMessage]);

  const sendMessage = useCallback((content: string) => {
    // Ajouter le message à l'UI
    addMessage({
      role: 'user',
      content,
      timestamp: Date.now(),
    });

    // Envoyer au serveur Python
    window.electronAPI.sendUserMessage(content);

    // Mettre à jour le statut
    setIsAgentBusy(true);
    setStatus(prev => ({ ...prev, agent: 'executing' }));
  }, [addMessage]);

  const resetEnvironment = useCallback(() => {
    setMessages([]);
    setStatus(prev => ({ ...prev, environment: 'resetting', agent: 'idle' }));
    window.electronAPI.resetEnvironment();
    addSystemMessage('Resetting environment...');
  }, [addSystemMessage]);

  // NOUVEAU: Fonctions de contrôle manuel
  const pauseAgent = useCallback(async () => {
    console.log('Pausing agent...');
    window.electronAPI.sendUserMessage(JSON.stringify({ type: 'pause_agent' }));
    setControlMode('manual');
    
    // Cacher le screenshot
    if ((window as any).screenshotHandler) {
      (window as any).screenshotHandler.hide();
    }
    
    // Activer le BrowserView interactif
    try {
      const result = await window.electronAPI.enableInteractiveMode();
      if (result.success) {
        console.log('✓ Interactive mode enabled:', result.url);
      } else {
        console.error('Failed to enable interactive mode:', result.error);
      }
    } catch (error) {
      console.error('Error enabling interactive mode:', error);
    }
  }, []);

  const resumeAgent = useCallback(async () => {
    console.log('Resuming agent...');
    
    // Désactiver le BrowserView interactif
    try {
      const result = await window.electronAPI.disableInteractiveMode();
      if (result.success) {
        console.log('✓ Interactive mode disabled. Final URL:', result.finalUrl);
      } else {
        console.error('Failed to disable interactive mode:', result.error);
      }
    } catch (error) {
      console.error('Error disabling interactive mode:', error);
    }
    
    // Réafficher le screenshot
    if ((window as any).screenshotHandler) {
      (window as any).screenshotHandler.show();
    }
    
    window.electronAPI.sendUserMessage(JSON.stringify({ type: 'resume_agent' }));
    setControlMode('agent');
  }, []);

  return {
    messages,
    status,
    sendMessage,
    resetEnvironment,
    cdpPort,
    isAgentBusy,
    controlMode,      // NOUVEAU
    setControlMode,   // NOUVEAU
    pauseAgent,       // NOUVEAU
    resumeAgent,      // NOUVEAU
  };
}
