const $ = (id) => document.getElementById(id);
const messagesEl = $("messages"), form = $("form"), input = $("input");
const stateLine = $("stateLine"), statusEl = $("status");
const micBtn = $("micBtn"), micHint = $("micHint");
const speakBtn = $("speakBtn"), stopBtn = $("stopBtn"), autoTts = $("autoTts");
const modal = $("modal"), tabsEl = $("tabs");

let history = [{ role: "system", content: "Sen ULTRON'sun: kısa, net, Türkçe konuşan yerel kişisel asistan. Gereksiz uzunluk yapma." }];
let lastReply = "";
let cfg = null;       // /api/config sonucu
let activeTab = null; // ayarlarda görünen sağlayıcı

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

function maskOf(p) {
  return p.hasKey ? `（${p.masked}）` : "";
}

function renderTabs() {
  tabsEl.innerHTML = "";
  for (const [id, p] of Object.entries(cfg.providers)) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tab" + (id === activeTab ? " on" : "") + (id === cfg.activeProvider ? " active" : "");
    b.textContent = (id === cfg.activeProvider ? "★ " : "") + p.label + (p.hasKey ? " ✓" : "");
    b.onclick = () => { activeTab = id; renderTabs(); fillFields(); };
    tabsEl.appendChild(b);
  }
}

function fillFields() {
  const p = cfg.providers[activeTab];
  $("provInfo").innerHTML = "";
  const a = document.createElement("a");
  a.href = p.keyUrl;
  a.target = "_blank";
  a.rel = "noopener";
  a.textContent = "🔑 " + p.label + " key al →";
  $("provInfo").appendChild(a);
  const hint = document.createElement("span");
  hint.textContent = " " + p.keyHint + " " + maskOf(p);
  $("provInfo").appendChild(hint);
  $("fKey").placeholder = p.hasKey ? "Kayıtlı " + p.masked + " (değiştirmek için yaz)" : p.keyHint;
  $("fKey").value = "";
  $("fModel").value = p.model || "";
  $("fUrl").value = p.baseURL || "";
  $("useBtn").textContent = activeTab === cfg.activeProvider ? "★ Aktif (şu an bu kullanılıyor)" : "★ Aktif olarak kullan";
}

async function openSettings(welcome) {
  try {
    cfg = await fetch("/api/config").then((x) => x.json());
  } catch {
    addMsg("err", "Ayarlar yüklenemedi — server çalışıyor mu?");
    return;
  }
  if (!activeTab || !cfg.providers[activeTab]) activeTab = cfg.activeProvider;
  $("welcome").classList.toggle("hidden", !welcome);
  $("modalTitle").textContent = welcome ? "API Anahtarı Gerekli" : "Ayarlar";
  $("demoBtn").style.display = welcome ? "" : "none";
  renderTabs();
  fillFields();
  modal.classList.remove("hidden");
}

async function refreshStatus() {
  try {
    const r = await fetch("/api/status").then((x) => x.json());
    const label = r.activeProvider ? r.activeProvider : "?";
    statusEl.textContent = r.hasKey ? `çevrimiçi • ${label} • ${r.model}` : (r.hasAnyKey ? `demo • key bu sağlayıcıda yok (${label})` : "demo mod (key yok)");
    return r;
  } catch {
    statusEl.textContent = "bağlantı yok";
    return null;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMsg("you", text);
  history.push({ role: "user", content: text });
  stateLine.textContent = "Düşünüyorum…";
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history.slice(-20) }),
    }).then((x) => x.json());
    if (!r.ok) throw new Error(r.error || "hata");
    if (r.demo) {
      addMsg("bot", "Bu sağlayıcıda API key yok — demo moddayım. ⚙'dan key ekle, gerçek cevaplara geçelim.");
      openSettings(true);
      return;
    }
    lastReply = r.reply;
    history.push({ role: "assistant", content: r.reply });
    addMsg("bot", r.reply);
    stateLine.textContent = "Hazırım.";
    if (autoTts.checked) speak(r.reply);
  } catch (err) {
    addMsg("err", "Hata: " + err.message);
    stateLine.textContent = "Bir sorun oldu.";
  }
});

speakBtn.onclick = () => lastReply && speak(lastReply);
stopBtn.onclick = () => { try { speechSynthesis.cancel(); } catch {} };

// --- Mikrofon (opsiyonel) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) {
  micHint.textContent = "Bu tarayıcıda mikrofon diktesi yok — yazarak kullanabilirsin.";
  micBtn.style.opacity = ".4";
} else {
  const rec = new SR();
  rec.lang = "tr-TR";
  rec.interimResults = false;
  micBtn.onclick = () => { try { rec.start(); } catch {} };
  rec.onstart = () => { micBtn.classList.add("listening"); micHint.textContent = "Dinliyorum… konuş."; };
  rec.onend = () => { micBtn.classList.remove("listening"); micHint.textContent = ""; };
  rec.onresult = (e) => { input.value = e.results[0][0].transcript; input.focus(); };
  rec.onerror = (e) => { micHint.textContent = "Mikrofon hatası (" + e.error + ") — yazarak devam edebilirsin."; };
}

// --- Ayarlar ---
$("settingsBtn").onclick = () => openSettings(false);
$("closeBtn").onclick = () => modal.classList.add("hidden");
$("demoBtn").onclick = () => modal.classList.add("hidden");
$("useBtn").onclick = async () => {
  await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ activeProvider: activeTab }) });
  cfg.activeProvider = activeTab;
  renderTabs();
  fillFields();
  refreshStatus();
};
$("saveBtn").onclick = async () => {
  const body = { providers: { [activeTab]: {} } };
  if ($("fKey").value) body.providers[activeTab].apiKey = $("fKey").value;
  if ($("fModel").value) body.providers[activeTab].model = $("fModel").value;
  if ($("fUrl").value) body.providers[activeTab].baseURL = $("fUrl").value;
  const r = await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((x) => x.json());
  if (r.ok) cfg = r.config;
  $("fKey").value = "";
  renderTabs();
  fillFields();
  refreshStatus();
  addMsg("bot", cfg.providers[activeTab].label + " ayarları kaydedildi." + (cfg.providers[activeTab].hasKey ? "" : " (Key girilmedi — demo mod.)"));
};

(async function init() {
  addMsg("bot", "Selam, ben ULTRON. Sağdan yaz, istersen mikrofonla söyle, “Sesli anlat”la dinle.");
  const st = await refreshStatus();
  if (st && !st.hasAnyKey) openSettings(true); // daha önce hiç key girilmediyse key ekranı
})();
