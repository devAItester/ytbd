# ytbd — YouTube content database

**ytbd** is a private, reproducible workspace for collecting and organizing YouTube channel metadata. The durable value is not only the resulting data: it is also the documented process used to discover channel sections, evaluate tools, collect raw responses, validate results, and regenerate derived views.

The first working example is the channel [AsForJS](https://www.youtube.com/@AsForJS).

## Principles

- Preserve the **method**, not only the final database.
- Keep raw source data separate from derived JSON and Markdown.
- Record commands, tool versions, logs, observations, and failures so a collection can be repeated and audited.
- Inspect the actual source structure before choosing a collection method.
- Validate data completeness; a successful command alone is not proof that the result is complete.
- Do not silently replace a known-good snapshot with partial or invalid data.
- Do not download video files when metadata and links are sufficient.
- Keep credentials, cookies, tokens, and other secrets out of Git.

## Current status

The repository is being initialized. The initial documentation records the method used to discover and collect AsForJS channel sections. Existing downloaded data from the earlier [aishare](https://github.com/devAItester/aishare) work is intended to be imported as a separate step, before further transformations.

## Start here

1. [Collection method and discovery notes](docs/collection-method.md) — how channel sections were identified, why yt-dlp was selected, and how to repeat the collection.
2. [Project structure and data lifecycle](docs/data-lifecycle.md) — how raw inputs, logs, validated snapshots, and derived outputs should relate.
3. [Tool evaluation notes](docs/tool-evaluation.md) — how to assess curl, yt-dlp, YouTube endpoints, and possible alternatives without prematurely committing to one.

## Initial AsForJS collection

The channel tabs tested successfully with yt-dlp were:

- **videos** — 6 entries in the saved snapshot
- **streams** — 253 entries
- **podcasts** — 21 entries
- **playlists** — 24 entries

These are historical snapshot counts, not live counts or a guarantee of completeness today. The original JSON and corresponding logs should be imported unchanged before regenerating or normalizing anything.

## Planned workflow

1. Preserve the discovery procedure and the tool-selection rationale.
2. Import the previously collected source JSON and logs.
3. Verify imported files and their provenance.
4. Build repeatable validation and transformation steps using the saved data, without repeatedly querying YouTube during development.
5. Add a manually triggered GitHub Actions workflow.
6. Run a full online collection only when needed; retain the previous valid snapshot if validation fails.
7. Enable daily scheduling only after the manual workflow has been tested end to end.

## Repository policy

This repository is private for convenience and control, not because its intended contents are secret. Still, treat credentials and browser/session data as secrets and never commit them. Respect YouTube availability and access restrictions; collection may fail or omit unavailable/private content.
