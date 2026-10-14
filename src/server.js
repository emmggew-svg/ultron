import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig, saveConfig } from "./config.js";
import { chatComplete } from "./llm.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC = path.join(__dirname, "..", "public");

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

export function createServer(cfg) {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://localhost");

    // --- API ---
    if (url.pathname === "/api/status" && req.method === "GET") {
      return send(res, 200, JSON.stringify({ ok: true, service: "ultron", hasKey: Boolean(cfg.apiKey), model: cfg.model }));
    }
    if (url.pathname === "/api/config" && req.method === "GET") {
      const safe = { ...cfg, apiKey: cfg.apiKey ? "***" + String(cfg.apiKey).slice(-4) : "" };
      return send(res, 200, JSON.stringify(safe));
    }
    if (url.pathname === "/api/config" && req.method === "POST") {
      try {
        const body = JSON.parse((await readBody(req)) || "{}");
        const next = saveConfig({
          ...(body.apiKey !== undefined ? { apiKey: body.apiKey } : {}),
          ...(body.model !== undefined ? { model: body.model } : {}),
          ...(body.baseURL !== undefined ? { baseURL: body.baseURL } : {}),
          ...(body.port !== undefined ? { port: Number(body.port) } : {}),
        });
        Object.assign(cfg, next);
        return send(res, 200, JSON.stringify({ ok: true }));
      } catch (e) {
        return send(res, 400, JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
      }
    }
    if (url.pathname === "/api/chat" && req.method === "POST") {
      try {
        const body = JSON.parse((await readBody(req)) || "{}");
        const messages = Array.isArray(body.messages) ? body.messages : [];
        if (!messages.length) return send(res, 400, JSON.stringify({ ok: false, error: "messages boş" }));
        const reply = await chatComplete({ baseURL: cfg.baseURL, model: cfg.model, apiKey: cfg.apiKey, messages });
        return send(res, 200, JSON.stringify({ ok: true, reply }));
      } catch (e) {
        return send(res, 500, JSON.stringify({ ok: false, error: String(e?.message ?? e) }));
      }
    }

    // --- Static ---
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
