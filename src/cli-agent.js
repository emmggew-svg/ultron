import readline from "node:readline";
import { runAgent, resolveApproval, abortRun } from "./agent.js";
import { loadConfig, saveConfig, PROVIDER_IDS } from "./config.js";

const C = {
  reset: "\x1b[0m",
  gray: "\x1b[90m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

function shortArgs(tool, args) {
  try {
    if (tool === "shell_run") return String(args.command ?? "");
    if (tool === "read_file" || tool === "list_dir") return String(args.path ?? "");
    if (tool === "grep") return String(args.pattern ?? "");
    if (tool === "write_file" || tool === "edit_file") return String(args.path ?? "");
    return JSON.stringify(args).slice(0, 120);
  } catch {
    return "";
  }
}

export async function runCliAgent() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout, prompt: `${C.cyan}ultron>${C.reset} ` });
  let cfg = loadConfig();
  const hist = [];
  let currentRun = null;
  let running = false;

  console.log(`${C.cyan}ULTRON terminal agenti${C.reset} — ${cfg.activeProvider} • ${cfg.providers[cfg.activeProvider].model}`);
  console.log(`${C.gray}Komutlar: /provider <id> • /model <ad> • /approval on|off • /exit${C.reset}`);

  const ask = (q) => {
    if (rl.closed) return Promise.resolve("n");
    return new Promise((res) => rl.question(q, res));
  };
  const prompt = () => {
    if (!rl.closed) rl.prompt();
  };

  rl.on("SIGINT", () => {
    if (running && currentRun) {
      abortRun(currentRun);
      console.log(`\n${C.yellow}Durduruluyor…${C.reset}`);
    } else {
      console.log("\nGörüşürüz.");
      process.exit(0);
    }
  });

  rl.prompt();
  for await (const line of rl) {
    const text = line.trim();
    if (!text) {
      if (!rl.closed) rl.prompt();
      continue;
    }
    if (text === "/exit" || text === "/quit" || text === "exit" || text === "quit" || text === "q") {
      console.log("Görüşürüz.");
      rl.close();
      return;
    }
    if (text.startsWith("/provider")) {
      const id = text.split(/\s+/)[1];
      if (!PROVIDER_IDS.includes(id)) {
        console.log(`${C.red}Kullanim: /provider <${PROVIDER_IDS.join("|")}>${C.reset}`);
      } else {
        saveConfig({ activeProvider: id });
        cfg = loadConfig();
        console.log(`Aktif saglayici: ${C.green}${id}${C.reset}`);
      }
      prompt();
      continue;
    }
    if (text.startsWith("/model")) {
      const m = text.split(/\s+/)[1];
      if (!m) {
        console.log(`${C.red}Kullanim: /model <ad>${C.reset}`);
      } else {
        saveConfig({ providers: { [cfg.activeProvider]: { model: m } } });
        cfg = loadConfig();
        console.log(`Model: ${C.green}${m}${C.reset}`);
      }
      prompt();
      continue;
    }
    if (text.startsWith("/approval")) {
      const v = text.split(/\s+/)[1];
      if (v !== "on" && v !== "off") {
        console.log(`${C.red}Kullanim: /approval on|off${C.reset}`);
      } else {
        saveConfig({ agent: { requireApproval: v === "on" } });
        cfg = loadConfig();
        console.log(`Arac onayi: ${v}`);
      }
      prompt();
      continue;
    }
    if (text === "/help") {
      console.log(`${C.gray}/provider • /model • /approval on|off • /exit${C.reset}`);
      prompt();
      continue;
    }

    running = true;
    hist.push({ role: "user", content: text });
    console.log(`${C.gray}Çalışma…${C.reset}`);
    try {
      await runAgent({
        providerId: cfg.activeProvider,
        creds: cfg.providers[cfg.activeProvider],
        messages: hist.slice(-40),
        requireApproval: cfg.agent?.requireApproval !== false,
        emit: async (ev) => {
          switch (ev.type) {
            case "start":
              currentRun = ev.runId;
              break;
            case "thought":
              console.log(`${C.gray}💭 ${ev.content.slice(0, 200)}${C.reset}`);
              break;
            case "tool_start":
              console.log(`❯ ${ev.label} · ${C.gray}${shortArgs(ev.tool, ev.args).slice(0, 140)}${C.reset}${ev.needsApproval ? ` ${C.yellow}(onay bekleniyor)${C.reset}` : ""}`);
              break;
            case "approval_needed": {
              const ans = (await ask(`${C.yellow}Onayla? [y/n]${C.reset} `)).trim().toLowerCase();
              resolveApproval(ev.runId, ev.seq, ans === "y" || ans === "yes" || ans === "e" || ans === "evet");
              break;
            }
            case "tool_result":
              if (ev.output === "Kullanıcı reddetti.") {
                console.log(`  ${C.red}⊘ reddedildi${C.reset}`);
              } else {
                console.log(`  ${ev.ok ? C.green + "✓" : C.red + "✗"}${C.reset} ${C.gray}${String(ev.output ?? "").slice(0, 500)}${C.reset}`);
              }
              break;
            case "message":
              hist.push({ role: "assistant", content: ev.content });
              console.log(`\n${ev.content}\n`);
              break;
            case "demo":
              console.log(`${C.yellow}Bu sağlayıcıda API key yok. Ayar için: openultron config set-key <KEY>${C.reset}`);
              break;
            case "aborted":
              console.log(`${C.yellow}— durduruldu.${C.reset}`);
              break;
            case "error":
              console.log(`${C.red}Hata: ${ev.error}${C.reset}`);
              break;
            default:
              break;
          }
        },
      });
    } finally {
      running = false;
      currentRun = null;
      cfg = loadConfig();
      prompt();
    }
  }
}
