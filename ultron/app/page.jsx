"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import UltronScene from "@/components/UltronScene";
import ChatPanel from "@/components/ChatPanel";
import Controls from "@/components/Controls";
import StatusBar from "@/components/StatusBar";

const UltronOrb = dynamic(() => import("@/components/UltronOrb"), { ssr: false });

export default function Page() {
  const [state, setState] = useState("IDLE");
  const [isMicActive, setIsMicActive] = useState(false);
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setUptime(t => t + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // WebSocket connection for real-time events
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    
    ws.onopen = () => {
      console.log("WS connected");
      ws.send(JSON.stringify({ type: "ping" }));
    };
    
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };
    
    ws.onclose = () => {
      console.log("WS disconnected, reconnecting in 3s...");
      setTimeout(() => window.location.reload(), 3000);
    };
    
    ws.onerror = (err) => {
      console.error("WS error", err);
    };

    return () => ws.close();
  }, []);

  const handleWSMessage = (msg) => {
    switch (msg.type) {
      case "state":
        setState(msg.data.state);
        break;
      case "utterance":
      case "user_utterance":
        break;
      case "tool_requested":
        break;
      case "tool_completed":
        break;
      case "interrupted":
        break;
      case "killswitch":
        setKillSwitchActive(true);
        break;
      case "error":
        console.error("Server error:", msg.data);
        break;
    }
  };

  const handleMicClick = async () => {
    const newState = !isMicActive;
    setIsMicActive(newState);
    
    try {
      const command = newState ? "mic_on" : "mic_off";
      const bodyObj = { tool: "shell_run", args: { command: command } };
      await fetch("http://localhost:8000/api/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyObj)
      });
    } catch (err) {
      console.error("Mic toggle failed:", err);
    }
  };

  const handleKillSwitch = async () => {
    setKillSwitchActive(true);
    try {
      const bodyObj = { tool: "shell_run", args: { command: "kill_switch" } };
      await fetch("http://localhost:8000/api/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyObj)
      });
    } catch (err) {
      console.error("Kill switch failed:", err);
    }
  };

  return (
    <div className="ultron-app">
      <StatusBar 
        state={state} 
        toolsCount={15} 
        uptime={uptime} 
        killSwitchActive={killSwitchActive} 
      />
      
      <div className="main-stage">
        <UltronScene />
        
        <div className="ui-overlay">
          <Controls
            state={state}
            onMicClick={handleMicClick}
            onKillSwitch={handleKillSwitch}
            isMicActive={isMicActive}
          />
          
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}

