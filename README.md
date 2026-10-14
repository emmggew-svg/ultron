# ULTRON

Yerel kişisel asistan. Tarayıcıda `http://localhost:3030` çalışır.

## Kurulum

```cmd
npm install -g .
openultron service start
```

Tarayıcı otomatik açılır. Arka planda çalıştırmak için:

```cmd
openultron service start -d
openultron service status
openultron service stop
```

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
openultron config set-model gemini-2.5-flash --provider gemini
openultron config show
```

Key yoksa **demo modda** çalışır.

Ayar dosyası: `~/.ultron/config.json`

## Geliştirme

```cmd
node ./src/server.js --port 3030
node ./bin/openultron.js service status
```
