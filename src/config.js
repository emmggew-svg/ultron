import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DIR = path.join(os.homedir(), ".ultron");
const FILE = path.join(DIR, "config.json");

const DEFAULTS = {
  port: 3030,
  baseURL: "https://api.openai.com/v1",
  model: "gpt-4o-mini",
  apiKey: "",
};

export function loadConfig() {
  try {
    const raw = fs.readFileSync(FILE, "utf8");
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveConfig(patch) {
  const cfg = { ...loadConfig(), ...patch };
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(cfg, null, 2), "utf8");
  return cfg;
}

export function configPath() {
  return FILE;
}
