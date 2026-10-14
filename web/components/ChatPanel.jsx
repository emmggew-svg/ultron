"use client";

import { useState, useEffect, useRef } from "react";

const SYSTEM = "Sen ULTRON'sun: kısa, net, Türkçe konuşan yerel kişisel asistan. Gereksiz uzunluk yapma.";

const STEP_ICON = {
  think: "💭",
  shell_run: "❯",
  read_file: "📖",
  list_dir: "📁",
  grep: "🔍",
  write_file: "✎",
  edit_file: "🛠",
};

function StepRow({ step, runId }) {
  const [open, setOpen] = useState(false);
  const icon = STEP_ICON[step.tool] ?? (step.kind === "think" ? "💭" : "⚙");
  const statusMark =
    step.status === "ok" ? "✓" : step.status === "err" ? "✗" : step.status === "denied" ? "⊘" : step.status === "wait" ? "…" : "●";

  const approve = async (decision) => {
    try {
      await fetch("/api/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ runId, seq: step.seq, approve: decision }),
      });
    } catch {}
  };

  return (
    <div className={`step ${step.status}`}>
      <div className="step-line" onClick={() => (step.detail ? setOpen((v) => !v) : null)}>
        <span className="step-icon">{icon}</span>
        <span className="step-label">{step.label}</span>
        <span className="step-status">{statusMark}</span>
      </div>
      {step.status === "wait" && step.needsApproval && (
        <div className="approval-card">
          <div className="approval-cmd">{step.cmd}</div>
          <div className="approval-row">
            <button className="btn small" onClick={() => approve(true)}>Onayla</button>
            <button className="btn small ghost" onClick={() => approve(false)}>Reddet</button>
          </div>
        </div>
      )}
      {open && step.detail && <pre className="step-detail">{step.detail}</pre>}
    </div>
  );
}

function shortArgs(tool, args) {
  try {
    if (tool === "shell_run") return String(args.command ?? "");
    if (tool === "read_file" || tool === "list_dir") return String(args.path ?? "");
    if (tool === "grep") return String(args.pattern ?? "");
    if (tool === "write_file") return String(args.path ?? "");
    if (tool === "edit_file") return String(args.path ?? "");
    return JSON.stringify(args).slice(0, 120);
  } catch {
    return "";
  }
}

export default function ChatPanel({ onStateChange }) {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "ULTRON hazır. Ne komut verirsin?", steps: [] },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [toast, setToast] = useState("");
  const [runId, setRunId] = useState(null);
  const messagesEndRef = useRef(null);
  const historyRef = useRef([{ role: "system", content: SYSTEM }]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    window.dispatchEvent(new CustomEvent("ultron-run", { detail: runId }));
  }, [runId]);

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

  const patchWorking = (fn) => {
    setMessages((prev) => prev.map((m) => (m.working ? fn(m) : m)));
  };
  const addStep = (step) => {
    patchWorking((m) => ({ ...m, steps: [...(m.steps || []), step] }));
  };
  const updateStep = (seq, patch) => {
    patchWorking((m) => ({
      ...m,
      steps: (m.steps || []).map((s) => (s.seq === seq ? { ...s, ...patch } : s)),
    }));
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);
    onStateChange?.("THINKING");

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    historyRef.current = [...historyRef.current, { role: "user", content: userMessage }].slice(-41);
    setMessages((prev) => [...prev, { role: "assistant", content: "", steps: [], working: true }]);

    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: historyRef.current }),
      });
      if (!res.ok || !res.body) throw new Error("agent bağlantısı kurulamadı");

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      const handleEvent = (ev) => {
        switch (ev.type) {
          case "start":
            setRunId(ev.runId);
            break;
          case "thinking":
            onStateChange?.("THINKING");
            break;
          case "thought":
            addStep({ kind: "think", label: ev.content.slice(0, 140), status: "ok", detail: ev.content });
            break;
          case "tool_start":
            addStep({
              kind: "tool", seq: ev.seq, tool: ev.tool,
              label: `${ev.label} · ${shortArgs(ev.tool, ev.args)}`.slice(0, 140),
              status: ev.needsApproval ? "wait" : "run",
              needsApproval: ev.needsApproval,
              cmd: shortArgs(ev.tool, ev.args),
              detail: JSON.stringify(ev.args, null, 2),
            });
            if (!ev.needsApproval) onStateChange?.("THINKING");
            break;
          case "approval_needed":
            updateStep(ev.seq, { status: "wait", needsApproval: true, cmd: shortArgs(ev.tool, ev.args) });
            break;
          case "tool_run":
            updateStep(ev.seq, { status: "run", needsApproval: false });
            break;
          case "tool_result":
            updateStep(ev.seq, {
              status: ev.output === "Kullanıcı reddetti." ? "denied" : ev.ok ? "ok" : "err",
              detail: String(ev.output ?? "").slice(0, 2000),
            });
            break;
          case "message": {
            const final = ev.content;
            historyRef.current = [...historyRef.current, { role: "assistant", content: final }].slice(-41);
            setMessages((prev) => {
              const out = prev.map((m) => (m.working ? { role: "assistant", content: final, steps: m.steps || [] } : m));
              return out;
            });
            onStateChange?.("IDLE");
            if (autoSpeak) speak(final);
            break;
          }
          case "demo":
            setMessages((prev) => prev.filter((m) => !m.working));
            setMessages((prev) => [...prev, { role: "assistant", content: "Bu sağlayıcıda API key yok — demo moddayım. Key ekranı açılıyor.", steps: [] }]);
            window.dispatchEvent(new Event("ultron-need-key"));
            break;
          case "aborted":
            patchWorking((m) => ({ ...m, content: (m.content || "") + "\n— durduruldu." }));
            onStateChange?.("IDLE");
            break;
          case "error":
            patchWorking((m) => ({ ...m, content: "Hata: " + ev.error }));
            onStateChange?.("ERROR");
            break;
          default:
            break;
        }
      };

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const part of parts) {
          const line = part.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          try {
            handleEvent(JSON.parse(line.slice(5).trim()));
          } catch {}
        }
      }
    } catch (err) {
      onStateChange?.("ERROR");
      setMessages((prev) => {
        const hasWorking = prev.some((m) => m.working);
        if (!hasWorking) return [...prev, { role: "assistant", content: "Hata: " + err.message, steps: [] }];
        return prev.map((m) => (m.working ? { role: "assistant", content: "Hata: " + err.message, steps: m.steps || [] } : m));
      });
    } finally {
      setIsLoading(false);
      setRunId(null);
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
              {(msg.steps?.length > 0) && (
                <div className="timeline">
                  {msg.steps.map((s, i) => (
                    <StepRow key={s.seq ?? i} step={s} runId={runId} />
                  ))}
                </div>
              )}
              {msg.content ? <span>{msg.content}</span> : null}
              {msg.working && (!msg.steps || msg.steps.length === 0) && (
                <span className="typing">düşünüyor<span className="dots"><span>.</span><span>.</span><span>.</span></span></span>
              )}
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
          {isLoading ? "Çalışıyor…" : "Gönder"}
        </button>
      </div>
    </div>
  );
}
