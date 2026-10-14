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

## API key bağlama

Arayüzde sağ üstteki ⚙'a bas, veya:

```cmd
openultron config set-key sk-...
openultron config set-model gpt-4o-mini
openultron config set-url https://api.openai.com/v1
```

Key yoksa **demo modda** çalışır (yazılabilir, konuşulabilir, ama LLM cevabı vermez).

Ayar dosyası: `~/.ultron/config.json`

## Geliştirme

```cmd
node ./src/server.js --port 3030
node ./bin/openultron.js service status
```
