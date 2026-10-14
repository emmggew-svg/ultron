import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

// ---- Güvenlik ----

// Çıktılardaki sırları maskele (key'ler sohbete/ekrana sızmasın)
export function redact(text) {
  return String(text ?? "").replace(
    /(sk-[A-Za-z0-9\-_]{8,}|sk-ant-[A-Za-z0-9\-_]{8,}|nvapi-[A-Za-z0-9\-_]{8,}|AIza[A-Za-z0-9\-_]{20,})/g,
    "[GİZLİ]"
  );
}

function clamp(text, max = 8000) {
  const s = String(text ?? "");
  if (s.length <= max) return s;
  return s.slice(0, max) + `\n… [${s.length - max} karakter kesildi]`;
}

// ---- Araç tanımları (modele anlatılan şema) ----

export const TOOL_DEFS = [
  { name: "shell_run", needsApproval: true, desc: "Windows komutu çalıştırır (cmd.exe). Onay gerekir.", args: "{command}" },
  { name: "read_file", needsApproval: false, desc: "Dosya okur (en fazla 2000 satır).", args: "{path}" },
  { name: "list_dir", needsApproval: false, desc: "Klasör içeriğini listeler.", args: "{path}" },
  { name: "grep", needsApproval: false, desc: "Dosyalarda metin arar.", args: "{pattern, path?}" },
  { name: "write_file", needsApproval: true, desc: "Dosya yazar/üzerine yazar. Onay gerekir.", args: "{path, content}" },
  { name: "edit_file", needsApproval: true, desc: "Dosyada exact metin değiştirir. Onay gerekir.", args: "{path, oldString, newString}" },
];

export function toolPromptBlock() {
  const lines = TOOL_DEFS.map((t) => `- ${t.name} ${t.args}: ${t.desc}`);
  return [
    "Elindeki araçlar (gerçekten çalışırlar):",
    ...lines,
    "Araç çağırmak için cevabına şu bloğu ekle:",
    "```tool",
    '{"name":"shell_run","args":{"command":"dir"}}',
    "```",
    "Bir cevapta birden fazla araç bloğu olabilir, sırayla çalışırlar.",
    "Araç sonuçları sana iletilir, sonra devam edersin.",
    "Onay gereken araçlarda kullanıcıya tek cümleyle ne yapacağını söyle,",
    "onay sonucu gelince devam et. İşin bitince araç bloğu koymadan normal cevabını yaz.",
  ].join("\n");
}

// ---- Çalıştırıcılar ----

function runCmd(command, { timeout = 30000, cwd } = {}) {
  return new Promise((resolve) => {
    execFile("cmd.exe", ["/c", command], { timeout, cwd, windowsHide: true, maxBuffer: 2 * 1024 * 1024 }, (err, stdout, stderr) => {
      const out = clamp(redact((stdout ?? "") + (stderr ? "\n[stderr]\n" + stderr : "")));
      resolve({ ok: !err || err.code === 0, exitCode: err?.code ?? 0, output: out || "(çıktı yok)" });
    });
  });
}

function readFile(p) {
  const abs = path.resolve(p);
  const raw = fs.readFileSync(abs, "utf8");
  const lines = raw.split("\n");
  const shown = lines.slice(0, 2000).join("\n");
  const note = lines.length > 2000 ? `\n… [${lines.length - 2000} satır kesildi]` : "";
  return { ok: true, output: clamp(redact(shown + note)) };
}

function listDir(p) {
  const abs = path.resolve(p || ".");
  const entries = fs.readdirSync(abs, { withFileTypes: true });
  const out = entries.slice(0, 300).map((e) => (e.isDirectory() ? e.name + "/" : e.name)).join("\n");
  return { ok: true, output: out || "(boş)" };
}

function grepFiles(pattern, root) {
  const start = path.resolve(root || ".");
  const hits = [];
  const skip = new Set(["node_modules", ".git", ".next", "out", "dist", ".venv"]);
  const walk = (dir, depth) => {
    if (depth > 6 || hits.length >= 50) return;
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      if (hits.length >= 50) break;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!skip.has(e.name)) walk(full, depth + 1);
      } else if (/\.(js|jsx|ts|tsx|json|md|css|html|py|txt|yaml|yml|toml)$/i.test(e.name)) {
        try {
          if (fs.statSync(full).size > 500_000) continue;
          const lines = fs.readFileSync(full, "utf8").split("\n");
          lines.forEach((ln, i) => {
            if (hits.length < 50 && ln.includes(pattern)) {
              hits.push(`${path.relative(start, full)}:${i + 1}: ${ln.trim().slice(0, 160)}`);
            }
          });
        } catch {}
      }
    }
  };
  walk(start, 0);
  return { ok: true, output: redact(hits.join("\n") || "(bulunamadı)") };
}

function writeFile(p, content) {
  const abs = path.resolve(p);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, content ?? "", "utf8");
  return { ok: true, output: `yazıldı: ${abs} (${String(content ?? "").length} karakter)` };
}

function editFile(p, oldString, newString) {
  const abs = path.resolve(p);
  const raw = fs.readFileSync(abs, "utf8");
  if (!raw.includes(oldString)) {
    return { ok: false, output: "oldString dosyada bulunamadı — değişiklik yapılmadı." };
  }
  const count = raw.split(oldString).length - 1;
  if (count > 1) {
    return { ok: false, output: `oldString ${count} yerde geçiyor — tekil olmalı, değişiklik yapılmadı.` };
  }
  fs.writeFileSync(abs, raw.replace(oldString, newString), "utf8");
  return { ok: true, output: `düzenlendi: ${abs}` };
}

export async function runTool(name, args = {}) {
  try {
    switch (name) {
      case "shell_run":
        if (!args.command) return { ok: false, output: "command gerekli." };
        return await runCmd(String(args.command), { cwd: args.cwd });
      case "read_file":
        if (!args.path) return { ok: false, output: "path gerekli." };
        return readFile(String(args.path));
      case "list_dir":
        return listDir(args.path ? String(args.path) : ".");
      case "grep":
        if (!args.pattern) return { ok: false, output: "pattern gerekli." };
        return grepFiles(String(args.pattern), args.path ? String(args.path) : ".");
      case "write_file":
        if (!args.path) return { ok: false, output: "path gerekli." };
        return writeFile(String(args.path), args.content ?? "");
      case "edit_file":
        if (!args.path || args.oldString === undefined || args.newString === undefined) {
          return { ok: false, output: "path + oldString + newString gerekli." };
        }
        return editFile(String(args.path), String(args.oldString), String(args.newString));
      default:
        return { ok: false, output: `bilinmeyen araç: ${name}` };
    }
  } catch (e) {
    return { ok: false, output: "araç hatası: " + String(e?.message ?? e) };
  }
}

export function needsApproval(name) {
  return (TOOL_DEFS.find((t) => t.name === name)?.needsApproval) ?? true;
}
