import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DIR = path.join(os.homedir(), ".ultron");
const FILE = path.join(DIR, "config.json");

export const PROVIDER_IDS = ["openai", "anthropic", "gemini", "nvidia"];

// Varsayılanlar — araştırılmış gerçek endpoint'ler (bkz. src/providers.js):
// OpenAI: api.openai.com/v1 · Anthropic: api.anthropic.com
// Gemini: generativelanguage.googleapis.com · NVIDIA: integrate.api.nvidia.com/v1
export const PROVIDER_DEFAULTS = {
  openai: { baseURL: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  anthropic: { baseURL: "https://api.anthropic.com", model: "claude-haiku-4-5-20251001" },
  gemini: { baseURL: "https://generativelanguage.googleapis.com", model: "gemini-2.5-flash" },
  nvidia: { baseURL: "https://integrate.api.nvidia.com/v1", model: "meta/llama-3.1-8b-instruct" },
};

function blankProviders() {
  const o = {};
  for (const [id, d] of Object.entries(PROVIDER_DEFAULTS)) {
    o[id] = { apiKey: "", model: d.model, baseURL: d.baseURL };
  }
  return o;
}

const DEFAULTS = { port: 3030, activeProvider: "openai", providers: blankProviders() };

export function loadConfig() {
  let raw = {};
  try {
    raw = JSON.parse(fs.readFileSync(FILE, "utf8"));
  } catch {}
  const cfg = { port: raw.port ?? DEFAULTS.port, activeProvider: raw.activeProvider ?? "openai", providers: blankProviders() };
  if (!PROVIDER_IDS.includes(cfg.activeProvider)) cfg.activeProvider = "openai";
  if (raw.providers && typeof raw.providers === "object") {
    for (const [id, p] of Object.entries(raw.providers)) {
      if (cfg.providers[id] && p && typeof p === "object") {
        cfg.providers[id] = { ...cfg.providers[id], ...p };
      }
    }
  }
  // Eski tek-key formatından taşıma (v0.1): {apiKey, model, baseURL} → providers.openai
  if (typeof raw.apiKey === "string" && raw.apiKey && !cfg.providers.openai.apiKey) {
    cfg.providers.openai.apiKey = raw.apiKey;
  }
  if (typeof raw.model === "string" && raw.model) cfg.providers.openai.model = raw.model;
  if (typeof raw.baseURL === "string" && raw.baseURL) cfg.providers.openai.baseURL = raw.baseURL;
  return cfg;
}

export function saveConfig(patch) {
  const cfg = loadConfig();
  if (patch.port !== undefined) cfg.port = Number(patch.port);
  if (patch.activeProvider !== undefined && PROVIDER_IDS.includes(patch.activeProvider)) {
    cfg.activeProvider = patch.activeProvider;
  }
  if (patch.providers && typeof patch.providers === "object") {
    for (const [id, p] of Object.entries(patch.providers)) {
      if (cfg.providers[id] && p && typeof p === "object") {
        cfg.providers[id] = { ...cfg.providers[id], ...p };
      }
    }
  }
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(cfg, null, 2), "utf8");
  return cfg;
}

export function hasAnyKey(cfg) {
  return PROVIDER_IDS.some((id) => Boolean(cfg.providers[id]?.apiKey));
}

export function configPath() {
  return FILE;
}
