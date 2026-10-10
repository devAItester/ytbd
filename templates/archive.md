# {{ title|e }} — архив

- **Канал:** <a href="{{ channel_url|e }}">{{ channel_url|e }}</a>
{% if channel_id %}- **ID:** {{ channel_id|e }}{{ "\n" }}{% endif %}
- **Последняя проверка:** {{ checked_at|e }}

Архив сохраняет ранее найденные записи, даже если они отсутствуют в текущем списке источника.

{% for section in sections %}
## {{ section.title|e }}

Архив: **{{ section.archive_count|e }}** · Сейчас в источнике: **{{ section.current_count|e }}**

{% if section.collection_error %}
Последняя попытка сбора завершилась ошибкой; сохранённый архив может быть устаревшим, а отсутствие новых записей не подтверждено.
{% endif %}
{% for item in section["items"] %}
<details>
<summary>{% if item.display_url %}<a href="{{ item.display_url|e }}">{{ item.title|e }}</a>{% else %}{{ item.title|e }}{% endif %} · ID: {{ item.id|e }}</summary>

{% if item.upload_date or item.release_date %}- **Дата:** {{ (item.upload_date or item.release_date)|e }}{% endif %}
{% if item.duration %}- **Длительность (сек.):** {{ item.duration|e }}{% endif %}
{% if item.description %}

**Описание**

{{ item.description|e }}
{% endif %}
</details>{{ '\n' }}

{% endfor %}
{% endfor %}
{% if errors %}
## Предупреждения

{% for error in errors %}
- {{ error|e }}
{% endfor %}
{% endif %}
