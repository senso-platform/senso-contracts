# MQTT-топики SensoBazaar (v1)

Префикс: `senso/v1/gw/{gatewayId}/`, где `gatewayId` — внешний id шлюза, `^[a-z0-9-]{3,64}$`.
Транспорт: MQTT 3.1.1, QoS 1. Вне localhost — только TLS (8883).

| Канал | Направление | Типы сообщений | QoS | Retained |
| --- | --- | --- | --- | --- |
| `telemetry` | шлюз → платформа | `TELEMETRY` | 1 | нет |
| `events` | шлюз → платформа | `DEVICE_DISCOVERED`, `DEVICE_INVENTORY`, `SECURITY_EVENT` | 1 | нет |
| `status` | шлюз → платформа | `GATEWAY_STATUS` (включая Last Will) | 1 | да |
| `cmd` | платформа → шлюз | зарезервировано (команды, не в MVP) | 1 | нет |
| `ack` | шлюз → платформа | зарезервано (подтверждения команд) | 1 | нет |

## Отражение в RabbitMQ

Брокер — RabbitMQ 4.x с MQTT-плагином, `mqtt.exchange = amq.topic`. Разделитель `/` превращается в `.`:

| MQTT-топик | Routing key на `amq.topic` |
| --- | --- |
| `senso/v1/gw/gw-01/telemetry` | `senso.v1.gw.gw-01.telemetry` |
| `senso/v1/gw/gw-01/events` | `senso.v1.gw.gw-01.events` |
| `senso/v1/gw/gw-01/status` | `senso.v1.gw.gw-01.status` |

Платформа подписывается на `senso.v1.gw.*.*` (очередь `q.ingest.raw`). `gatewayId` из ключа сверяется с полем `gatewayId` envelope — несовпадение отклоняется.

## Last Will и bootId

При подключении шлюз регистрирует LWT-сообщение в канале `status`:

- `payload.state = "OFFLINE"`, `bootId` **текущей** сессии, фиксированный `messageId`;
- `bootId` генерируется заново при каждом запуске процесса шлюза и меняется вместе с `GATEWAY_STATUS: ONLINE`;
- платформа считает статус недействительным, если `bootId` в `OFFLINE` не совпадает с последним `ONLINE` (устаревший Will от прошлой сессии).

## Авторизация

Логин MQTT равен `gatewayId`, пароль выдаётся при создании шлюза. ACL: публикация только в
`senso/v1/gw/<свой id>/...`, подписка только на `.../cmd`. До S2 — пользователи в
`definitions.json` брокера, с S2 — HTTP auth backend в `core-api`.

## Ограничения

- размер сообщения ≤ 256 КБ (принудительно и в брокере, и в `ingest`);
- ≤ 500 сэмплов в одном `TELEMETRY`;
- время только UTC ISO 8601 с миллисекундами; `sentAt` дальше +5 минут в будущее — отклонение;
- `messageId` сохраняется при повторной отправке (идемпотентность, QoS 1 допускает дубли).
