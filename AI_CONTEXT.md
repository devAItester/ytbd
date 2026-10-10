# AI context — ytbd

> Read this file before changing code or templates. It records the project intent and the current handoff point.

## Project goal

ytbd collects and archives public YouTube channel data, then renders Markdown views from the saved data. The next task is **presentation and template design**, not rebuilding the collector by default.

The collector already retrieves a broad set of data through yt-dlp, including channel metadata, discovered channel tabs, tab entries, detailed metadata for videos when full.md is selected, and optional local thumbnails/subtitles/transcripts. The current output is difficult to read because templates/full.md mostly prints whole JSON objects. That is a presentation problem: reorganize the existing fields into human-readable sections and cards while preserving access to the complete source metadata.

## Non-negotiable distinctions

1. **Collection, archive, rendering are separate layers.** Do not rewrite the collection mechanism merely because the rendered Markdown looks bad.
2. **Preserve source data.** Do not throw away fields from yt-dlp JSON to make the page shorter. Prefer selecting and grouping key fields for the main view while keeping complete JSON available in a collapsible diagnostic/details section.
3. **Do not claim YouTube Data API v3 is used.** The project currently does not call googleapis.com/youtube/v3 endpoints. It uses yt-dlp and parses public channel HTML to discover navigation tabs. See the API comparison at docs/youtube-data-api-comparison.md.
4. **Do not treat the YouTube Data API schema as the schema of the current data.** Render fields that are actually present in yt-dlp metadata. If a field is missing, omit it or mark it unavailable; do not invent a value.
5. **No video-file downloads.** --skip-download is intentional. Optional media collection saves images and subtitle/transcript artifacts, not the video itself.
6. **Do not silently change collection scope.** No new API, dependencies, authentication flow, quota costs, or collection strategy unless a demonstrated collection gap makes that necessary and the change is explicitly evaluated.
7. **Finish the whole task.** Run relevant tests, inspect generated Markdown, check the published result if the change is merged/deployed, and do not report a pull request as completed work before verification.

## Current implementation

- scripts/process_channels.py is the collector, archive updater, and Jinja renderer.
- templates/outline.md, templates/archive.md, templates/index.md, and templates/full.md are Markdown/Jinja presentation templates.
- Channel URLs come from config/channels.txt.
- Per-channel raw responses and content-addressed history live under data/channels/<handle>/raw/.
- The accumulated entries live under data/channels/<handle>/archive/.
- data/channels/<handle>/status.json records the last check and errors.
- Rendered Markdown is written to data/output/<handle>/<template>.md.
- full.md triggers detailed per-video metadata collection. With --download-media, local images, Russian/English subtitle tracks where available, and plain-text transcripts are also saved.
- Channel tabs are discovered from public HTML; the current recognized set includes videos, Shorts, streams, podcasts, playlists, community, channels, and about.
- Archives retain previously discovered entries even if an entry is absent from the latest scan. Failed or malformed responses must not overwrite the last successful raw snapshot.

## Next task: make full.md readable

Start by inspecting the real keys in saved example JSON and the existing rendered output. Then redesign templates/full.md around human reading:

- a concise channel header with title, link, ID, last check, and available channel images;
- a useful overview/index of the discovered sections;
- each video/stream/podcast/playlist entry presented as a readable card or section;
- title and source link first, then date, duration, channel/series, description, and other useful fields only when present;
- clear display of local thumbnail, subtitles, transcript, and metadata-file links when available;
- related data grouped by purpose rather than an alphabetic/raw JSON dump;
- complete source JSON retained in a collapsible block for debugging and future template experiments;
- clear, compact error and stale-data warnings;
- valid Markdown/HTML that renders predictably on GitHub.

Use graceful fallbacks because fields differ across video types. Do not assume every entry is a standard video: streams, upcoming/live broadcasts, Shorts, podcasts, playlists, and unavailable/deleted entries can have different metadata.

## How to judge the template

The goal is not merely valid Jinja or a successful test. Inspect the rendered page and judge whether a person can quickly answer:

- What is this channel and what sections does it have?
- What is each item, and where does its link go?
- When was it published or scheduled, if known?
- What is its duration or current state, if known?
- Where are its description, thumbnail, subtitles, transcript, and complete metadata?
- Is this item missing data, or did the last collection attempt fail?

Keep the default view scannable. Put uncommon/technical fields and the full JSON behind <details> blocks instead of making every record a wall of text.

## Verification before calling the task complete

1. Run the repository's automated tests and snapshot validation.
2. Render templates against representative fixtures/examples, including missing optional fields and non-video entries.
3. Inspect the actual Markdown output for broken links, whitespace, malformed nested <details>, raw JSON clutter, and missing media paths.
4. Confirm the collection/archive behavior was not unintentionally changed.
5. Review the diff and CI result. After merge, verify the published main state.

## Project docs

- Current implementation and handoff: docs/current-state.md
- YouTube Data API v3 comparison: docs/youtube-data-api-comparison.md
- Data lifecycle: docs/data-lifecycle.md
- Collection method: docs/collection-method.md
- Tool evaluation: docs/tool-evaluation.md
