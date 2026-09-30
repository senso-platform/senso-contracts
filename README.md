# senso-contracts

Контракты SensoBazaar: источник истины для `senso-backend`, `senso-frontend` и C++-шлюза.
Подключаются в `senso-backend` как git submodule в каталоге `contracts/`.

```
senso-contracts/
├─ mqtt/
│  ├─ TOPICS.md                  # топики, QoS, Last Will, ACL, лимиты
│  ├─ envelope.schema.json       # JSON Schema 2020-12, общий конвер сообщения
│  ├─ payloads/*.schema.json     # схемы полезных нагрузок по type
│  └─ examples/
│     ├─ valid/                  # проходят схему — обязательны для каждого типа
│     └─ invalid/                # падают по конкретной причине (см. scripts/validate_examples.py)
├─ openapi/
│  └─ senso-api.v1.yaml          # REST API 3.1: /api/v1 (Bearer JWT)
└─ scripts/
   └─ validate_examples.py       # локальная и CI-валидация примеров
```

## Правила изменения

1. Любое изменение — PR, апрув **обеих** затронутых сторон (backend TL; C++ — для `mqtt/`,
   frontend — для `openapi/`).
2. Несовместимые изменения envelope/payload: новая `schemaVersion` **и** новый `$id`
   (`...v2.json`), старая версия поддерживается не менее одного спринта.
   Добавление необязательного поля — совместимо, версию не повышать.
3. Каждое изменение схемы сопровождается примерами: минимум один `valid` и, если появилось
   новое отклонение, `invalid` с причиной в имени файла.
4. `openapi/` — contract-first: бэкенд генерирует интерфейсы из него, фронт — клиент.
   Пути и имена полей не «подстраивать под код», код подстраивается сюда.
5. CI обязан быть зелёным до мержа: валидация примеров + линт OpenAPI (см.
   `.github/workflows/validate.yml`).

## Проверка локально

```bash
pip install jsonschema openapi-spec-validator
python scripts/validate_examples.py          # примеры
python -c "from openapi_spec_validator import validate; import yaml; validate(yaml.safe_load(open('openapi/senso-api.v1.yaml')))"
```

## Связанные документы

- `docs/adr/ADR-0001-v2-backend-architecture.md` в `senso-backend` — разделы 6 (MQTT) и 9 (API).
- `docs/bootstrap/INIT-PLAN.md` Фаза 0 — уточнения (bootId, DEVICE_INVENTORY).
