"use client";

import { useState, useEffect } from "react";

export default function SettingsModal({ welcome, onClose }) {
  const [cfg, setCfg] = useState(null);
  const [tab, setTab] = useState(null);
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [url, setUrl] = useState("");
  const [saved, setSaved] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const c = await fetch("/api/config").then((x) => x.json());
        setCfg(c);
        setTab(c.activeProvider);
        setModel(c.providers[c.activeProvider]?.model ?? "");
        setUrl(c.providers[c.activeProvider]?.baseURL ?? "");
      } catch {
        setSaved("Ayarlar yüklenemedi.");
      }
    })();
  }, []);

  const select = (id) => {
    setTab(id);
    setKey("");
    setModel(cfg.providers[id]?.model ?? "");
    setUrl(cfg.providers[id]?.baseURL ?? "");
    setSaved("");
  };

  const save = async (makeActive) => {
    const body = { providers: { [tab]: {} } };
    if (key) body.providers[tab].apiKey = key;
    if (model) body.providers[tab].model = model;
    if (url) body.providers[tab].baseURL = url;
    if (makeActive) body.activeProvider = tab;
    try {
      const r = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }).then((x) => x.json());
      if (!r.ok) throw new Error(r.error || "hata");
      setCfg(r.config);
      setKey("");
      setSaved("Kaydedildi ✓");
      setTimeout(() => setSaved(""), 2500);
    } catch (e) {
      setSaved("Hata: " + e.message);
    }
  };

  if (!cfg) {
    return (
      <div className="modal-backdrop">
        <div className="modal-card"><p>Yükleniyor…</p></div>
      </div>
    );
  }

  const p = cfg.providers[tab];

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <h3>{welcome ? "API Anahtarı Gerekli" : "Ayarlar"}</h3>
        {welcome && (
          <p className="welcome-text">
            👋 Hoş geldin! ULTRON'u kullanmak için önce bir <b>API anahtarı</b> gir.
            Sağlayıcını seç, key'ini yapıştır, kaydet.
          </p>
        )}

        <div className="prov-tabs">
          {Object.entries(cfg.providers).map(([id, pr]) => (
            <button
              key={id}
              className={`prov-tab ${id === tab ? "on" : ""} ${id === cfg.activeProvider ? "active" : ""}`}
              onClick={() => select(id)}
            >
              {id === cfg.activeProvider ? "★ " : ""}{pr.label}{pr.hasKey ? " ✓" : ""}
            </button>
          ))}
        </div>

        <p className="prov-info">
          <a href={p.keyUrl} target="_blank" rel="noopener noreferrer">🔑 {p.label} key al →</a>
          <span> {p.keyHint}{p.hasKey ? ` (${p.masked})` : ""}</span>
        </p>

        <label className="field">API Key
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={p.hasKey ? `Kayıtlı ${p.masked} (değiştirmek için yaz)` : p.keyHint}
          />
        </label>
        <label className="field">Model
          <input value={model} onChange={(e) => setModel(e.target.value)} />
        </label>
        <label className="field">Endpoint
          <input value={url} onChange={(e) => setUrl(e.target.value)} />
        </label>

        <div className="modal-row">
          <button className="btn ghost" onClick={() => save(false)}>Kaydet</button>
          <button className="btn" onClick={() => save(true)}>
            {tab === cfg.activeProvider ? "Kaydet ★" : "Kaydet + Aktif Yap"}
          </button>
          <button className="btn ghost" onClick={onClose}>Kapat</button>
        </div>
        {saved && <p className="saved-note">{saved}</p>}
        {welcome && (
          <button className="linklike" onClick={onClose}>
            Key olmadan demo modda devam et →
          </button>
        )}
      </div>
    </div>
  );
}
