// src/renderer/components/InputBox.tsx
import React from 'react';

interface InputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  disabled: boolean;
  placeholder: string;
}

export function InputBox({
  value,
  onChange,
  onSend,
  onKeyDown,
  disabled,
  placeholder,
}: InputBoxProps) {
  return (
    <div className="input-box">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={3}
        className="input-textarea"
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="send-button"
        title="Send message (Enter)"
      >
        ➤
      </button>
    </div>
  );
}

