# {{ title }} — архив

- **Канал:** <a href="{{ channel_url }}">{{ channel_url }}</a>
{% if channel_id %}- **ID:** {{ channel_id }}{% endif %}
- **Последняя проверка:** {{ checked_at }}

Архив сохраняет ранее найденные записи, даже если они отсутствуют в текущем списке источника.

{% for section in sections %}
## {{ section.title }}

Архив: **{{ section.archive_count }}** · Сейчас в источнике: **{{ section.current_count }}**

{% for item in section.items %}
<details>
<summary>{% if item.display_url %}<a href="{{ item.display_url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %} · ID: {{ item.id }}</summary>

{% if item.upload_date or item.release_date %}- **Дата:** {{ item.upload_date or item.release_date }}{% endif %}
{% if item.duration %}- **Длительность (сек.):** {{ item.duration }}{% endif %}
{% if item.description %}

**Описание**

{{ item.description }}
{% endif %}
</details>

{% endfor %}
{% endfor %}
{% if errors %}
## Предупреждения

{% for error in errors %}
- {{ error }}
{% endfor %}
{% endif %}
