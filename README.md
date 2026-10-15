# ULTRON

Yerel kişisel asistan. Tarayıcıda `http://localhost:3030` çalışır.

## Kurulum

```cmd
npm install -g .
openultron start
```

`start` (veya `service start`) sorar:

```text
Which service do you want to start?
❯ OpenUltron Default  localhost web arayüzü (sesli + chat)
  openultron CLI      terminal agenti, Claude Code tarzi (sessiz)
```

Ok tuşlarıyla seç, Enter'a bas. Direkt açmak için:

```cmd
openultron start --web [-d]
openultron start --cli
openultron cli
```

Terminal agentinde ses yok; araç onayı `y/n` ile sorulur, `/provider`, `/model`, `/approval`, `/exit` komutları var.

## Sağlayıcılar (hepsi desteklenir)

| Sağlayıcı | Endpoint | Key nereden |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | https://platform.openai.com/api-keys |
| Anthropic (Claude) | `https://api.anthropic.com` | https://console.anthropic.com/ |
| Google Gemini | `https://generativelanguage.googleapis.com` | https://aistudio.google.com/apikey |
| NVIDIA Build | `https://integrate.api.nvidia.com/v1` | https://build.nvidia.com/ |

Tarayıcı ilk açıldığında hiç key girilmediyse **API anahtarı ekranı** otomatik çıkar. Sekmeden sağlayıcıyı seç, key + model + endpoint gir, kaydet. Veya terminalden:

```cmd
openultron config use gemini
openultron config set-key AIza... --provider gemini
openultron config set-model gemini-3.8-flash --provider gemini
openultron config show
```

Key yoksa **demo modda** çalışır.

Ayar dosyası: `~/.ultron/config.json`

## Web arayüzü (senin Next.js'in)

`web/` klasörü senin hazırladığın Next.js (Three.js orb + sağda chat paneli).
`openultron service start` ilk çalışta otomatik derler (`web/out`), sonra
:3030'dan statik sunar. Manuel derleme:

```cmd
openultron web build
```

Not: `web/`, eski Python backend'e (`localhost:8000`) değil, bu repodaki
Node backend'e (`/api/chat`, `/api/config`, `/api/status`) bağlıdır.

## Geliştirme

```cmd
node ./src/server.js --port 3030
node ./bin/openultron.js service status
```
