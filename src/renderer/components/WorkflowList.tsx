// src/renderer/components/WorkflowList.tsx

import React from 'react';
import { WorkflowCard } from './WorkflowCard';
import { WorkflowSummary } from '../types';

interface WorkflowListProps {
  workflows: WorkflowSummary[];
  isPlaying: boolean;
  onPlay: (workflowId: string) => void;
  onDelete: (workflowId: string) => void;
  onRefresh: () => void;
}

export function WorkflowList({ workflows, isPlaying, onPlay, onDelete, onRefresh }: WorkflowListProps) {
  if (workflows.length === 0) {
    return (
      <div className="workflow-list empty">
        <div className="empty-state">
          <span className="empty-icon">📁</span>
          <p>No workflows yet</p>
          <p className="empty-hint">Record your first workflow to get started!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="workflow-list">
      <div className="list-header">
        <h3>Saved Workflows ({workflows.length})</h3>
        <button className="btn-refresh" onClick={onRefresh} title="Refresh list">
          🔄
        </button>
      </div>

      <div className="workflow-grid">
        {workflows.map((workflow) => (
          <WorkflowCard
            key={workflow.id}
            workflow={workflow}
            isPlaying={isPlaying}
            onPlay={() => onPlay(workflow.id)}
            onDelete={() => {
              if (confirm(`Delete workflow "${workflow.name}"?`)) {
                onDelete(workflow.id);
              }
            }}
          />
        ))}
      </div>
    </div>
  );
}

