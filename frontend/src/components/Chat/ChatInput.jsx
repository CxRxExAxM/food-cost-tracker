import { useRef, useEffect } from 'react';
import './ChatInput.css';

export default function ChatInput({ value, onChange, onSend, disabled }) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend(value);
    }
  };

  return (
    <div className="chat-input-container">
      <textarea
        ref={inputRef}
        className="chat-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about forecasts, events, or potentials..."
        disabled={disabled}
        rows={1}
      />
      <button
        className="chat-send-btn"
        onClick={() => onSend(value)}
        disabled={disabled || !value.trim()}
      >
        Send
      </button>
    </div>
  );
}
