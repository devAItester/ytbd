# {{ title|e }}

- **Канал:** <a href="{{ channel_url|e }}">{{ channel_url|e }}</a>
{% if channel_id %}- **ID:** {{ channel_id|e }}{% endif %}
- **Последняя проверка:** {{ checked_at|e }}

## Содержание канала

{% for section in sections %}
<details>
<summary>{{ section.title|e }} — {{ section.archive_count|e }} записей{% if section.current_count != section.archive_count %} (в текущем списке: {{ section.current_count|e }}){% endif %}</summary>

{% if section["items"] %}
{% for item in section["items"] %}
- {% if item.display_url %}<a href="{{ item.display_url|e }}">{{ item.title|e }}</a>{% else %}{{ item.title|e }}{% endif %}{% if item.upload_date %} — {{ item.upload_date|e }}{% endif %}
{% endfor %}
{% else %}
Пока нет сохранённых записей для этого раздела.
{% endif %}
</details>

{% endfor %}
{% if errors %}
## Предупреждения последней проверки

Часть источников не обновилась. Предыдущие сохранённые данные оставлены на месте.

{% for error in errors %}
- {{ error|e }}
{% endfor %}
{% endif %}

Исходные ответы и накопленный архив хранятся отдельно от этого представления.
