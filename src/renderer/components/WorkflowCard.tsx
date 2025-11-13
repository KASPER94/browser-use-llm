// src/renderer/components/WorkflowCard.tsx

import React from 'react';
import { WorkflowSummary } from '../types';

interface WorkflowCardProps {
  workflow: WorkflowSummary;
  isPlaying: boolean;
  onPlay: () => void;
  onDelete: () => void;
}

export function WorkflowCard({ workflow, isPlaying, onPlay, onDelete }: WorkflowCardProps) {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffHours < 48) return 'Yesterday';
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="workflow-card">
      <div className="card-header">
        <h4 className="card-title">{workflow.name}</h4>
        <button className="btn-delete" onClick={onDelete} title="Delete workflow">
          🗑️
        </button>
      </div>

      {workflow.description && (
        <p className="card-description">{workflow.description}</p>
      )}

      <div className="card-meta">
        <span className="meta-item">
          <span className="meta-icon">🔢</span>
          {workflow.action_count} actions
        </span>
        <span className="meta-item">
          <span className="meta-icon">⏱️</span>
          {formatDuration(workflow.duration)}
        </span>
      </div>

      <div className="card-meta">
        <span className="meta-item">
          <span className="meta-icon">📅</span>
          {formatDate(workflow.created_at)}
        </span>
      </div>

      {workflow.start_url && (
        <div className="card-url">
          <span className="meta-icon">🌐</span>
          <span className="url-text" title={workflow.start_url}>
            {new URL(workflow.start_url).hostname}
          </span>
        </div>
      )}

      <button
        className="btn-play"
        onClick={onPlay}
        disabled={isPlaying}
      >
        {isPlaying ? '⏳ Playing...' : '▶️ Play Workflow'}
      </button>
    </div>
  );
}

