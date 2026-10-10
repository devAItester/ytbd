# Data lifecycle and repository structure

## Core rule

**Raw source data is immutable evidence; normalized JSON and Markdown are derived outputs.** A transformation must be reproducible from saved inputs, and a failed refresh must not silently replace the last valid snapshot.

## Proposed structure

~~~text
ytbd/
├── .github/
│   └── workflows/          # Added after local/test steps are defined
├── data/
│   └── AsForJS/
│       ├── raw/             # Original tab JSON and matching logs
│       ├── derived/         # Combined JSON and generated Markdown
│       └── manifests/       # Collection time, tool version, counts, status
├── docs/
│   ├── collection-method.md
│   ├── data-lifecycle.md
│   └── tool-evaluation.md
├── tests/                   # Deterministic checks using saved files
├── src/                     # Collection and transformation code
└── README.md
~~~

This is the intended layout, not a claim that these directories or scripts already exist. Import the previously collected files before building transformations around them; preserve their names and contents during the initial import.

## Lifecycle

1. **Discover** — identify available channel sections and evaluate candidate methods.
2. **Collect** — save the original response for each section and separate logs.
3. **Record provenance** — record timestamp, yt-dlp version, command/options, and exit status.
4. **Validate** — check JSON syntax, expected top-level structure, entry counts, IDs/URLs, and diagnostics.
5. **Accept snapshot** — only mark the collection usable after required checks pass.
6. **Transform** — create combined JSON, playlist contents, and Markdown from the accepted raw snapshot.
7. **Compare** — compare counts, IDs, ordering, and errors with the previous accepted snapshot.
8. **Publish** — commit the new snapshot and derived output only after validation.

## Required safeguards

- Never use --ignore-errors as a substitute for validation.
- Do not interpret a missing or invalid JSON file as an empty channel.
- Preserve logs alongside the files they explain.
- Keep old valid data when a refresh fails validation.
- Record partial success explicitly; do not present a partial snapshot as complete.
- Preserve source ordering and repeated videos that legitimately appear in multiple playlists.
- Do not remove or normalize source fields without recording that transformation.
- Use deterministic tests against saved fixtures; tests should not require network access.
- During the initial import, do not regenerate or rewrite the historical outputs.

## Initial import checklist

- [ ] Import all four tab JSON files.
- [ ] Import their four matching logs.
- [ ] Import existing combined JSON, Markdown outputs, and collection script as historical artifacts where available.
- [ ] Preserve the original folder/file names in an import note or manifest.
- [ ] Compare file sizes, JSON validity, entry counts, and hashes where possible.
- [ ] Confirm the imported files are visible on GitHub by fetching them back.
- [ ] Only then decide how to reorganize or regenerate them.
