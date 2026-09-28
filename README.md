# TSUTMB Hostel

VK-бот для управления данными общежития и синхронизации с Google Sheets.

## Конфигурация

Production-конфигурация передаётся через environment variables. Секреты не хранятся в Git.

Обязательные переменные:

- `GROUP_ACCESS_TOKEN` — токен VK-группы.
- `CONVERSATION_ID` — основной peer/conversation ID.
- `ADMINS_CONVERSATION_ID` — peer/conversation ID администраторов.
- `SPREADSHEET_ID` — ID Google Sheets документа.
- `SHEETS_SERVICE_ACCOUNT_JSON` — полный JSON Google service account. Для локальной разработки вместо него можно использовать `SHEETS_SERVICE_ACCOUNT_FILENAME` и файл в `resources/`.

Остальные значения и defaults перечислены в `.env.example`.

## Observability

Основной канал наблюдаемости — OpenTelemetry OTLP/HTTP. Приложение экспортирует логи и traces с единым resource:

- `service.name=tsutmb-hostel`;
- `service.version` из `OTEL_SERVICE_VERSION`;
- `deployment.environment.name` из `OTEL_ENVIRONMENT`.

Настройки:

- `OTEL_ENABLED=true`;
- `OTEL_EXPORTER_OTLP_ENDPOINT=https://collector.example.com`;
- `OTEL_EXPORTER_OTLP_HEADERS` — необязательные `key=value` пары через запятую;
- `OTEL_LOG_LEVEL=INFO`.

К базовому endpoint автоматически добавляются `/v1/logs` и `/v1/traces`.

Трассируются значимые операции приложения: startup VK/Google Sheets, загрузка и обновление базы, Google Sheets read/write, команды пользователей и изменения состава беседы. Тексты сообщений, токены и содержимое таблицы в span attributes не записываются.

Логи, созданные внутри активного span, экспортируются с его trace context. Файлового логирования в приложении нет. `LOG_CONSOLE_ENABLED` управляет только аварийным/операционным stderr для Docker/Coolify.

## Локальный запуск

1. Скопировать `.env.example` в `.env` и заполнить значения.
2. При использовании file-based Google credentials положить `service_account.json` в `resources/`.
3. Запустить `docker compose up --build`.

`resources/`, `.env` и service-account credentials исключены из Git и Docker build context.

## Deployment

Для Coolify приложение собирается напрямую из `Dockerfile`. Environment variables задаются в Coolify; production service-account JSON передаётся через `SHEETS_SERVICE_ACCOUNT_JSON`, поэтому отдельный credential-файл и persistent volume для него не нужны.

GitHub Actions выполняет Ruff, format check, Python compile check и проверочную Docker-сборку. CI не публикует production image: deployment platform сама собирает выбранный commit.
