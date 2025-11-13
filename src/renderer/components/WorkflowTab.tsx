// src/renderer/components/WorkflowTab.tsx

import React from 'react';
import { WorkflowRecorder } from './WorkflowRecorder';
import { WorkflowList } from './WorkflowList';
import { WorkflowSummary, Workflow } from '../types';

interface WorkflowTabProps {
  workflows: WorkflowSummary[];
  isRecording: boolean;
  isPlaying: boolean;
  currentWorkflow: Workflow | null;
  startRecording: () => void;
  stopRecording: (workflowName?: string) => void;
  refreshWorkflows: () => void;
  getWorkflow: (workflowId: string) => void;
  playWorkflow: (workflowId: string) => void;
  deleteWorkflow: (workflowId: string) => void;
}

export function WorkflowTab(props: WorkflowTabProps) {
  const {
    workflows,
    isRecording,
    isPlaying,
    startRecording,
    stopRecording,
    playWorkflow,
    deleteWorkflow,
    refreshWorkflows,
  } = props;

  return (
    <div className="workflow-tab">
      <div className="workflow-header">
        <h2>📹 Workflows Library</h2>
        <p className="workflow-subtitle">Record and replay your web journeys</p>
      </div>

      {/* Recorder Section */}
      <WorkflowRecorder
        isRecording={isRecording}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
      />

      {/* Workflows List */}
      <WorkflowList
        workflows={workflows}
        isPlaying={isPlaying}
        onPlay={playWorkflow}
        onDelete={deleteWorkflow}
        onRefresh={refreshWorkflows}
      />
    </div>
  );
}

