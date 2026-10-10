import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

root = Path(".")
tabs = {}

for name in ("videos", "streams", "podcasts", "playlists"):
    with (root / f"{name}.json").open() as f:
        tabs[name] = json.load(f)

# Объединяем плейлисты и подкасты, убирая дубликаты.
playlists = {}
for source in ("podcasts", "playlists"):
    for item in tabs[source].get("entries", []):
        if item.get("id") and item.get("url"):
            playlists[item["id"]] = {
                "id": item["id"],
                "title": item.get("title", ""),
                "url": item["url"],
                "source": source,
            }

def fetch(item):
    cmd = [
        "yt-dlp",
        "--ignore-errors",
        "--flat-playlist",
        "--dump-single-json",
        "--socket-timeout", "15",
        "--retries", "1",
        "--extractor-retries", "1",
        item["url"],
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            return item["id"], data, None
        return item["id"], None, result.stderr[-1000:]
    except Exception as e:
        return item["id"], None, str(e)

expanded = {}
errors = {}

print(f"Получаю содержимое {len(playlists)} списков; параллельно: 4")

with ThreadPoolExecutor(max_workers=4) as pool:
    jobs = [pool.submit(fetch, item) for item in playlists.values()]
    for n, job in enumerate(as_completed(jobs), 1):
        pid, data, error = job.result()
        if data:
            expanded[pid] = data
        else:
            errors[pid] = error
        print(f"\rГотово: {n}/{len(jobs)}", end="", flush=True)

print()

output = {
    "channel": "AsForJS",
    "tabs": tabs,
    "playlist_metadata": list(playlists.values()),
    "playlist_contents": expanded,
    "errors": errors,
}

with (root / "tree-data.json").open("w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Списков успешно получено: {len(expanded)}")
print(f"Ошибок: {len(errors)}")
print("Итоговый файл: tree-data.json")
