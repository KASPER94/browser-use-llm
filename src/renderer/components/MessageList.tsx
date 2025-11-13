// src/renderer/components/MessageList.tsx
import React from 'react';
import { Message } from '../types';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="empty-state">
        <h3>👋 Welcome to BrowserGym!</h3>
        <p>Ask the agent to perform web automation tasks.</p>
        <div className="examples">
          <p><strong>Try asking:</strong></p>
          <ul>
            <li>"Go to Google and search for Python tutorials"</li>
            <li>"Navigate to GitHub and search for BrowserGym"</li>
            <li>"Fill out the form on example.com"</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <div key={index} className={`message message-${message.role}`}>
          <div className="message-header">
            <span className="message-role">
              {message.role === 'user' && '👤 You'}
              {message.role === 'assistant' && '🤖 Agent'}
              {message.role === 'system' && 'ℹ️ System'}
              {message.role === 'error' && '❌ Error'}
            </span>
            <span className="message-time">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="message-content">{message.content}</div>
        </div>
      ))}
    </div>
  );
}

