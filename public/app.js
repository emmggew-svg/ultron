const $ = (id) => document.getElementById(id);
const messagesEl = $("messages"), form = $("form"), input = $("input");
const orb = $("orb"), stateLine = $("stateLine"), statusEl = $("status");
const micBtn = $("micBtn"), micHint = $("micHint");
const speakBtn = $("speakBtn"), stopBtn = $("stopBtn"), autoTts = $("autoTts");
const modal = $("modal");

let history = [{ role: "system", content: "Sen ULTRON'sun: kısa, net, Türkçe konuşan yerel kişisel asistan. Gereksiz uzunluk yapma." }];
let lastReply = "";

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "you" ? "you" : role === "err" ? "bot err" : "bot");
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function speak(text) {
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "tr-TR";
    speechSynthesis.speak(u);
  } catch {}
}

async function refreshStatus() {
  try {
    const r = await fetch("/api/status").then((x) => x.json());
    statusEl.textContent = r.hasKey ? `çevrimiçi • ${r.model}` : "demo mod (key yok)";
  } catch {
    statusEl.textContent = "bağlantı yok";
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMsg("you", text);
  history.push({ role: "user", content: text });
  orb.classList.add("busy");
  stateLine.textContent = "Düşünüyorum…";
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history.slice(-20) }),
    }).then((x) => x.json());
    if (!r.ok) throw new Error(r.error || "hata");
    lastReply = r.reply;
    history.push({ role: "assistant", content: r.reply });
    addMsg("bot", r.reply);
    stateLine.textContent = "Hazırım.";
    if (autoTts.checked) speak(r.reply);
  } catch (err) {
    addMsg("err", "Hata: " + err.message);
    stateLine.textContent = "Bir sorun oldu.";
  } finally {
    orb.classList.remove("busy");
  }
});

speakBtn.onclick = () => lastReply && speak(lastReply);
stopBtn.onclick = () => { try { speechSynthesis.cancel(); } catch {} };

// --- Mic (optional, graceful) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) {
  micHint.textContent = "Bu tarayıcıda mikrofon diktesi yok — yazarak kullanabilirsin.";
  micBtn.style.opacity = ".4";
} else {
  const rec = new SR();
  rec.lang = "tr-TR";
  rec.interimResults = false;
  micBtn.onclick = () => {
    try { rec.start(); } catch {}
  };
  rec.onstart = () => { micBtn.classList.add("listening"); micHint.textContent = "Dinliyorum… konuş."; };
  rec.onend = () => { micBtn.classList.remove("listening"); micHint.textContent = ""; };
  rec.onresult = (e) => {
    const t = e.results[0][0].transcript;
    input.value = t;
    input.focus();
  };
  rec.onerror = (e) => { micHint.textContent = "Mikrofon hatası (" + e.error + ") — yazarak devam edebilirsin."; };
}

// --- Settings ---
$("settingsBtn").onclick = async () => {
  modal.classList.remove("hidden");
  try {
    const c = await fetch("/api/config").then((x) => x.json());
    $("fModel").value = c.model || "";
    $("fUrl").value = c.baseURL || "";
  } catch {}
};
$("closeBtn").onclick = () => modal.classList.add("hidden");
$("saveBtn").onclick = async () => {
  const body = {};
  if ($("fKey").value) body.apiKey = $("fKey").value;
  if ($("fModel").value) body.model = $("fModel").value;
  if ($("fUrl").value) body.baseURL = $("fUrl").value;
  await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  $("fKey").value = "";
  modal.classList.add("hidden");
  refreshStatus();
  addMsg("bot", "Ayarlar kaydedildi.");
};

addMsg("bot", "Selam, ben ULTRON. Sağdan yaz, istersen mikrofonla söyle, “Sesli anlat”la dinle. API key'i ⚙'dan ekleyebilirsin.");
refreshStatus();
