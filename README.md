# ytbd — YouTube data, with a working example

**Goal:** collect public YouTube channel metadata, validate it, and keep reproducible snapshots. The saved AsForJS data is a test fixture: you can run the project without querying YouTube.

## Use it now — no terminal required

1. Open the repository's [Actions tab](https://github.com/devAItester/ytbd/actions).
2. Select **Validate saved AsForJS snapshot**.
3. Click **Run workflow**, leave branch `main` selected, and click the green **Run workflow** button.
4. Open the new run at the top of the page. A green check means the saved JSON passed validation; open **Validate snapshot** to read the counts and checks.

This checks the data already stored in GitHub. It does **not** contact YouTube or claim that the snapshot is current.

## Run it locally

Install Python 3 if it is not already installed. From a terminal in the repository root, run:

```sh
python3 scripts/validate_snapshot.py
```

The validator reads `examples/AsForJS/`, checks the four saved tab JSON files and `tree-data.json`, then prints counts. It does not modify source files.

## What the example contains

- `examples/AsForJS/videos.json`, `streams.json`, `podcasts.json`, `playlists.json`: saved tab snapshots.
- `examples/AsForJS/tree-data.json`: expanded playlist data from the earlier collection.
- `examples/AsForJS/collect.py` and `collect.log`: original collector and log.
- `examples/AsForJS/items/`: per-playlist JSON snapshots and collection logs.
- `examples/AsForJS/full-data/DjuK8h7-ep8/`: detailed metadata and subtitle/format inventories for one video.
- `examples/AsForJS/channel-tree-full.md`: generated channel-tree view.

The counts in a saved snapshot are historical, not live channel totals. More source notes and method documentation are in [docs/collection-method.md](docs/collection-method.md), [docs/data-lifecycle.md](docs/data-lifecycle.md), and [docs/tool-evaluation.md](docs/tool-evaluation.md).

## Collect fresh data (not yet automated)

The original collection process is documented in [examples/AsForJS/get-source-data.md](examples/AsForJS/get-source-data.md) once imported. Fresh collection should be treated as a separate operation from validation: review the result before replacing a known-good snapshot. Do not commit cookies, browser profiles, tokens, or other secrets.

## Project principles

- Preserve source snapshots and the procedure used to obtain them.
- Keep raw data separate from generated output.
- Validate completeness before accepting a new snapshot.
- Use saved fixtures while developing; avoid unnecessary requests to YouTube.
- Never silently replace a valid snapshot with partial or invalid data.
