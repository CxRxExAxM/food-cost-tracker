import { useState, useCallback } from 'react';
import axios from '../../../lib/axios';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return;

    // Add user message optimistically
    const userMessage = {
      role: 'user',
      content: content,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/chat', {
        message: content,
        session_id: sessionId
      });

      // Update session ID if new
      if (response.data.session_id && !sessionId) {
        setSessionId(response.data.session_id);
      }

      // Add assistant message
      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        result_type: response.data.render_type,
        result_data: response.data.render_data,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      setError(err.response?.data?.detail || 'Failed to send message. Please try again.');

      // Remove optimistic user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, []);

  return {
    messages,
    sessionId,
    loading,
    error,
    sendMessage,
    clearMessages
  };
}
