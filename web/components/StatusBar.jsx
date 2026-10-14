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

export default function StatusBar({ state, uptime, backend, onOpenSettings }) {
  const [time, setTime] = useState(new Date());
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (["LISTENING", "SPEAKING", "THINKING"].includes(state)) {
      const interval = setInterval(() => setPulse((p) => !p), 500);
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

  const dotColor =
    state === "ERROR" || state === "KILLED" ? "#ef4444"
    : state === "IDLE" ? "#4ade80"
    : "#fbbf24";

  return (
    <div className="status-bar">
      <div className="status-left">
        <span
          className="status-dot"
          style={{
            backgroundColor: dotColor,
            boxShadow: pulse ? `0 0 12px ${dotColor}` : "none",
          }}
        />
        <span className="status-text">{STATE_LABELS[state] ?? state}</span>
      </div>

      <div className="status-center">
        <span className="uptime">{"⏱ " + formatUptime(uptime)}</span>
        <span className="backend-info" title={backend?.hasKey ? "API key bağlı" : "Demo mod (key yok)"}>
          ★ {backend?.activeProvider ?? "…"} • {backend?.model ?? "…"}
          {backend && !backend.hasKey ? " (demo)" : ""}
        </span>
      </div>

      <div className="status-right">
        <span className="clock">
          {time.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </span>
        <button className="settings-btn" title="Ayarlar / API Key" onClick={onOpenSettings}>
          ⚙
        </button>
      </div>
    </div>
  );
}
