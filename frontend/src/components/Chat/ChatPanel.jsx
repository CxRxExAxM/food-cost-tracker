import { useState, useEffect, useRef } from 'react';
import ChatInput from './ChatInput';
import MessageList from './MessageList';
import { useChat } from './hooks/useChat';
import './ChatPanel.css';

export default function ChatPanel({ isOpen, onClose }) {
  const { messages, sendMessage, loading, error } = useChat();
  const [inputValue, setInputValue] = useState('');

  const handleSend = async (message) => {
    if (!message.trim()) return;

    setInputValue('');
    await sendMessage(message);
  };

  if (!isOpen) return null;

  return (
    <div className="chat-panel-overlay" onClick={onClose}>
      <div className="chat-panel" onClick={(e) => e.stopPropagation()}>
        <div className="chat-header">
          <h2>RestauranTek Assistant</h2>
          <button className="chat-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <MessageList messages={messages} loading={loading} />

        {error && (
          <div className="chat-error">
            {error}
          </div>
        )}

        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          disabled={loading}
        />
      </div>
    </div>
  );
}
