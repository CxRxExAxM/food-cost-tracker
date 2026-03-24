import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import './MessageList.css';

export default function MessageList({ messages, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 && !loading && (
        <div className="message-list-empty">
          <div className="empty-icon">💬</div>
          <h3>Ask me anything</h3>
          <p>Try asking about:</p>
          <ul>
            <li>Upcoming events this week</li>
            <li>Forecast for next month</li>
            <li>Which groups have the most rooms?</li>
            <li>Events over 100 covers</li>
          </ul>
        </div>
      )}

      {messages.map((message, index) => (
        <MessageBubble key={index} message={message} />
      ))}

      {loading && (
        <div className="message-loading">
          <div className="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
