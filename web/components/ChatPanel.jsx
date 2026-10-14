"use client";

import { useState, useEffect, useRef } from "react";

const SYSTEM = "Sen ULTRON'sun: kısa, net, Türkçe konuşan yerel kişisel asistan. Gereksiz uzunluk yapma.";

export default function ChatPanel({ onStateChange }) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "ULTRON hazır. Ne komut verirsin?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [toast, setToast] = useState("");
  const messagesEndRef = useRef(null);
  const historyRef = useRef([{ role: "system", content: SYSTEM }]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Mikrofon diktesi + sayfa bildirimleri
  useEffect(() => {
    const onDict = (e) => setInput((prev) => (prev ? prev + " " : "") + e.detail);
    const onToast = (e) => {
      setToast(e.detail);
      setTimeout(() => setToast(""), 3000);
    };
    window.addEventListener("ultron-dictation", onDict);
    window.addEventListener("ultron-toast", onToast);
    return () => {
      window.removeEventListener("ultron-dictation", onDict);
      window.removeEventListener("ultron-toast", onToast);
    };
  }, []);

  const speak = (text) => {
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "tr-TR";
      u.onstart = () => onStateChange?.("SPEAKING");
      u.onend = () => onStateChange?.("IDLE");
      u.onerror = () => onStateChange?.("IDLE");
      speechSynthesis.speak(u);
    } catch {}
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);
    onStateChange?.("THINKING");

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    historyRef.current = [...historyRef.current, { role: "user", content: userMessage }].slice(-21);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: historyRef.current }),
      });

      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "hata");

      if (data.demo) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Bu sağlayıcıda API key yok — demo moddayım. Key ekranı açılıyor, ekleyince gerçek cevaplara geçelim." },
        ]);
        window.dispatchEvent(new Event("ultron-need-key"));
        return;
      }

      historyRef.current = [...historyRef.current, { role: "assistant", content: data.reply }].slice(-21);
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      if (autoSpeak) speak(data.reply);
    } catch (err) {
      onStateChange?.("ERROR");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Hata: " + err.message },
      ]);
    } finally {
      setIsLoading(false);
      onStateChange?.("IDLE");
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
        <span className="chat-actions">
          <button
            className={`mini-btn ${autoSpeak ? "on" : ""}`}
            title="Sesli cevap"
            onClick={() => setAutoSpeak((v) => !v)}
          >
            🔊
          </button>
        </span>
      </div>

      <div className="messages-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-bubble">
              <span>{msg.content}</span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {toast && <div className="toast">{toast}</div>}

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
