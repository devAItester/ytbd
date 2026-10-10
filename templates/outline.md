# {{ title }}

- **Канал:** <a href="{{ channel_url }}">{{ channel_url }}</a>
{% if channel_id %}- **ID:** {{ channel_id }}{% endif %}
- **Последняя проверка:** {{ checked_at }}

## Содержание канала

{% for section in sections %}
<details>
<summary>{{ section.title }} — {{ section.archive_count }} записей{% if section.current_count != section.archive_count %} (в текущем списке: {{ section.current_count }}){% endif %}</summary>

{% if section.items %}
{% for item in section.items %}
- {% if item.display_url %}<a href="{{ item.display_url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}{% if item.upload_date %} — {{ item.upload_date }}{% endif %}
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
- {{ error }}
{% endfor %}
{% endif %}

Исходные ответы и накопленный архив хранятся отдельно от этого представления.
