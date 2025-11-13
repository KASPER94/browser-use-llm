// src/renderer/components/ChatPanel.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Message, BrowserGymStatus } from '../types';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { WorkflowDropdown } from './WorkflowDropdown';
import { ControlMode } from '../hooks/useBrowserGym';
import { useWorkflows } from '../hooks/useWorkflows';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  status: BrowserGymStatus;
  controlMode: ControlMode;
  onPauseAgent: () => void;
  onResumeAgent: () => void;
  isAgentBusy: boolean;
  workflowsHook: ReturnType<typeof useWorkflows>;
}

export function ChatPanel({ 
  messages, 
  onSendMessage, 
  status, 
  controlMode, 
  onPauseAgent, 
  onResumeAgent,
  isAgentBusy,
  workflowsHook 
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll vers le bas quand nouveaux messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim() && status.websocket === 'connected') {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isDisabled = status.websocket !== 'connected' || status.agent === 'executing';

  // Déterminer si le bouton pause/resume doit être affiché
  const showControlButton = status.websocket === 'connected' && status.environment === 'ready';
  // FIX: Afficher "Take Control" dès que l'environnement est prêt et qu'on est en mode agent
  // (pas seulement quand isAgentBusy = true, sinon le bouton disparaît entre les actions)
  const canPause = controlMode === 'agent' && status.environment === 'ready';
  const canResume = controlMode === 'manual';

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>BrowserGym Agent</h2>
        <div className="status-indicators">
          <span className={`indicator ${status.websocket}`}>
            {status.websocket === 'connected' ? '🟢' : '🔴'} Server
          </span>
          <span className={`indicator ${status.agent}`}>
            {status.agent === 'executing' ? '⚡' : '💤'} Agent
          </span>
          {controlMode === 'manual' && (
            <span className="indicator manual">
              🖐️ Manual
            </span>
          )}
        </div>
      </div>

      <div className="messages-container">
        <MessageList messages={messages} />
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        {/* NOUVEAU: Bouton Take Control / Resume */}
        {showControlButton && (
          <div className="control-button-container">
            {canPause && (
              <button 
                className="control-button pause-button"
                onClick={onPauseAgent}
                title="Take manual control"
              >
                <span className="button-icon">🖐️</span>
                <span className="button-text">Take Control</span>
              </button>
            )}
            {canResume && (
              <button 
                className="control-button resume-button"
                onClick={onResumeAgent}
                title="Resume agent execution"
              >
                <span className="button-icon">▶️</span>
                <span className="button-text">Resume Agent</span>
              </button>
            )}
          </div>
        )}
        
        {/* NOUVEAU: Workflow Dropdown */}
        <WorkflowDropdown
          workflows={workflowsHook.workflows}
          isPlaying={workflowsHook.isPlaying}
          onPlay={workflowsHook.playWorkflow}
          disabled={status.websocket !== 'connected' || status.agent === 'executing'}
        />
        
        <InputBox
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          placeholder={
            status.websocket !== 'connected'
              ? 'Waiting for connection...'
              : controlMode === 'manual'
              ? 'Manual control mode - Click Resume to continue'
              : status.agent === 'executing'
              ? 'Agent is working...'
              : 'Type your instruction...'
          }
        />
      </div>
    </div>
  );
}

