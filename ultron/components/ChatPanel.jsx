"use client";

import { useState, useEffect, useRef } from "react";

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "ULTRON hazır. Ne komut verirsin?" }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);
    
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });
      
      const data = await res.json();
      
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.response,
        toolCalls: data.tool_calls 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Bağlantı hatası. API sunucusu çalışıyor mu?" 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">ULTRON</span>
        <span className="connection-status">● Bağlı</span>
      </div>
      
      <div className="messages-container" ref={messagesEndRef}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-bubble">
              {msg.role === "assistant" && msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="tool-calls">
                  {msg.toolCalls.map((tc, i) => (
                    <div key={i} className="tool-call">
                      <span className="tool-name">{tc.tool}</span>
                      <span className="tool-args">{JSON.stringify(tc.args)}</span>
                      <span className="tool-result">{tc.result?.slice(0, 100)}...</span>
                    </div>
                  ))}
                </div>
              )}
              <span>{msg.content}</span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="ULTRON'a komut ver..."
          disabled={isLoading}
          rows={3}
        />
        <button 
          className="send-btn" 
          onClick={sendMessage} 
          disabled={!input.trim() || isLoading}
        >
          {isLoading ? "İşleniyor..." : "Gönder"}
        </button>
      </div>
    </div>
  );
}

