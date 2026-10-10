"""Independent downloading of video thumbnails from archive URLs."""
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

def download_video_thumbnail(video_id: str, item: dict, output_dir: Path) -> tuple[str | None, str | None]:
    """Save the highest-resolution thumbnail without fetching full video metadata."""
    thumbnails = item.get("thumbnails", [])
    if not isinstance(thumbnails, list):
        return None, None
    candidates = [x for x in thumbnails if isinstance(x, dict) and isinstance(x.get("url"), str) and x["url"].startswith(("https://", "http://"))]
    if not candidates:
        return None, None
    def score(item: dict) -> int:
        try:
            return int(item.get("width") or 0) * int(item.get("height") or 0)
        except (TypeError, ValueError):
            return 0
    selected = max(candidates, key=score)
    extension = Path(urlsplit(selected["url"]).path).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".jpg"
    relative = Path("media") / "thumbnails" / (video_id + extension)
    destination = output_dir / relative
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not (destination.is_file() and destination.stat().st_size):
            request = Request(selected["url"], headers={"User-Agent": "Mozilla/5.0 (compatible; ytbd media downloader)"})
            with urlopen(request, timeout=20) as response:
                payload = response.read()
            if not payload:
                raise OSError("empty image response")
            destination.write_bytes(payload)
    except (OSError, ValueError) as exc:
        return None, str(exc)
    return relative.as_posix(), None
