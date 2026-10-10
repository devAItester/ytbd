# {{ title }}

<a href="{{ channel_url }}">Открыть канал на YouTube</a>{% if channel_id %} · ID: {{ channel_id }}{% endif %}

_Краткий индекс · проверено: {{ checked_at }}_

{% for section in sections %}
## {{ section.title }} ({{ section.archive_count }})

{% for item in section.items %}
- {% if item.display_url %}<a href="{{ item.display_url }}">{{ item.title }}</a>{% else %}{{ item.title }}{% endif %}{% if item.upload_date %} — {{ item.upload_date }}{% endif %}
{% endfor %}
{% endfor %}
{% if errors %}
## Предупреждения

{% for error in errors %}
- {{ error }}
{% endfor %}
{% endif %}
