// src/renderer/components/WorkflowRecorder.tsx

import React, { useState } from 'react';

interface WorkflowRecorderProps {
  isRecording: boolean;
  onStartRecording: () => void;
  onStopRecording: (workflowName?: string) => void;
}

export function WorkflowRecorder({ isRecording, onStartRecording, onStopRecording }: WorkflowRecorderProps) {
  const [workflowName, setWorkflowName] = useState('');
  const [showNameInput, setShowNameInput] = useState(false);

  const handleStart = () => {
    onStartRecording();
    setShowNameInput(false);
    setWorkflowName('');
  };

  const handleStop = () => {
    setShowNameInput(true);
  };

  const handleSave = () => {
    const name = workflowName.trim() || `Workflow ${new Date().toLocaleString()}`;
    onStopRecording(name);
    setShowNameInput(false);
    setWorkflowName('');
  };

  const handleCancel = () => {
    setShowNameInput(false);
    setWorkflowName('');
  };

  if (showNameInput) {
    return (
      <div className="workflow-recorder recording-complete">
        <h3>✅ Recording Complete</h3>
        <p>Give your workflow a name:</p>
        <input
          type="text"
          className="workflow-name-input"
          placeholder="e.g., Login to GitHub"
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
            if (e.key === 'Escape') handleCancel();
          }}
          autoFocus
        />
        <div className="recorder-actions">
          <button className="btn-primary" onClick={handleSave}>
            💾 Save Workflow
          </button>
          <button className="btn-secondary" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`workflow-recorder ${isRecording ? 'recording' : ''}`}>
      {isRecording ? (
        <>
          <div className="recording-indicator">
            <span className="rec-dot pulsing"></span>
            <span className="rec-text">Recording in progress...</span>
          </div>
          <p className="recording-hint">
            Navigate, click, and fill forms. Your actions are being recorded.
          </p>
          <button className="btn-stop" onClick={handleStop}>
            ⏹️ Stop Recording
          </button>
        </>
      ) : (
        <>
          <p className="recorder-description">
            Click the button below to start recording your browser actions.
          </p>
          <button className="btn-record" onClick={handleStart}>
            🎬 New Recording
          </button>
        </>
      )}
    </div>
  );
}

