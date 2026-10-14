"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import UltronScene from "@/components/UltronScene";
import ChatPanel from "@/components/ChatPanel";
import Controls from "@/components/Controls";
import StatusBar from "@/components/StatusBar";
import SettingsModal from "@/components/SettingsModal";

const UltronOrb = dynamic(() => import("@/components/UltronOrb"), { ssr: false });

export default function Page() {
  const [state, setState] = useState("IDLE");
  const [isMicActive, setIsMicActive] = useState(false);
  const [uptime, setUptime] = useState(0);
  const [backend, setBackend] = useState({ activeProvider: "…", model: "…", hasKey: false, hasAnyKey: false });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsWelcome, setSettingsWelcome] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setUptime((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // Backend durumu (sağlayıcı + key) — 5 sn'de bir yokla
  const pollStatus = useCallback(async () => {
    try {
      const r = await fetch("/api/status").then((x) => x.json());
      setBackend({
        activeProvider: r.activeProvider ?? "?",
        model: r.model ?? "?",
        hasKey: !!r.hasKey,
        hasAnyKey: !!r.hasAnyKey,
      });
      return r;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    (async () => {
      const r = await pollStatus();
      // Daha önce hiç key girilmediyse key ekranını aç
      if (r && !r.hasAnyKey) {
        setSettingsWelcome(true);
        setSettingsOpen(true);
      }
    })();
    const t = setInterval(pollStatus, 5000);
    const needKey = () => {
      setSettingsWelcome(true);
      setSettingsOpen(true);
    };
    window.addEventListener("ultron-need-key", needKey);
    return () => {
      clearInterval(t);
      window.removeEventListener("ultron-need-key", needKey);
    };
  }, [pollStatus]);

  // Mikrofon: tarayıcı diktesi → ChatPanel'e aktar (yoksa da yazılabilir)
  const handleMicClick = async () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      window.dispatchEvent(new CustomEvent("ultron-toast", { detail: "Bu tarayıcıda dikte yok — yazarak kullan." }));
      return;
    }
    if (isMicActive) {
      setIsMicActive(false);
      setState("IDLE");
      return;
    }
    try {
      const rec = new SR();
      rec.lang = "tr-TR";
      rec.interimResults = false;
      setIsMicActive(true);
      setState("LISTENING");
      rec.onresult = (e) => {
        const t = e.results[0][0].transcript;
        window.dispatchEvent(new CustomEvent("ultron-dictation", { detail: t }));
      };
      rec.onend = () => {
        setIsMicActive(false);
        setState((s) => (s === "LISTENING" ? "IDLE" : s));
      };
      rec.onerror = () => {
        setIsMicActive(false);
        setState("IDLE");
      };
      rec.start();
    } catch {
      setIsMicActive(false);
      setState("IDLE");
    }
  };

  const handleKillSwitch = () => {
    try {
      speechSynthesis.cancel();
    } catch {}
    setIsMicActive(false);
    setState("IDLE");
    window.dispatchEvent(new CustomEvent("ultron-toast", { detail: "Durduruldu." }));
  };

  return (
    <div className="ultron-app">
      <StatusBar state={state} uptime={uptime} backend={backend} onOpenSettings={() => { setSettingsWelcome(false); setSettingsOpen(true); }} />

      <div className="main-stage">
        <UltronScene />

        <div className="ui-overlay">
          <Controls
            state={state}
            onMicClick={handleMicClick}
            onKillSwitch={handleKillSwitch}
            isMicActive={isMicActive}
          />

          <ChatPanel onStateChange={setState} />
        </div>
      </div>

      {settingsOpen && (
        <SettingsModal
          welcome={settingsWelcome}
          onClose={() => {
            setSettingsOpen(false);
            pollStatus();
          }}
        />
      )}
    </div>
  );
}
