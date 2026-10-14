#!/usr/bin/env node
// openultron CLI — zero dependency.
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig, saveConfig, configPath } from "../src/config.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER = path.join(__dirname, "..", "src", "server.js");
const PIDFILE = path.join(os.homedir(), ".ultron", "server.pid");

function help() {
  console.log(`openultron — ULTRON local assistant
Kullanim:
  openultron service start [--port 3030]   Servisi baslat (foreground)
  openultron service start -d [--port N]   Arka planda baslat (detached)
  openultron service stop                   Servisi durdur
  openultron service status                 Durum + port bilgisi
  openultron open [--port N]                Taryicida ac
  openultron config show                    Aktif ayari goster (key maskeli)
  openultron config set-key <KEY>           API key kaydet
  openultron config set-model <MODEL>       Model sec (orn: gpt-4o-mini)
  openultron config set-url <BASE_URL>      OpenAI-compatible endpoint
`);
}

function arg(flag) {
  const i = process.argv.indexOf(flag);
  return i !== -1 ? process.argv[i + 1] : undefined;
}
function has(flag) {
  return process.argv.includes(flag);
}
function port() {
  return Number(arg("--port") ?? loadConfig().port ?? 3030);
}
function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}
function readPid() {
  try {
    return Number(fs.readFileSync(PIDFILE, "utf8").trim());
  } catch {
    return null;
  }
}
async function openBrowser(url) {
  const cmd = process.platform === "win32" ? "cmd" : process.platform === "darwin" ? "open" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  spawn(cmd, args, { stdio: "ignore", detached: true }).unref();
}
async function waitUp(portN, tries = 25) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://localhost:${portN}/api/status`);
      if (r.ok) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

const [, , ...rest] = process.argv;
const [cmd, sub, extra] = rest;

if (cmd === "service" && sub === "start") {
  const p = port();
  saveConfig({ port: p });
  if (has("-d") || has("--detached")) {
    const old = readPid();
    if (old && pidAlive(old)) {
      console.log(`Zaten calisiyor (pid ${old}) → http://localhost:${p}`);
      process.exit(0);
    }
    const child = spawn(process.execPath, [SERVER, "--port", String(p)], {
      detached: true,
      stdio: "ignore",
      cwd: path.join(__dirname, ".."),
    });
    child.unref();
    fs.mkdirSync(path.dirname(PIDFILE), { recursive: true });
    fs.writeFileSync(PIDFILE, String(child.pid));
    const up = await waitUp(p);
    console.log(up ? `Baslatildi (pid ${child.pid}) → http://localhost:${p}` : `Baslatildi ama saglik kontrolu basarisiz (pid ${child.pid})`);
  } else {
    console.log(`ULTRON starting → http://localhost:${p}  (durdurmak icin Ctrl+C)`);
    await openBrowser(`http://localhost:${p}`);
    const child = spawn(process.execPath, [SERVER, "--port", String(p)], { stdio: "inherit" });
    const onExit = () => child.kill();
    process.on("SIGINT", onExit);
    process.on("SIGTERM", onExit);
    child.on("exit", (code) => process.exit(code ?? 0));
  }
} else if (cmd === "service" && sub === "stop") {
  const pid = readPid();
  if (!pid) {
    console.log("Calisan servis bulunamadi (pid dosyasi yok).");
    process.exit(0);
  }
  try {
    process.kill(pid);
    fs.rmSync(PIDFILE, { force: true });
    console.log(`Durduruldu (pid ${pid}).`);
  } catch {
    fs.rmSync(PIDFILE, { force: true });
    console.log("Surec zaten olmus, kayit temizlendi.");
  }
} else if (cmd === "service" && sub === "status") {
  const p = port();
  const pid = readPid();
  let httpOk = false;
  try {
    const r = await fetch(`http://localhost:${p}/api/status`);
    httpOk = r.ok;
  } catch {}
  console.log(JSON.stringify({ port: p, pid, pidAlive: pid ? pidAlive(pid) : false, httpOk }, null, 2));
} else if (cmd === "open") {
  const p = port();
  await openBrowser(`http://localhost:${p}`);
  console.log(`Acildi → http://localhost:${p}`);
} else if (cmd === "config" && sub === "show") {
  const c = loadConfig();
  console.log(JSON.stringify({ ...c, apiKey: c.apiKey ? "***" + String(c.apiKey).slice(-4) : "" }, null, 2));
  console.log(`dosya: ${configPath()}`);
} else if (cmd === "config" && sub === "set-key") {
  if (!extra) {
    console.error("Kullanim: openultron config set-key <KEY>");
    process.exit(1);
  }
  saveConfig({ apiKey: extra });
  console.log("API key kaydedildi.");
} else if (cmd === "config" && sub === "set-model") {
  if (!extra) {
    console.error("Kullanim: openultron config set-model <MODEL>");
    process.exit(1);
  }
  saveConfig({ model: extra });
  console.log(`Model: ${extra}`);
} else if (cmd === "config" && sub === "set-url") {
  if (!extra) {
    console.error("Kullanim: openultron config set-url <BASE_URL>");
    process.exit(1);
  }
  saveConfig({ baseURL: extra });
  console.log(`Endpoint: ${extra}`);
} else {
  help();
}
