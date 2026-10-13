"use client";

import { useState, useEffect } from "react";

const STATE_COLORS = {
  IDLE: "#4ade80",
  LISTENING: "#fbbf24",
  THINKING: "#60a5fa",
  SPEAKING: "#f87171",
  ERROR: "#ef4444",
  KILLED: "#ef4444",
};

const STATE_LABELS = {
  IDLE: "HAZIR",
  LISTENING: "DINLIYOR",
  THINKING: "DÜŞÜNÜYOR",
  SPEAKING: "KONUŞUYOR",
  ERROR: "HATA",
  KILLED: "DURDURULDU",
};

export default function StatusBar({ state, toolsCount, uptime, killSwitchActive }) {
  const [time, setTime] = useState(new Date());
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (["LISTENING", "SPEAKING"].includes(state)) {
      const interval = setInterval(() => setPulse(p => !p), 500);
      return () => clearInterval(interval);
    }
    setPulse(false);
  }, [state]);

  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="status-bar">
      <div className="status-left">
        <span 
          className="status-dot" 
          style={{ 
            backgroundColor: ["LISTENING", "SPEAKING"].includes(state) ? "#fbbf24" : "#4ade80",
            boxShadow: "0 0 12px currentColor"
          }} 
        />
        <span className="status-text">
          {["LISTENING", "SPEAKING"].includes(state) ? "DINLIYOR / KONUŞUYOR" : "HAZIR"}
        </span>
      </div>

      <div className="status-center">
        <span className="uptime">{"⏱ " + formatUptime(uptime)}</span>
        <span className="tools-count">🔧 {toolsCount} araç</span>
      </div>

      <div className="status-right">
        <button className="kill-switch-btn" title="KILL SWITCH (Ctrl+Alt+Shift+K)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </button>
      </div>
    </div>
  );
}

