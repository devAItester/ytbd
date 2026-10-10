# Tool evaluation notes

## Goal

Keep a record of why a tool was tried, what it actually returned, and why it was accepted or rejected. This avoids repeating exploratory work and prevents a convenient one-time result from becoming an undocumented dependency.

## Current tool roles

| Tool | Intended role | Current status |
|---|---|---|
| curl | Probe HTTP reachability, inspect endpoints, capture raw responses | Used during discovery; a 200 status alone is insufficient |
| yt-dlp | Collect channel-tab metadata as JSON | Worked for the four AsForJS tabs in the historical snapshot |
| jq | Inspect JSON keys, counts, and selected fields | Used for command-line validation |
| Python | Repeatable validation and transformations | Existing collection code exists in the earlier aishare archive; migration/review still required |
| GitHub Actions | Unattended collection and refresh | Not configured yet |

## Evaluation checklist

For each new tool or method, record:

1. Problem being solved.
2. Exact command, URL, or API endpoint.
3. Tool version and environment.
4. Input and output examples, with secrets removed.
5. Available fields and structure.
6. Count/order comparison with the current baseline.
7. Failure modes and limits observed.
8. Whether it can run unattended.
9. Decision: use, keep as fallback, investigate later, or reject.
10. Date and links to relevant source documentation.

## Candidate methods

- **yt-dlp** — current baseline for tab collection.
- **Direct HTTP/HTML inspection with curl** — useful for discovery and debugging; avoid relying on undocumented page markup as the main database interface unless there is a clear reason.
- **Invidious API** — was probed as an alternative during initial exploration. Public instances are third-party and can be unavailable or rate-limited; do not treat a particular public instance as a stable service dependency.
- **Other methods** — may be added when a concrete requirement appears. Do not add dependencies merely because they exist.

## Decision record

### Initial AsForJS collection

- **Decision:** use yt-dlp to collect JSON from the four channel tabs.
- **Reason:** it successfully returned structured metadata for the required sections without downloading the video files.
- **Baseline counts:** videos 6, streams 253, podcasts 21, playlists 24.
- **Limit:** counts describe the previously saved snapshot, not the current channel state.
- **Next verification:** import the saved files, preserve them unchanged, then compare any new collector against the same source snapshot and completeness requirements.
