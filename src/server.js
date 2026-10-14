import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig, saveConfig, hasAnyKey, PROVIDER_IDS } from "./config.js";
import { PROVIDERS, chatWithProvider } from "./providers.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_OUT = path.join(__dirname, "..", "web", "out");
const PUBLIC_FALLBACK = path.join(__dirname, "..", "public");

// Next.js statik export varsa onu sun, yoksa basit public/ arayüzü
function staticRoot() {
  try {
    if (fs.statSync(path.join(WEB_OUT, "index.html")).isFile()) return WEB_OUT;
  } catch {}
  return PUBLIC_FALLBACK;
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
};

function send(res, code, body, type = "application/json; charset=utf-8") {
  res.writeHead(code, { "Content-Type": type });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let buf = "";
    req.on("data", (c) => {
      buf += c;
      if (buf.length > 1_000_000) reject(new Error("body too large"));
    });
    req.on("end", () => resolve(buf));
    req.on("error", reject);
  });
}

function safeConfig(cfg) {
  const providers = {};
  for (const id of PROVIDER_IDS) {
    const p = cfg.providers[id];
    providers[id] = {
      label: PROVIDERS[id].label,
      keyUrl: PROVIDERS[id].keyUrl,
      keyHint: PROVIDERS[id].keyHint,
      hasKey: Boolean(p.apiKey),
      masked: p.apiKey ? "***" + String(p.apiKey).slice(-4) : "",
      model: p.model,
      baseURL: p.baseURL,
    };
  }
  return { port: cfg.port, activeProvider: cfg.activeProvider, hasAnyKey: hasAnyKey(cfg), providers };
}

export function createServer(cfg) {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://localhost");

    // CLI'dan yapılan değişiklikler server çalışırken de geçerli olsun:
    // her API isteğinde ayarı diskten tazele.
    if (url.pathname.startsWith("/api/")) {
      try {
        Object.assign(cfg, loadConfig());
      } catch {}
    }

    // --- API ---
    if (url.pathname === "/api/status" && req.method === "GET") {
      const p = cfg.providers[cfg.activeProvider];
      return send(res, 200, JSON.stringify({
        ok: true,
        service: "ultron",
        activeProvider: cfg.activeProvider,
        hasKey: Boolean(p.apiKey),
        hasAnyKey: hasAnyKey(cfg),
        model: p.model,
      }));
    }
    if (url.pathname === "/api/config" && req.method === "GET") {
      return send(res, 200, JSON.stringify(safeConfig(cfg)));
    }
    if (url.pathname === "/api/config" && req.method === "POST") {
      try {
        const body = JSON.parse((await readBody(req)) || "{}");
        const patch = {};
        if (body.activeProvider !== undefined) patch.activeProvider = body.activeProvider;
        if (body.port !== undefined) patch.port = Number(body.port);
        if (body.providers && typeof body.providers === "object") {
          patch.providers = {};
          for (const [id, p] of Object.entries(body.providers)) {
            if (!PROVIDER_IDS.includes(id) || !p || typeof p !== "object") continue;
            patch.providers[id] = {};
            // Boş key gönderilirse mevcut key korunur (maskeli değer asla yazılmaz)
            if (typeof p.apiKey === "string" && p.apiKey && !p.apiKey.startsWith("***")) {
              patch.providers[id].apiKey = p.apiKey;
            }
            if (typeof p.model === "string" && p.model) patch.providers[id].model = p.model;
            if (typeof p.baseURL === "string" && p.baseURL) patch.providers[id].baseURL = p.baseURL;
          }
        }
        const next = saveConfig(patch);
        Object.assign(cfg, next);
        return send(res, 200, JSON.stringify({ ok: true, config: safeConfig(cfg) }));
      } catch (e) {
        return send(res, 400, JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
      }
    }
    if (url.pathname === "/api/chat" && req.method === "POST") {
      try {
        const body = JSON.parse((await readBody(req)) || "{}");
        const messages = Array.isArray(body.messages) ? body.messages : [];
        if (!messages.length) return send(res, 400, JSON.stringify({ ok: false, error: "messages boş" }));
        const id = PROVIDER_IDS.includes(body.provider) ? body.provider : cfg.activeProvider;
        const creds = cfg.providers[id];
        try {
          const reply = await chatWithProvider(id, creds, messages);
          return send(res, 200, JSON.stringify({ ok: true, reply, provider: id }));
        } catch (e) {
          if (e?.code === "NO_KEY") {
            return send(res, 200, JSON.stringify({ ok: true, demo: true, provider: id, reply: null }));
          }
          throw e;
        }
      } catch (e) {
        return send(res, 500, JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
      }
    }

    // --- Static ---
    const PUBLIC = staticRoot();
    let filePath = path.join(PUBLIC, url.pathname === "/" ? "index.html" : url.pathname.slice(1));
    if (!filePath.startsWith(PUBLIC)) return send(res, 403, "forbidden", "text/plain");
    try {
      const stat = fs.statSync(filePath);
      if (stat.isDirectory()) filePath = path.join(filePath, "index.html");
      const ext = path.extname(filePath).toLowerCase();
      const data = fs.readFileSync(filePath);
      return send(res, 200, data, MIME[ext] ?? "application/octet-stream");
    } catch {
      return send(res, 404, "not found", "text/plain");
    }
  });
}

function parsePort(argv) {
  const i = argv.indexOf("--port");
  if (i !== -1 && argv[i + 1]) return Number(argv[i + 1]);
  return loadConfig().port ?? 3030;
}

// Direct run: node src/server.js [--port 3030]
const isDirect = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isDirect) {
  const port = parsePort(process.argv.slice(2));
  const cfg = loadConfig();
  cfg.port = port;
  createServer(cfg).listen(port, () => {
    console.log(`ULTRON running → http://localhost:${port}`);
  });
}
