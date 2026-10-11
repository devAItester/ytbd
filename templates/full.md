# {{ title|e }}

- **Канал:** <a href="{{ channel_url|e }}">{{ channel_url|e }}</a>
- **ID канала:** {{ channel_id|e }}
- **Проверено:** {{ checked_at|e }}

Это представление показывает JSON-метаданные, фактически сохранённые сборщиком yt-dlp. Структура полей не подменяется схемой YouTube Data API; отсутствующие у источника поля не выдумываются.

========================

это блок ограниченный === в котором я пытаюсь тебе объяснить что в него добавить, а ты вносишь изменения  ТОЛЬКО в такой же блок ниже , я его смотрю и пишу тут пожелания за прделами блока ниже ничего править не надо - когда будет готово в блоке нижк - просто удалим лишний вывод - это файл человекочитаемого вывода рав - не более.

# {{ title|e }}

_update: {{ checked_at|e }}_
<details>
<summary>local</summary>
  
<ul>
<li>one</li>
<li>two</li>
</ul>
</details>
<details>
<summary>meta</summary>
<ul>
<li>one</li>
<li>two</li>
<li>
<summary>twos</summary>
<ul>
<li>one</li>
<li>two</li>
</ul>
</details>

<details>
<summary>название первого раздела канала</summary>
<ul>
<li>one</li>
<li>two</li>
</ul>
</details>

<details>
<summary>название второго раздела канала</summary>
<ul>
<li>one</li>
<li>two</li>
</ul>
</details>
...

========================




## Метаданные канала

<details>
<summary>channel.json — полный сохранённый объект</summary>

```json
{{ channel_data|tojson(indent=2) }}
```

</details>

## Разделы канала

{% set channel_local = local_media.get("_channel", {}) %}
{% if channel_local %}
## Локальные изображения канала

{% for name, path in channel_local.items() %}
- **{{ name|e }}:** `{{ path|e }}`
{% endfor %}
{% endif %}

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
{% endfor %}
{% endfor %}
{% if errors %}
## Ошибки последней проверки

{% for error in errors %}
- {{ error|e }}
{% endfor %}
{% endif %}
{% if detail_errors %}
## Замечания подробного сбора

Часть записей не удалось дополнить полными метаданными. Исходные поля плоского архива сохранены.

{% for error in detail_errors %}
- {{ error|e }}
{% endfor %}
{% endif %}

## Локальные файлы

При запуске `full.md` с параметром `--download-media` сборщик сохраняет доступные обложки канала и видео, ручные и автоматически созданные субтитры, текстовые транскрипты и JSON метаданных. Сам видеофайл не скачивается. Если YouTube не предоставляет субтитры, транскрипт не создаётся.

{% for video_id, local in local_media.items() if video_id != "_channel" %}
<details>
<summary>Видео ID: {{ video_id|e }}</summary>

- **Каталог:** `{{ local.directory|e }}/`
{% if local.metadata %}- **JSON метаданных:** `{{ local.metadata|e }}`
{% endif %}{% for path in local.thumbnails %}
- **Обложка:** `{{ path|e }}`
{% endfor %}{% for path in local.subtitles %}
- **Субтитры:** `{{ path|e }}`
{% endfor %}{% for path in local.transcripts %}
- **Транскрипт:** `{{ path|e }}`
{% endfor %}
</details>

{% endfor %}
