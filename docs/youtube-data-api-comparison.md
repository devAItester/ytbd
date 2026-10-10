# YouTube Data API v3: официальные методы и ytbd

Сверка выполнена 2026-10-11 по [официальному справочнику YouTube Data API v3](https://developers.google.com/youtube/v3/docs). Это инвентаризация ресурсов и методов официального API и сопоставление с текущей реализацией проекта, а не заявление о полноте данных конкретного канала.

## Главный вывод

**На данный момент ytbd напрямую не вызывает методы YouTube Data API v3.** В проекте нет вызовов https://www.googleapis.com/youtube/v3/.... Вместо них используются:

- yt-dlp для JSON-метаданных канала, плоских списков записей и подробных метаданных видео;
- публичный HTML канала для обнаружения вкладок навигации;
- yt-dlp для получения доступных изображений и субтитров при включённом сборе локальных материалов;
- собственные JSON-файлы проекта для сырого снимка, истории, накопленного архива и статуса.

Поэтому колонка «Разница / пробел» не означает автоматически, что проект обязан реализовать данный метод. Она показывает, что официальная возможность не вызывается напрямую; необходимость добавления определяется задачами проекта.

## Полный перечень ресурсов и методов из справочника

`list` означает чтение, `insert` — создание, `update` — изменение, `delete` — удаление. Некоторые методы требуют OAuth 2.0 и прав владельца; список ниже не означает, что их можно вызывать анонимно.

| Ресурс API | Методы из официальной документации | Что сопоставимо в ytbd сейчас | Разница / пробел |
|---|---|---|---|
| [Activities](https://developers.google.com/youtube/v3/docs/activities) | list | Нет отдельного источника событий активности | Активности не собираются; вкладки канала не эквивалентны ленте активности |
| [Captions](https://developers.google.com/youtube/v3/docs/captions) | list, download, insert, update, delete | yt-dlp получает доступные субтитры и сохраняет RU/EN дорожки по флагу | Это не вызовы captions.list/download; доступность и набор дорожек могут отличаться |
| [ChannelBanners](https://developers.google.com/youtube/v3/docs/channelBanners) | insert | Изображения канала могут сохраняться из URL, полученных yt-dlp | Нет официального channelBanners.insert; нет управления баннерами |
| [Channels](https://developers.google.com/youtube/v3/docs/channels) | list, update | Метаданные канала из yt-dlp; URL вкладок извлекаются из HTML | Нет прямого channels.list; поля и структура ответа отличаются от API schema |
| [ChannelSections](https://developers.google.com/youtube/v3/docs/channelSections) | list, insert, update, delete | Обнаруживаются публичные вкладки канала | Вкладки (videos, playlists и т. п.) не равны оформленным полкам channelSections; полки API не запрашиваются |
| [Comments](https://developers.google.com/youtube/v3/docs/comments) | list, insert, update, delete, setModerationStatus | Нет | Комментарии и модерация не собираются |
| [CommentThreads](https://developers.google.com/youtube/v3/docs/commentThreads) | list, insert | Нет | Ветки комментариев не собираются |
| [i18nLanguages](https://developers.google.com/youtube/v3/docs/i18nLanguages) | list | Нет отдельного запроса справочника языков API | Нет прямого получения списка поддерживаемых языков интерфейса |
| [i18nRegions](https://developers.google.com/youtube/v3/docs/i18nRegions) | list | Нет отдельного запроса справочника регионов API | Нет прямого получения списка регионов |
| [Members](https://developers.google.com/youtube/v3/docs/members) | list | Нет | Список платных участников канала не собирается; API требует авторизации владельца |
| [MembershipsLevels](https://developers.google.com/youtube/v3/docs/membershipsLevels) | list | Нет | Уровни платного членства не собираются; API требует авторизации |
| [PlaylistImages](https://developers.google.com/youtube/v3/docs/playlistImages) | list, insert, update, delete | Метаданные плейлистов и доступные URL изображений могут приходить через yt-dlp | Нет прямого доступа к ресурсу playlistImages и управления изображениями плейлистов |
| [PlaylistItems](https://developers.google.com/youtube/v3/docs/playlistItems) | list, insert, update, delete | yt-dlp получает элементы списков/плейлистов в составе вкладок | Нет прямого playlistItems.list; нужно сравнивать ID, порядок, пагинацию и поля отдельно |
| [Playlists](https://developers.google.com/youtube/v3/docs/playlists) | list, insert, update, delete | Сбор вкладки плейлистов и доступных метаданных через yt-dlp | Нет прямого playlists.list; создание, редактирование и удаление не являются задачами проекта |
| [Search](https://developers.google.com/youtube/v3/docs/search) | list | Каналы вводятся пользователем в config/channels.txt | Поиск YouTube API не используется; обнаружение вкладок — не поиск видео/каналов |
| [Subscriptions](https://developers.google.com/youtube/v3/docs/subscriptions) | list, insert, delete | config/channels.txt — список каналов, выбранных пользователем | Этот файл не является списком подписок аккаунта YouTube; API подписок не вызывается |
| [Thumbnails](https://developers.google.com/youtube/v3/docs/thumbnails) | set | yt-dlp может скачивать доступные обложки/thumbnail-файлы | Проект получает/скачивает существующие изображения, но не вызывает thumbnails.set и не меняет обложки на YouTube |
| [VideoAbuseReportReasons](https://developers.google.com/youtube/v3/docs/videoAbuseReportReasons) | list | Нет | Справочник причин жалоб не нужен текущему сбору и не запрашивается |
| [VideoCategories](https://developers.google.com/youtube/v3/docs/videoCategories) | list | Если категория присутствует, она сохраняется как поле метаданных yt-dlp | Нет прямого запроса справочника категорий |
| [Videos](https://developers.google.com/youtube/v3/docs/videos) | list, batchGetStats, insert, update, delete, rate, getRating, reportAbuse | yt-dlp получает подробные JSON-метаданные видео; локально сохраняется meta.json | Нет прямого videos.list / batchGetStats; API-оценки, загрузка, изменение, удаление и жалобы не выполняются |
| [Watermarks](https://developers.google.com/youtube/v3/docs/watermarks) | set, unset | Нет | Управление водяными знаками не выполняется |

> Справочник API обновляется. Перед решением о реализации конкретного метода сверяйся с его официальной страницей; таблица фиксирует состояние документации на дату выше.

## Полезные различия при сравнении данных

| Область | Текущий источник проекта | Официальный API | Что сравнивать |
|---|---|---|---|
| Метаданные канала | yt-dlp JSON | channels.list | ID, название, описание, ссылки, изображения, статистику, доступные поля |
| Вкладки и списки записей | HTML-навигация + yt-dlp | Несколько ресурсов, включая playlistItems.list и playlists.list | Полноту вкладок, количество, порядок, ID, обработку пагинации |
| Подробные данные видео | yt-dlp JSON | videos.list | Пересечение полей, различия формата, доступность статистики и статуса |
| Субтитры | yt-dlp tracks/captions | captions.list / captions.download | Наличие дорожек, язык, ручные/автоматические дорожки, доступ к тексту |
| Обложки | URL из метаданных и локальное скачивание | thumbnails описывает управление пользовательской обложкой; URL миниатюр обычно входят в ресурсы | Доступные размеры, URL, качество и наличие локального файла |
| Комментарии | Не собираются | commentThreads.list и comments.list | Не применимо до появления отдельного требования |
| Подписки | Пользовательский список URL | subscriptions.list | Не сравнивать как эквивалент: источники имеют разный смысл |

## Ограничения интерпретации

- Наличие похожего поля в yt-dlp JSON не доказывает, что оно получено тем же способом или соответствует конкретному полю Data API.
- Различие структуры не обязательно означает потерю данных. Сначала сравнивай смысл, значения и доступность полей.
- YouTube Data API требует API key или OAuth 2.0; операции изменения и доступ к приватным данным требуют авторизации. Добавление API повлияет на настройки, квоты, авторизацию и тестирование.
- Не добавляй API только ради совпадения со справочником. Сначала сформулируй конкретный пробел, который мешает цели проекта.

## Официальные источники

- [Полный справочник YouTube Data API v3](https://developers.google.com/youtube/v3/docs)
- [Обзор и поддерживаемые операции](https://developers.google.com/youtube/v3/getting-started)
- [Channels](https://developers.google.com/youtube/v3/docs/channels)
- [Videos](https://developers.google.com/youtube/v3/docs/videos)
- [Playlists](https://developers.google.com/youtube/v3/docs/playlists)
- [PlaylistItems](https://developers.google.com/youtube/v3/docs/playlistItems)
- [Search](https://developers.google.com/youtube/v3/docs/search)
- [Captions](https://developers.google.com/youtube/v3/docs/captions)
