// Minimal OpenAI-compatible chat forwarder. No dependencies (uses global fetch).
export async function chatComplete({ baseURL, model, apiKey, messages }) {
  if (!apiKey) {
    // Demo mode: usable without a key.
    const last = messages?.at(-1)?.content ?? "";
    return `Demo moddayım (API key yok). Dediğin: "${String(last).slice(0, 200)}"\n\nAyarlar'dan API key ekle, gerçek cevaplara geçelim.`;
  }
  const url = `${baseURL.replace(/\/$/, "")}/chat/completions`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ model, messages, temperature: 0.7 }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`LLM ${res.status}: ${text.slice(0, 300)}`);
  }
  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error("LLM boş cevap döndü.");
  return content;
}
