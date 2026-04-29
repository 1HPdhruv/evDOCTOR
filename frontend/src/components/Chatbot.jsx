import React, { useState, useRef, useEffect } from 'react';
import { apiFetch } from '../api';

const QUICK_ACTIONS = [
  { label: '🔋 Battery Issue', msg: 'My EV battery is draining fast' },
  { label: '⚡ Charging Problem', msg: 'My car is not charging properly' },
  { label: '🔊 Strange Noise', msg: 'I hear a grinding noise while driving' },
  { label: '📉 Range Dropped', msg: 'My range has dropped significantly' },
  { label: '🚫 Won\'t Start', msg: 'My EV won\'t start at all' },
  { label: '⚠️ Warning Light', msg: 'There is a warning light on my dashboard' },
];

// Simple markdown-like rendering for chat messages
function ChatContent({ text }) {
  if (!text) return null;
  
  const lines = text.split('\n');
  return (
    <div className="chat-content">
      {lines.map((line, i) => {
        // Bold: **text**
        let rendered = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Inline code: `text`
        rendered = rendered.replace(/`(.+?)`/g, '<code style="background:rgba(34,211,238,0.15);padding:1px 4px;border-radius:3px;font-size:0.82em">$1</code>');
        // Bullet points
        if (rendered.startsWith('•') || rendered.startsWith('-')) {
          return <div key={i} style={{ paddingLeft: '0.5rem', marginBottom: '2px' }} dangerouslySetInnerHTML={{ __html: rendered }} />;
        }
        // Numbered lists
        if (/^\d+\./.test(rendered)) {
          return <div key={i} style={{ paddingLeft: '0.5rem', marginBottom: '2px' }} dangerouslySetInnerHTML={{ __html: rendered }} />;
        }
        // Empty line = spacer
        if (!rendered.trim()) return <div key={i} style={{ height: '6px' }} />;
        return <div key={i} dangerouslySetInnerHTML={{ __html: rendered }} />;
      })}
    </div>
  );
}

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi there! 👋 I\'m the **evDOCTOR AI Assistant**.\n\nI can help you with:\n• Diagnosing EV faults\n• Explaining DTC/OBD-II codes\n• Battery & charging issues\n• Maintenance tips & costs\n\nDescribe your problem or tap a quick action below!' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const sendMessage = async (text) => {
    if (!text.trim()) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setShowQuickActions(false);

    try {
      const res = await apiFetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: messages })
      });
      
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I\'m having trouble connecting to the server. Please try again.' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Network error. Please check your connection and try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const clearChat = () => {
    setMessages([
      { role: 'assistant', content: 'Chat cleared! 🧹 How can I help you now?' }
    ]);
    setShowQuickActions(true);
  };

  return (
    <>
      {/* Floating Button */}
      <button 
        className="chat-fab" 
        onClick={() => setIsOpen(!isOpen)}
        title="Chat with AI Assistant"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="chat-window glass-card">
          <div className="chat-header">
            <div className="chat-header-left">
              <span className="chat-status-dot"></span>
              <h3>evDOCTOR AI</h3>
            </div>
            <div className="chat-header-actions">
              <button className="chat-action-btn" onClick={clearChat} title="Clear chat">🗑️</button>
              <button className="chat-close" onClick={() => setIsOpen(false)}>×</button>
            </div>
          </div>
          
          <div className="chat-body">
            {messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role}`}>
                {m.role === 'assistant' && <div className="chat-avatar">🤖</div>}
                <div className="chat-bubble">
                  <ChatContent text={m.content} />
                </div>
              </div>
            ))}

            {/* Quick Actions */}
            {showQuickActions && !loading && (
              <div className="quick-actions">
                {QUICK_ACTIONS.map((qa, i) => (
                  <button key={i} className="quick-action-btn" onClick={() => sendMessage(qa.msg)}>
                    {qa.label}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className="chat-message assistant">
                <div className="chat-avatar">🤖</div>
                <div className="chat-bubble loading">
                  <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-footer" onSubmit={handleSend}>
            <input 
              ref={inputRef}
              type="text" 
              placeholder="Ask about your EV issue..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button type="submit" disabled={!input.trim() || loading}>➤</button>
          </form>
        </div>
      )}
    </>
  );
}
