# {{ title|e }}

- **Канал:** <a href="{{ channel_url|e }}">{{ channel_url|e }}</a>
- **ID канала:** {{ channel_id|e }}
- **Проверено:** {{ checked_at|e }}

Это представление показывает JSON-метаданные, фактически сохранённые сборщиком yt-dlp. Структура полей не подменяется схемой YouTube Data API; отсутствующие у источника поля не выдумываются.

## Метаданные канала

<details>
<summary>channel.json — полный сохранённый объект</summary>

```json
{{ channel_data|tojson(indent=2) }}
```

</details>

## Разделы канала

{% for section in sections %}
## {{ section.title|e }} — {{ section.archive_count }} записей

{% if section.collection_error %}
Последняя попытка сбора завершилась ошибкой; сохранённый архив может быть устаревшим.
{% endif %}
{% for item in section["items"] %}
<details>
<summary>{{ item.title|e }} — ID: {{ item.id|e }}</summary>

```json
{{ item|tojson(indent=2) }}
```

</details>
{% set local = local_media.get(item.id|string) %}
{% if local %}
### Локальные файлы

- **Каталог:** `{{ local.directory|e }}/`
{% if local.metadata %}- **JSON метаданных:** `{{ local.metadata|e }}`
{% endif %}{% for path in local.thumbnails %}
- **Обложка:** `{{ path|e }}`
{% endfor %}{% for path in local.subtitles %}
- **Субтитры:** `{{ path|e }}`
{% endfor %}{% for path in local.transcripts %}
- **Транскрипт:** `{{ path|e }}`
{% endfor %}
{% endif %}

{% endfor %}
{% endfor %}
{% if errors %}
## Ошибки последней проверки

{% for error in errors %}
- {{ error|e }}
{% endfor %}
{% endif %}

## Локальные файлы

При запуске `full.md` с параметром `--download-media` сборщик сохраняет обложку, доступные ручные и автоматически созданные субтитры, текстовые транскрипты и JSON метаданных. Сам видеофайл не скачивается. Если YouTube не предоставляет субтитры, транскрипт не создаётся.
