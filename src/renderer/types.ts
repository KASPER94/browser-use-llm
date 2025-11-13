// src/renderer/types.ts

export interface Message {
  role: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: number;
}

export interface BrowserGymStatus {
  websocket: 'connected' | 'disconnected' | 'connecting';
  agent: 'idle' | 'executing' | 'error' | 'paused'; // NOUVEAU: ajout de 'paused'
  environment: 'ready' | 'resetting' | 'not_initialized';
}

export interface PythonMessage {
  type: 'observation' | 'agent_message' | 'error' | 'status' | 'init_complete' | 'screenshot' | 'agent_paused' | 'agent_resumed' | 'recording_started' | 'recording_stopped' | 'workflows_list' | 'workflow_data' | 'workflow_completed' | 'workflow_deleted';
  data?: any;
  message?: string;
  error?: string;
}

// ===== NOUVEAU: Types pour Workflows =====

export interface WorkflowAction {
  type: 'goto' | 'click' | 'fill';
  selector?: string;
  value?: string;
  url?: string;
  text?: string;
  timestamp?: number;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  created_at: string;
  start_url: string;
  actions: WorkflowAction[];
  duration: number;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  created_at: string;
  action_count: number;
  duration: number;
  start_url: string;
}

// Types pour l'API Electron exposée
declare global {
  interface Window {
    electronAPI: {
      sendUserMessage: (message: string) => void;
      executeAction: (action: string) => void;
      resetEnvironment: () => void;
      enableInteractiveMode: () => Promise<{ success: boolean; url?: string; error?: string }>;
      disableInteractiveMode: () => Promise<{ success: boolean; finalUrl?: string; error?: string }>;
      enableRecordingMode: () => Promise<{ success: boolean; url?: string; error?: string }>;
      disableRecordingMode: () => Promise<{ success: boolean; finalUrl?: string; error?: string }>;
      getCapturedActions: () => Promise<{ success: boolean; actions: any[]; error?: string }>;
      onPythonMessage: (callback: (data: PythonMessage) => void) => void;
      onWebSocketStatus: (callback: (status: string) => void) => void;
      removeAllListeners: () => void;
    };
  }
}

export {};

