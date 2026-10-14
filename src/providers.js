// Sağlayıcı istekleri — endpoint'ler resmi dokümanlardan alındı (Ekim 2026):
// - OpenAI:    POST {baseURL}/chat/completions, Authorization: Bearer <key>
//              https://platform.openai.com/docs/api-reference/chat
// - NVIDIA:    POST https://integrate.api.nvidia.com/v1/chat/completions,
//              Authorization: Bearer <nvapi-...> (OpenAI-uyumlu şema)
//              https://build.nvidia.com/
// - Anthropic: POST https://api.anthropic.com/v1/messages,
//              headers: x-api-key + anthropic-version: 2023-06-01,
//              body: {model, max_tokens, messages}
//              https://platform.claude.com/docs/en/api/messages
// - Gemini:    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent,
//              header: x-goog-api-key: <key>,
//              body: {contents: [{role, parts: [{text}]}]}
//              https://ai.google.dev/api/generate-content

export const PROVIDERS = {
  openai: {
    label: "OpenAI",
    keyUrl: "https://platform.openai.com/api-keys",
    keyHint: "sk-… ile başlar",
  },
  anthropic: {
    label: "Anthropic (Claude)",
    keyUrl: "https://console.anthropic.com/",
    keyHint: "sk-ant-… ile başlar",
  },
  gemini: {
    label: "Google Gemini",
    keyUrl: "https://aistudio.google.com/apikey",
    keyHint: "Google AI Studio'dan alınır",
  },
  nvidia: {
    label: "NVIDIA Build",
    keyUrl: "https://build.nvidia.com/",
    keyHint: "nvapi-… ile başlar",
  },
};

function noKey() {
  const e = new Error("Bu sağlayıcı için API key girilmedi.");
  e.code = "NO_KEY";
  return e;
}

async function failIfBad(res, name) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${name} ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}

// OpenAI + NVIDIA (ikisi de OpenAI-uyumlu /chat/completions şeması)
async function chatOpenAICompatible({ baseURL, apiKey, model, messages }) {
  if (!apiKey) throw noKey();
  const url = `${baseURL.replace(/\/$/, "")}/chat/completions`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, messages, temperature: 0.7 }),
  });
  const data = await failIfBad(res, "LLM");
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error("LLM boş cevap döndü.");
  return content;
}

async function chatAnthropic({ apiKey, model, messages }) {
  if (!apiKey) throw noKey();
  const system = messages.filter((m) => m.role === "system").map((m) => m.content).join("\n");
  const rest = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role === "assistant" ? "assistant" : "user", content: String(m.content ?? "") }));
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({ model, max_tokens: 1024, ...(system ? { system } : {}), messages: rest }),
  });
  const data = await failIfBad(res, "Anthropic");
  const text = (data?.content ?? []).filter((b) => b.type === "text").map((b) => b.text).join("");
  if (!text) throw new Error("Anthropic boş cevap döndü.");
  return text;
}

async function chatGemini({ apiKey, model, messages }) {
  if (!apiKey) throw noKey();
  const system = messages.filter((m) => m.role === "system").map((m) => m.content).join("\n");
  const contents = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: String(m.content ?? "") }] }));
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
    body: JSON.stringify({ ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}), contents }),
  });
  const data = await failIfBad(res, "Gemini");
  const text = (data?.candidates?.[0]?.content?.parts ?? []).map((p) => p.text ?? "").join("");
  if (!text) throw new Error("Gemini boş cevap döndü: " + JSON.stringify(data).slice(0, 200));
  return text;
}

export async function chatWithProvider(id, creds, messages) {
  if (id === "anthropic") return chatAnthropic({ ...creds, messages });
  if (id === "gemini") return chatGemini({ ...creds, messages });
  return chatOpenAICompatible({ ...creds, messages }); // openai + nvidia
}
