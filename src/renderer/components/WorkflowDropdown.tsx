// src/renderer/components/WorkflowDropdown.tsx

import React, { useState } from 'react';
import { WorkflowSummary } from '../types';

interface WorkflowDropdownProps {
  workflows: WorkflowSummary[];
  isPlaying: boolean;
  onPlay: (workflowId: string) => void;
  disabled: boolean;
}

export function WorkflowDropdown({ workflows, isPlaying, onPlay, disabled }: WorkflowDropdownProps) {
  const [selectedWorkflowId, setSelectedWorkflowId] = useState('');

  const handlePlay = () => {
    if (selectedWorkflowId && !isPlaying) {
      onPlay(selectedWorkflowId);
    }
  };

  if (workflows.length === 0) {
    return null; // Don't show dropdown if no workflows
  }

  return (
    <div className="workflow-dropdown">
      <select
        className="workflow-select"
        value={selectedWorkflowId}
        onChange={(e) => setSelectedWorkflowId(e.target.value)}
        disabled={disabled || isPlaying}
      >
        <option value="">Select a workflow...</option>
        {workflows.map((workflow) => (
          <option key={workflow.id} value={workflow.id}>
            {workflow.name} ({workflow.action_count} actions)
          </option>
        ))}
      </select>
      <button
        className="workflow-play-btn"
        onClick={handlePlay}
        disabled={!selectedWorkflowId || isPlaying || disabled}
        title={isPlaying ? 'Workflow is playing...' : 'Play selected workflow'}
      >
        {isPlaying ? '⏳' : '▶️'}
      </button>
    </div>
  );
}

