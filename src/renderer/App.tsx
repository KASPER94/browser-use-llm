// src/renderer/App.tsx
import React, { useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { StatusBar } from './components/StatusBar';
import { WorkflowTab } from './components/WorkflowTab';
import { useBrowserGym } from './hooks/useBrowserGym';
import { useWorkflows } from './hooks/useWorkflows';
import './styles/index.css';

type Tab = 'agent' | 'workflows';

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('agent');
  
  const { 
    messages, 
    status, 
    sendMessage, 
    resetEnvironment, 
    controlMode, 
    pauseAgent, 
    resumeAgent,
    isAgentBusy 
  } = useBrowserGym();

  const workflowsHook = useWorkflows();

  return (
    <div className="app-container-overlay">
      <div className="chat-overlay">
        <StatusBar status={status} onReset={resetEnvironment} />
        
        {/* Navigation Tabs */}
        <div className="tab-navigation">
          <button 
            className={`tab-button ${activeTab === 'agent' ? 'active' : ''}`}
            onClick={() => setActiveTab('agent')}
          >
            🤖 Agent
          </button>
          <button 
            className={`tab-button ${activeTab === 'workflows' ? 'active' : ''}`}
            onClick={() => setActiveTab('workflows')}
          >
            📹 Workflows
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'agent' && (
          <ChatPanel 
            messages={messages} 
            onSendMessage={sendMessage} 
            status={status} 
            controlMode={controlMode}
            onPauseAgent={pauseAgent}
            onResumeAgent={resumeAgent}
            isAgentBusy={isAgentBusy}
            workflowsHook={workflowsHook}
          />
        )}

        {activeTab === 'workflows' && (
          <WorkflowTab {...workflowsHook} />
        )}
      </div>
    </div>
  );
}
