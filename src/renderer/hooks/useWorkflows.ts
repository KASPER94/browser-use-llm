// src/renderer/hooks/useWorkflows.ts

import { useState, useEffect, useCallback } from 'react';
import { WorkflowSummary, Workflow, PythonMessage } from '../types';

export function useWorkflows() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null);

  // Écouter les messages Python liés aux workflows
  useEffect(() => {
    const handlePythonMessage = (data: PythonMessage) => {
      switch (data.type) {
        case 'recording_started':
          setIsRecording(true);
          // NOUVEAU: Ouvrir le BrowserView pour recording
          window.electronAPI.enableRecordingMode()
            .then(result => {
              if (result.success) {
                console.log('✓ Recording BrowserView opened:', result.url);
              } else {
                console.error('Failed to open recording BrowserView:', result.error);
              }
            });
          break;

        case 'recording_stopped':
          setIsRecording(false);
          // NOUVEAU: Fermer le BrowserView
          window.electronAPI.disableRecordingMode()
            .then(result => {
              if (result.success) {
                console.log('✓ Recording BrowserView closed');
              }
            });
          // Rafraîchir la liste des workflows
          refreshWorkflows();
          break;

        case 'workflows_list':
          if (data.data?.workflows) {
            setWorkflows(data.data.workflows);
          }
          break;

        case 'workflow_data':
          if (data.data?.workflow) {
            setCurrentWorkflow(data.data.workflow);
          }
          break;

        case 'workflow_completed':
          setIsPlaying(false);
          break;

        case 'workflow_deleted':
          // Rafraîchir la liste après suppression
          refreshWorkflows();
          break;
      }
    };

    window.electronAPI.onPythonMessage(handlePythonMessage);
  }, []);

  // Démarrer l'enregistrement
  const startRecording = useCallback(() => {
    window.electronAPI.sendUserMessage(JSON.stringify({ type: 'start_recording' }));
  }, []);

  // Arrêter l'enregistrement
  const stopRecording = useCallback(async (workflowName?: string) => {
    // NOUVEAU: Récupérer les actions capturées depuis le BrowserView
    try {
      const result = await window.electronAPI.getCapturedActions();
      const capturedActions = result.success ? result.actions : [];
      
      console.log(`📦 Retrieved ${capturedActions.length} captured actions from BrowserView`);
      
      // Envoyer stop_recording avec les actions capturées
      window.electronAPI.sendUserMessage(JSON.stringify({
        type: 'stop_recording',
        workflow_name: workflowName || `Workflow ${Date.now()}`,
        captured_actions: capturedActions
      }));
    } catch (error) {
      console.error('Failed to get captured actions:', error);
      // Envoyer quand même stop_recording sans actions
      window.electronAPI.sendUserMessage(JSON.stringify({
        type: 'stop_recording',
        workflow_name: workflowName || `Workflow ${Date.now()}`,
        captured_actions: []
      }));
    }
  }, []);

  // Lister les workflows
  const refreshWorkflows = useCallback(() => {
    window.electronAPI.sendUserMessage(JSON.stringify({ type: 'list_workflows' }));
  }, []);

  // Obtenir un workflow par ID
  const getWorkflow = useCallback((workflowId: string) => {
    window.electronAPI.sendUserMessage(JSON.stringify({
      type: 'get_workflow',
      workflow_id: workflowId
    }));
  }, []);

  // Jouer un workflow
  const playWorkflow = useCallback((workflowId: string) => {
    setIsPlaying(true);
    window.electronAPI.sendUserMessage(JSON.stringify({
      type: 'play_workflow',
      workflow_id: workflowId
    }));
  }, []);

  // Supprimer un workflow
  const deleteWorkflow = useCallback((workflowId: string) => {
    window.electronAPI.sendUserMessage(JSON.stringify({
      type: 'delete_workflow',
      workflow_id: workflowId
    }));
  }, []);

  // Charger la liste des workflows au montage
  useEffect(() => {
    refreshWorkflows();
  }, [refreshWorkflows]);

  return {
    workflows,
    isRecording,
    isPlaying,
    currentWorkflow,
    startRecording,
    stopRecording,
    refreshWorkflows,
    getWorkflow,
    playWorkflow,
    deleteWorkflow,
  };
}

