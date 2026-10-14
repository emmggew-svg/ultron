import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { chatWithProvider } from "./providers.js";
import { runTool, needsApproval, toolPromptBlock, redact } from "./tools.js";

const SYSTEM_BASE = "Sen ULTRON'sun: kısa, net, Türkçe konuşan yerel kişisel asistan. Gereksiz uzunluk yapma.";

export const runs = new Map(); // runId -> { abort: bool, approvals: Map(seq -> resolve) }
let seq = 0;
const nextId = () => `run_${Date.now().toString(36)}_${(seq++).toString(36)}${Math.floor(Math.random() * 1e4).toString(36)}`;

function audit(entry) {
  try {
    const dir = path.join(os.homedir(), ".ultron");
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(path.join(dir, "audit.log"), JSON.stringify({ t: new Date().toISOString(), ...entry }) + "\n", "utf8");
  } catch {}
}

// Model cevabındaki ```tool {"name":..,"args":{..}}``` bloklarını çıkarır.
// Geriye kalan metni (temizlenmiş) ve araç listesini döndürür.
export function parseToolCalls(text) {
  const calls = [];
  const re = /```tool\s*([\s\S]*?)```/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    try {
      const obj = JSON.parse(m[1]);
      if (obj && typeof obj.name === "string") {
        calls.push({ name: obj.name, args: obj.args && typeof obj.args === "object" ? obj.args : {} });
      }
    } catch {}
  }
  const clean = String(text ?? "").replace(re, "").trim();
  return { calls, clean };
}

const TOOL_LABEL = {
  shell_run: "Kabuk",
  read_file: "Oku",
  list_dir: "Listele",
  grep: "Grep",
  write_file: "Yaz",
  edit_file: "Düzenle",
};
export const toolLabel = (name) => TOOL_LABEL[name] ?? name;

function approvalTimeoutMs() {
  return 5 * 60 * 1000;
}

// emit: (eventObj) => void  — örn. SSE yazıcı
// chatFn: (messages) => Promise<string>  — testlerde stub'lanabilir
export async function runAgent({ providerId, creds, messages, emit, chatFn, maxSteps = 12, requireApproval = true }) {
  const runId = nextId();
  const state = { abort: false, approvals: new Map() };
  runs.set(runId, state);
  const send = (obj) => emit({ runId, ...obj });

  send({ type: "start" });
  const convo = [
    { role: "system", content: SYSTEM_BASE + "\n\n" + toolPromptBlock() },
    ...messages.filter((m) => m.role !== "system"),
  ];

  const chat = chatFn ?? ((msgs) => chatWithProvider(providerId, creds, msgs));
  let answer = "";

  try {
    for (let step = 0; step < maxSteps; step++) {
      if (state.abort) {
        send({ type: "aborted" });
        audit({ runId, ev: "aborted" });
        return;
      }
      send({ type: "thinking", step });
      let reply;
      try {
        reply = await chat(convo);
      } catch (e) {
        if (e?.code === "NO_KEY") {
          send({ type: "demo" });
          return;
        }
        throw e;
      }
      const { calls, clean } = parseToolCalls(reply);

      if (calls.length === 0) {
        answer = clean || reply;
        convo.push({ role: "assistant", content: answer });
        send({ type: "message", content: answer });
        audit({ runId, ev: "done", steps: step });
        return;
      }

      // Düşünce metni varsa önce onu göster
      if (clean) {
        convo.push({ role: "assistant", content: clean });
        send({ type: "thought", content: clean });
      }

      for (const call of calls) {
        if (state.abort) {
          send({ type: "aborted" });
          return;
        }
        const n = state.approvals.size;
        const callSeq = `${step}.${n}`;
        const needAppr = requireApproval && needsApproval(call.name);

        send({ type: "tool_start", seq: callSeq, tool: call.name, label: toolLabel(call.name), args: call.args, needsApproval: needAppr });
        audit({ runId, ev: "tool", tool: call.name, args: redact(JSON.stringify(call.args)).slice(0, 500) });

        if (needAppr) {
          const approved = await new Promise((resolve) => {
            state.approvals.set(callSeq, resolve);
            send({ type: "approval_needed", seq: callSeq, tool: call.name, label: toolLabel(call.name), args: call.args });
            setTimeout(() => {
              if (state.approvals.has(callSeq)) {
                state.approvals.delete(callSeq);
                resolve(false);
              }
            }, approvalTimeoutMs());
          });
          if (state.abort) {
            send({ type: "aborted" });
            return;
          }
          if (!approved) {
            send({ type: "tool_result", seq: callSeq, tool: call.name, ok: false, output: "Kullanıcı reddetti." });
            convo.push({ role: "user", content: `[araç ${call.name} kullanıcı tarafından reddedildi]` });
            continue;
          }
        }

        send({ type: "tool_run", seq: callSeq, tool: call.name });
        const result = await runTool(call.name, call.args);
        send({ type: "tool_result", seq: callSeq, tool: call.name, ok: result.ok, output: result.output });
        convo.push({ role: "user", content: `[araç ${call.name} sonucu ok=${result.ok}]\n${result.output}` });
      }
    }
    send({ type: "message", content: "Adım limitine takıldım — daha küçük parçalara bölüp tekrar sor." });
  } catch (e) {
    send({ type: "error", error: String(e?.message ?? e) });
  } finally {
    runs.delete(runId);
  }
}

export function resolveApproval(runId, callSeq, approved) {
  const st = runs.get(runId);
  if (!st) return false;
  const fn = st.approvals.get(callSeq);
  if (!fn) return false;
  st.approvals.delete(callSeq);
  fn(!!approved);
  return true;
}

export function abortRun(runId) {
  const st = runs.get(runId);
  if (!st) return false;
  st.abort = true;
  for (const [, fn] of st.approvals) {
    try {
      fn(false);
    } catch {}
  }
  st.approvals.clear();
  return true;
}
