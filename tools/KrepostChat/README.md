# Krepost Chat — отдельная программа оператора

Чат с Крепостью (Studio API) **с паролем**. TOTP/ключ — позже.

## Межсетевой мост (не тот же Wi‑Fi)

Порты в роутер **не** пробрасываем. Связь через **Tailscale** (уже в каноне Крепости).

### Один раз

1. Аккаунт на https://tailscale.com — один на Studio и Air  
2. Установить Tailscale на оба Mac, войти, Run at startup  
3. На **Studio**:
   ```bash
   export KREPOST_OPERATOR_PASSWORD='…'
   ./scripts/krepost_bridge_studio.sh
   ```
   Запомни URL вида `http://100.x.x.x:8000`  
4. На **Air**:
   ```bash
   ./scripts/krepost_bridge_air.sh
   # или: ./scripts/krepost_bridge_air.sh 100.x.x.x
   ```

### В Krepost Chat

Кнопки на экране входа:
- **Мост Tailscale** — подставить `100.x` Studio (другая сеть / мобильный интернет)
- **Домашний Wi‑Fi** — `http://10.0.0.1:8000`
- **Статус моста** — пиры Tailscale

Конфиг сохраняется в `~/.krepost/chat_bridge.json`.

## На Studio (сервер)

В launchd / env перед `serve_lmstudio`:

```bash
export KREPOST_OPERATOR_PASSWORD='ваш-длинный-пароль'
# опционально жёстко:
# export KREPOST_REQUIRE_AUTH=1
```

Без пароля API как раньше открыт (для локальных тестов).  
С паролем: `/v1/query`, `/v1/agent`, `/v1/ingest` только с `Authorization: Bearer <token>` после `POST /v1/login`.

Личные файлы → `vault/personal/` (+ индекс в RAG, если memory включена).

## На MacBook Air (клиент)

```bash
cd /Users/hervam/Krepost_Z.codeProject
git pull   # ветка с KrepostChat
chmod +x tools/KrepostChat/install_mac.sh
./tools/KrepostChat/install_mac.sh
```

Ярлык: `~/Applications/Krepost Chat.app`

В окне:
1. API: `http://10.0.0.1:8000` (Studio в LAN) или `http://127.0.0.1:8000`
2. Пароль оператора
3. Режимы: Быстрый / Vault / Агент
4. **Загрузить файл…** — личные `.md`/`.txt` в `vault/personal/`

## API

| Метод | Путь | Auth |
|-------|------|------|
| POST | `/v1/login` `{password}` | нет |
| POST | `/v1/query` | Bearer |
| POST | `/v1/agent` | Bearer |
| POST | `/v1/ingest` `{filename,content,private}` | Bearer |
| POST | `/v1/ingest/upload` multipart | Bearer |
| GET | `/health` | нет |
