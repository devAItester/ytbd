# {{ title|e }}

<a href="{{ channel_url|e }}">Открыть канал на YouTube</a>{% if channel_id %} · ID: {{ channel_id|e }}{% endif %}

_Краткий индекс · проверено: {{ checked_at|e }}_

{% for section in sections %}
## {{ section.title|e }} ({{ section.archive_count|e }})

{% for item in section["items"] %}
- {% if item.display_url %}<a href="{{ item.display_url|e }}">{{ item.title|e }}</a>{% else %}{{ item.title|e }}{% endif %}{% if item.upload_date %} — {{ item.upload_date|e }}{% endif %}{{ "\n" }}
{% endfor %}
{% endfor %}
{% if errors %}
## Предупреждения

{% for error in errors %}
- {{ error|e }}
{% endfor %}
{% endif %}
