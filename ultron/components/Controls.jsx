"use client";

import { useState, useEffect } from "react";

const STATE_LABELS = {
  IDLE: "HAZIR",
  LISTENING: "DINLIYOR",
  THINKING: "DÜŞÜNÜYOR",
  SPEAKING: "KONUŞUYOR",
  ERROR: "HATA",
  KILLED: "DURDURULDU",
};

const STATE_COLORS = {
  IDLE: "#4ade80",
  LISTENING: "#fbbf24",
  THINKING: "#60a5fa",
  SPEAKING: "#f87171",
  ERROR: "#ef4444",
  KILLED: "#ef4444",
};

export default function Controls({ state, onMicClick, onKillSwitch, isMicActive }) {
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (state === "LISTENING" || state === "SPEAKING") {
      const interval = setInterval(() => setPulse(p => !p), 500);
      return () => clearInterval(interval);
    }
    setPulse(false);
  }, [state]);

  return (
    <div className="controls">
      <div className="status-indicator">
        <span 
          className="status-dot" 
          style={{ 
            backgroundColor: STATE_COLORS[state],
            boxShadow: pulse ? `0 0 12px ${STATE_COLORS[state]}` : "none"
          }} 
        />
        <span className="status-label">{STATE_LABELS[state]}</span>
      </div>

      <div className="control-buttons">
        <button
          className={`mic-btn ${isMicActive ? "active" : ""}`}
          onClick={onMicClick}
          title={isMicActive ? "Mikrofonu Kapat" : "Mikrofonu Aç"}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="22" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </button>

        <button
          className="kill-btn"
          onClick={onKillSwitch}
          title="KILL SWITCH — Acil Durdurma (Ctrl+Alt+Shift+K)"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </button>
      </div>

      <div className="shortcuts-hint">
        <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> = Kill Switch
      </div>
    </div>
  );
}

