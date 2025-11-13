// src/renderer/components/StatusBar.tsx
import React from 'react';
import { BrowserGymStatus } from '../types';

interface StatusBarProps {
  status: BrowserGymStatus;
  onReset: () => void;
}

export function StatusBar({ status, onReset }: StatusBarProps) {
  return (
    <div className="status-bar">
      <div className="status-info">
        <span className="app-title">🌐 BrowserGym</span>
        <span className="divider">|</span>
        <span className={`status-badge ${status.environment}`}>
          {status.environment === 'ready' && '✓ Ready'}
          {status.environment === 'resetting' && '⟳ Resetting...'}
          {status.environment === 'not_initialized' && '⚠ Not initialized'}
        </span>
      </div>
      <div className="status-actions">
        <button
          onClick={onReset}
          className="reset-button"
          disabled={status.websocket !== 'connected'}
          title="Reset environment"
        >
          🔄 Reset
        </button>
      </div>
    </div>
  );
}

