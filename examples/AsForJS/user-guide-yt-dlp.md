# YouTube / yt-dlp: пользовательская инструкция для AsForJS

## Для чего этот документ

Это инструкция для пользователя: как подготовить среду, выяснить реальные возможности инструмента, понять выбор способа и повторить действия готовыми командами. Рабочий контекст для следующего этапа анализа находится отдельно в `continue-tree-work.md`.

- Канал: https://www.youtube.com/@AsForJS
- Репозиторий: https://github.com/devAItester/aishare
- Каталог: `Archive/YouTube Transcript Copy/summaries/yt-dlp/AsForJS/`

## 1. Почему выбран yt-dlp

Для этой задачи нужен не видеофайл, а структура канала: названия, URL, ID, порядок записей и содержимое плейлистов. Поэтому выбран **yt-dlp**: он получает метаданные YouTube, может выдавать их в JSON и позволяет обрабатывать результат без скачивания самих видео. JSON подходит как исходный формат; Python-скрипт объединяет данные, а Markdown представляет их в виде читаемого дерева.

Ограничения: результат отражает доступные инструменту данные в момент сбора. Удалённые, приватные и недоступные записи могут отсутствовать. Наличие плейлиста в метаданных ещё не доказывает, что его элементы собраны полностью. Успешное завершение команды не заменяет проверки количества записей, логов и структуры JSON.

## 2. Сначала проверь среду

Сейчас используется Windows 11 с Git for Windows Git Bash (mintty). Здесь `$HOME` — обычно `/c/Users/Nikos`; пути из Arch Linux не переносятся автоматически. Не делай вывод о потере данных, если локального каталога нет: сначала проверь удалённый GitHub.

В Git Bash:

```bash
printf '%s\\n' '=== Environment ==='
uname -a
printf 'HOME=%s\\nMSYSTEM=%s\\n' "$HOME" "${MSYSTEM:-unset}"

printf '\\n%s\\n' '=== Tools and versions ==='
for tool in git python python3 yt-dlp; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%-10s %s\\n' "$tool" "$(command -v "$tool")"
  else
    printf '%-10s NOT FOUND\\n' "$tool"
  fi
done
git --version
python --version 2>/dev/null || true
yt-dlp --version 2>/dev/null || true

printf '\\n%s\\n' '=== Expected local paths ==='
for p in "$HOME/youtube/AsForJS" "$HOME/dev/devAItester/aishare"; do
  test -e "$p" && echo "FOUND  $p" || echo "MISSING $p"
done
```

Если `MISSING`, это означает только отсутствие по указанному пути в этой Windows-среде.

## 3. Установка yt-dlp и проверка возможностей

Сначала проверь, установлен ли инструмент. Если команда `yt-dlp --version` уже работает, переустанавливать его не нужно.

Для среды Windows с доступным Python:

```bash
python -m pip --version
python -m pip install --upgrade yt-dlp
yt-dlp --version
```

Если `python` не найден, проверь Python Launcher (`py -m pip --version`) в PowerShell и установи Python для Windows. Не смешивай установки Windows и Arch Linux: это отдельные среды.

Проверить справку и небольшой запрос метаданных, не скачивая видео:

```bash
yt-dlp --help
yt-dlp --flat-playlist --dump-single-json 'https://www.youtube.com/@AsForJS/videos' > /tmp/asforjs-videos.json
python -c "import json; d=json.load(open('/tmp/asforjs-videos.json', encoding='utf-8')); print('title:', d.get('title')); print('entries:', len(d.get('entries') or [])); print('keys:', ', '.join(sorted(d.keys())))"
```

Если запрос завершается ошибкой, сначала изучи текст ошибки и версию yt-dlp. Не делай вывод, что канал пуст, и не переходи к другому инструменту без диагностики.

## 4. Как выясняем возможности и выбираем метод

Порядок принятия решения:

1. Проверяем, не собраны ли нужные данные раньше.
2. Изучаем реальную структуру JSON: ключи, вложенные `entries`, ID, URL, порядок и количество элементов.
3. Проверяем yt-dlp на небольшом запросе, прежде чем запускать массовый сбор.
4. Сравниваем результат с требованиями: для дерева нужны названия, ссылки, порядок и все доступные элементы, а не видеофайлы.
5. Сохраняем исходные JSON отдельно; строим Markdown как производное представление.
6. Сверяем счётчики и ошибки, затем повторно открываем опубликованные файлы на GitHub.

Метод выбирается не по принципу «команда отработала», а по тому, сохраняет ли он необходимые данные и позволяет ли проверить полноту.

## 5. Что уже есть

В удалённом каталоге сохранены исходные JSON и логи вкладок, `tree-data.json`, `collect.py`, каталог `items/`, данные эксперимента с отдельным видео, краткое дерево и полное дерево.

- [Каталог AsForJS](https://github.com/devAItester/aishare/tree/main/Archive/YouTube%20Transcript%20Copy/summaries/yt-dlp/AsForJS)
- [Полное дерево канала](https://github.com/devAItester/aishare/blob/main/Archive/YouTube%20Transcript%20Copy/summaries/yt-dlp/AsForJS/channel-tree-full.md)
- [Объединённые данные JSON](https://github.com/devAItester/aishare/blob/main/Archive/YouTube%20Transcript%20Copy/summaries/yt-dlp/AsForJS/tree-data.json)

В сохранённом снимке: Videos — 6 записей; Streams — 253; вкладка Podcasts — 21; вкладка Playlists — 24; раскрыты 24 списка с суммарно 272 элементами; поле ошибок в `tree-data.json` пустое. Это счётчики снимка, а не подтверждение текущей актуальности данных на YouTube.

## 6. Конечный набор команд для повседневных задач

### Открыть готовый результат

- [Полное дерево](https://github.com/devAItester/aishare/blob/main/Archive/YouTube%20Transcript%20Copy/summaries/yt-dlp/AsForJS/channel-tree-full.md)
- [Все файлы AsForJS](https://github.com/devAItester/aishare/tree/main/Archive/YouTube%20Transcript%20Copy/summaries/yt-dlp/AsForJS)

Для просмотра опубликованного дерева локальная установка yt-dlp и клонирование репозитория не требуются.

### Найти локальный clone репозитория

```bash
find "$HOME" -maxdepth 5 -type d -path '*/devAItester/aishare/.git' -print 2>/dev/null
```

Если ничего не выведено, clone в домашнем каталоге не найден. Не подставляй предполагаемый путь в команды Git.

### Проверить локальный clone

Подставь в `repo` точный путь, найденный предыдущей командой:

```bash
repo='/c/точный/путь/к/aishare'
git -C "$repo" status --short
git -C "$repo" log -1 --oneline
git -C "$repo" ls-files 'Archive/YouTube Transcript Copy/summaries/yt-dlp/AsForJS'
```

### Обновить локальный clone

```bash
repo='/c/точный/путь/к/aishare'
git -C "$repo" pull --ff-only
git -C "$repo" log -1 --oneline
```

После этого всё равно открой нужный файл на GitHub и проверь опубликованное содержимое: успешный pull или commit не доказывает корректность дерева.

### Повторить сбор данных

Не запускай `collect.py` вслепую. Сначала прочитай его содержимое и логи, выясни параметры, выходные пути и поведение при перезаписи. Новый сбор лучше сохранять отдельно от исходного снимка, затем сравнить количество записей и ошибки. Только после проверки заменяй производный результат и публикуй изменения.

## 7. Критерии готовности

- Исходные JSON не затёрты производным Markdown.
- Сохранены исходные названия, прямые ссылки и порядок.
- Включены все доступные элементы списков, а не только первые несколько.
- Повторяющиеся ролики в разных плейлистах не удалены молча.
- Счётчики сверены с JSON, ошибки и ограничения обозначены.
- После публикации файл повторно прочитан с GitHub.

## 8. Два документа — две задачи

- `user-guide-yt-dlp.md` — как пользователю подготовить среду, проверить инструмент, понять выбор метода и повторить действия.
- `continue-tree-work.md` — рабочий контекст для ИИ: что сделано, какие файлы изучить и что проверить дальше.

При изменении процесса обновляй обе инструкции: пользовательскую — если меняются установка, выбор метода или команды; рабочую — если меняются состояние проекта и оставшиеся аналитические задачи.
