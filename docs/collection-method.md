# AsForJS: discovery and collection method

## Purpose

This document preserves the reproducible procedure used to determine which channel sections existed and how to collect their metadata. It records the reasoning as well as the commands: the method is part of the project, not disposable setup history.

Source channel: https://www.youtube.com/@AsForJS

## 1. Discovery before collection

The task was to preserve channel structure and metadata—titles, IDs, URLs, ordering, and playlist contents—not to download video files.

The discovery sequence used lightweight HTTP checks and source inspection before choosing a collector:

1. Check whether the YouTube channel URL responds.
2. Probe possible alternative frontends/API endpoints as experiments, not as guaranteed dependencies.
3. Inspect the channel's actual tabs/sections.
4. Test whether the selected tool can return machine-readable JSON for each tab.
5. Inspect JSON keys, nested entries, IDs, URLs, titles, ordering, and counts.
6. Save raw output and diagnostics before doing transformations.

### HTTP reachability probe

A simple curl probe can show whether an endpoint responds, but HTTP 200 does **not** establish that it returned the expected channel data or a complete response.

Example for a single endpoint:

~~~bash
curl -L --silent --show-error \
  --output /dev/null \
  --write-out 'HTTP %{http_code}\nURL %{url_effective}\n' \
  'https://www.youtube.com/@AsForJS'
~~~

For alternative frontends or APIs, probe each candidate separately and inspect the body and response headers before relying on it. Public Invidious instances can disappear, rate-limit requests, or change behavior; they are discovery leads, not a stable project dependency.

An example API discovery request that was tested during the earlier investigation was:

~~~bash
curl -L --silent --show-error \
  'https://invidious.nerdvpn.de/api/v1/search?q=AsForJS&type=channel'
~~~

A candidate channel ID from a search response can then be inspected with that instance's channel endpoint, for example /api/v1/channels/CHANNEL_ID. Replace the placeholder only with an ID actually returned by the search response. Do not assume the instance or endpoint remains available.

**Interpretation rule:** keep the probe result, timestamp, URL, status, and any relevant error in the investigation notes. Do not treat a successful HTTP status as proof that an alternative is suitable.

## 2. Why yt-dlp was selected for the initial collection

For the first working example, yt-dlp successfully returned JSON for the four channel tabs:

- videos
- streams
- podcasts
- playlists

This was a better fit than scraping page HTML by hand for the initial data set because it directly produced structured metadata and did not require downloading the videos themselves.

The choice is pragmatic, not a claim that yt-dlp is the only possible method. Alternatives can be tested later against the same requirements and saved sample data.

## 3. Reproduce the four-tab collection

Requirements: yt-dlp, a working connection to YouTube, and a Bash-compatible shell.

Run the block from a new working directory. It writes one JSON file and one diagnostic log for each tab.

~~~bash
mkdir -p AsForJS-source
cd AsForJS-source

for tab in videos streams podcasts playlists; do
  printf '\n=== Collecting %s ===\n' "$tab"
  yt-dlp \
    --ignore-errors \
    --flat-playlist \
    --dump-single-json \
    "https://www.youtube.com/@AsForJS/$tab" \
    > "$tab.json" \
    2> "$tab.log"
  printf 'exit status: %s\n' "$?"
done
~~~

Options:

- --ignore-errors allows processing to continue through some item-level errors; it does not mean the result is complete.
- --flat-playlist requests a flat listing rather than fully processing each video.
- --dump-single-json writes one JSON object for the requested listing.
- Standard output is saved to the JSON file.
- Standard error is saved to the matching log.

The loop's exit status is printed for each tab, but it is not the only validation criterion. Inspect the JSON and logs as described below.

## 4. Validate the raw outputs

If jq is installed:

~~~bash
for tab in videos streams podcasts playlists; do
  printf '\n=== %s ===\n' "$tab"
  test -s "$tab.json" || { echo "MISSING OR EMPTY JSON"; continue; }
  jq -e '.entries | length' "$tab.json"
  printf '%s\n' '--- log ---'
  if test -s "$tab.log"; then
    sed -n '1,120p' "$tab.log"
  else
    echo 'No log output'
  fi
done
~~~

Do not proceed as though collection succeeded if a file is absent, empty, invalid JSON, or structurally different from expectations. A non-empty log needs interpretation; it does not automatically mean every entry failed. An empty log does not prove completeness.

For deeper inspection:

~~~bash
jq 'keys' videos.json
jq '{title, id, webpage_url, extractor, count: (.entries | length)}' videos.json
jq '.entries[0] | {id, title, url, webpage_url, ie_key}' videos.json
~~~

The exact fields vary by extractor response. Inspect the actual data rather than assuming every field exists.

## 5. Historical snapshot counts

The previously saved AsForJS snapshot contained:

| Tab | Entries |
|---|---:|
| videos | 6 |
| streams | 253 |
| podcasts | 21 |
| playlists | 24 |

These counts are useful as a comparison baseline for the imported snapshot, not as permanent expected counts. YouTube content changes, and inaccessible/private/deleted items may be absent.

## 6. Collection versus transformation

The four tab JSON files are source inputs. They should be retained as collected, with their corresponding logs. Later stages may combine metadata, fetch playlist contents, validate relationships, or generate Markdown—but those are derived artifacts and must not overwrite the original inputs.

During development, use the saved JSON as fixtures. Query YouTube again only when testing the online collection itself or refreshing the source snapshot.

## 7. What to record when evaluating another method

For each alternative, note:

- date and environment;
- exact endpoint or command;
- tool and version;
- whether the response was machine-readable;
- which required fields were available;
- ordering and item counts;
- rate limits, access errors, missing items, or instability;
- whether the method can be repeated without credentials or manual browser steps;
- whether it is suitable for unattended GitHub Actions runs.

Do not replace the current method until an alternative has been tested against the same saved input and completeness criteria.
