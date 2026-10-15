#!/usr/bin/env node
// openultron CLI — zero dependency.
import { spawn, execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig, saveConfig, configPath, PROVIDER_IDS } from "../src/config.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER = path.join(__dirname, "..", "src", "server.js");
const PIDFILE = path.join(os.homedir(), ".ultron", "server.pid");

function help() {
  console.log(`openultron — ULTRON local assistant
Kullanim:
  openultron start [--port 3030] [-d]    Servisi baslat (foreground + tarayici acar)
  openultron service start [...]         Ayni komutun uzun hali
  openultron service stop                   Servisi durdur
  openultron service status                 Durum + port bilgisi
  openultron open [--port N]                Taryicida ac
  openultron web build                      Next.js arayüzünü derle (web/out)
  openultron config show                    Aktif ayari goster (key'ler maskeli)
  openultron config use <saglayici>         Aktif saglayici: openai | anthropic | gemini | nvidia
  openultron config set-key <KEY> [--provider X]
                                            API key kaydet (varsayilan: aktif saglayici)
  openultron config set-model <MODEL> [--provider X]
  openultron config set-url <BASE_URL> [--provider X]
  openultron config set-approval <on|off>    Kritik araçlarda onay sor (varsayilan: on)
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
function provider() {
  const p = arg("--provider");
  if (!p) return loadConfig().activeProvider;
  if (!PROVIDER_IDS.includes(p)) {
    console.error(`Bilinmeyen saglayici: ${p} (secenekler: ${PROVIDER_IDS.join(" | ")})`);
    process.exit(1);
  }
  return p;
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
let [cmd, sub, extra] = rest;
// Kısayol: `openultron start` = `openultron service start`
if (cmd === "start" && (sub === undefined || sub.startsWith("-") || sub === "--port")) {
  cmd = "service";
  sub = "start";
}

const WEB_DIR = path.join(__dirname, "..", "web");
function webOutExists() {
  try {
    return fs.statSync(path.join(WEB_DIR, "out", "index.html")).isFile();
  } catch {
    return false;
  }
}
function buildWeb() {
  console.log("Web arayüzü derleniyor (ilk kurulum biraz sürebilir)…");
  execSync("npm install --no-audit --no-fund", { cwd: WEB_DIR, stdio: "inherit" });
  execSync("npm run build", { cwd: WEB_DIR, stdio: "inherit" });
  console.log("Web derlendi → web/out");
}

if (cmd === "web" && sub === "build") {
  buildWeb();
} else if (cmd === "service" && sub === "start") {
  const p = port();
  saveConfig({ port: p });
  if (!webOutExists()) buildWeb();
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
  const out = { port: c.port, activeProvider: c.activeProvider, providers: {} };
  for (const id of PROVIDER_IDS) {
    const p = c.providers[id];
    out.providers[id] = { hasKey: Boolean(p.apiKey), masked: p.apiKey ? "***" + String(p.apiKey).slice(-4) : "", model: p.model, baseURL: p.baseURL };
  }
  console.log(JSON.stringify(out, null, 2));
  console.log(`dosya: ${configPath()}`);
} else if (cmd === "config" && sub === "use") {
  if (!extra || !PROVIDER_IDS.includes(extra)) {
    console.error(`Kullanim: openultron config use <${PROVIDER_IDS.join("|")}>`);
    process.exit(1);
  }
  saveConfig({ activeProvider: extra });
  console.log(`Aktif saglayici: ${extra}`);
} else if (cmd === "config" && sub === "set-key") {
  if (!extra) {
    console.error("Kullanim: openultron config set-key <KEY> [--provider X]");
    process.exit(1);
  }
  const id = provider();
  saveConfig({ providers: { [id]: { apiKey: extra } } });
  console.log(`API key kaydedildi (${id}).`);
} else if (cmd === "config" && sub === "set-model") {
  if (!extra) {
    console.error("Kullanim: openultron config set-model <MODEL> [--provider X]");
    process.exit(1);
  }
  const id = provider();
  saveConfig({ providers: { [id]: { model: extra } } });
  console.log(`Model (${id}): ${extra}`);
} else if (cmd === "config" && sub === "set-url") {
  if (!extra) {
    console.error("Kullanim: openultron config set-url <BASE_URL> [--provider X]");
    process.exit(1);
  }
  const id = provider();
  saveConfig({ providers: { [id]: { baseURL: extra } } });
  console.log(`Endpoint (${id}): ${extra}`);
} else if (cmd === "config" && sub === "set-approval") {
  if (extra !== "on" && extra !== "off") {
    console.error("Kullanim: openultron config set-approval <on|off>");
    process.exit(1);
  }
  saveConfig({ agent: { requireApproval: extra === "on" } });
  console.log(`Arac onayi: ${extra}`);
} else {
  help();
}
