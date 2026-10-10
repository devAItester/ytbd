#!/usr/bin/env python3
"""Live end-to-end checks for every Markdown template using a public YouTube channel."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_URL = "https://www.youtube.com/@RTFMurych"
TEMPLATES = ("outline.md", "archive.md", "index.md", "full.md")


def copy_evidence(temp: Path, artifacts: Path | None, template_name: str) -> None:
    if artifacts is None:
        return
    destination = artifacts / Path(template_name).stem
    destination.mkdir(parents=True, exist_ok=True)
    for name, target in (
        ("output/RTFMurych", destination / "output"),
        ("data/RTFMurych/status.json", destination / "status.json"),
        ("data/RTFMurych/tabs.json", destination / "tabs.json"),
        ("data/RTFMurych/archive", destination / "archive"),
        ("data/RTFMurych/raw/video-details", destination / "raw/video-details"),
    ):
        source = temp / name
        if source.is_dir():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target, dirs_exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def check_output(template_name: str, output: str, tabs: list[dict]) -> list[str]:
    failures = []
    if not tabs:
        failures.append("не обнаружено ни одной вкладки")
    for tab in tabs:
        key = tab["key"]
        title = tab["title"]
        if template_name == "outline.md":
            marker = f"<summary>{title} —"
        elif template_name == "full.md":
            marker = f"## {title} —"
        else:
            marker = f"## {title}"
        if marker not in output:
            failures.append(f"в Markdown отсутствует обнаруженная вкладка {key!r}")

    if re.search(r"- \*\*ID:\*\* [^\n]*- \*\*Последняя проверка:", output):
        failures.append("ID канала склеен с датой проверки")
    if "</a>- <a" in output:
        failures.append("соседние пункты списка склеены")
    if any(line.strip() != "</details>" for line in output.splitlines() if "</details>" in line):
        failures.append("закрывающий тег details приклеен к содержимому карточки")
    if template_name == "full.md":
        if "Метаданные канала" not in output:
            failures.append("в полном представлении отсутствуют метаданные канала")
        if '"_type"' not in output and '"id"' not in output:
            failures.append("в полном представлении не обнаружены поля JSON-метаданных")
        if "Локальные файлы" not in output:
            failures.append("в полном представлении отсутствует раздел о локальных файлах")
    if template_name == "outline.md" and "<details>" not in output:
        failures.append("в обзоре отсутствуют раскрывающиеся разделы")
    if template_name == "archive.md" and "<details>" not in output:
        failures.append("в архиве отсутствуют карточки записей")
    if template_name == "index.md":
        if "<details>" in output:
            failures.append("в индексе неожиданно появились раскрывающиеся карточки")
        lines = output.splitlines()
        if any(
            line.startswith("## ") and index > 0 and lines[index - 1].startswith("- ")
            for index, line in enumerate(lines)
        ):
            failures.append("заголовок раздела индекса не отделён пустой строкой от предыдущего списка")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, help="Optional directory for preserving rendered Markdown and test evidence")
    args = parser.parse_args()
    if args.artifacts:
        args.artifacts.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ytbd-live-smoke-") as temporary:
        root = Path(temporary)
        input_path = root / "channels.txt"
        input_path.write_text(CHANNEL_URL + "\n", encoding="utf-8")

        for template_name in TEMPLATES:
            template_root = root / Path(template_name).stem
            data_root = template_root / "data"
            output_root = template_root / "output"
            command = [
                sys.executable,
                str(ROOT / "scripts/process_channels.py"),
                "--input", str(input_path),
                "--template", template_name,
                "--data", str(data_root),
                "--output", str(output_root),
            ]
            if template_name == "full.md":
                command.extend(["--detail-limit", "3", "--download-media"])
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, check=False
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")

            copy_evidence(template_root, args.artifacts, template_name)
            if result.returncode:
                failures.append(f"{template_name}: сборщик завершился с кодом {result.returncode}")
                continue

            channel_dir = data_root / "RTFMurych"
            try:
                status = json.loads((channel_dir / "status.json").read_text(encoding="utf-8"))
                tabs = json.loads((channel_dir / "tabs.json").read_text(encoding="utf-8"))
                output_path = output_root / "RTFMurych" / template_name
                output = output_path.read_text(encoding="utf-8")
            except (OSError, json.JSONDecodeError) as exc:
                failures.append(f"{template_name}: не удалось прочитать результат: {exc}")
                continue

            if status.get("errors"):
                failures.append(f"{template_name}: ошибки сбора: {status['errors']!r}")
            for tab in tabs:
                if status.get("tabs", {}).get(tab["key"], {}).get("status") != "ok":
                    failures.append(f"{template_name}: вкладка не собрана успешно: {tab['key']}")
            failures.extend(
                f"{template_name}: {message}"
                for message in check_output(template_name, output, tabs)
            )
            if template_name == "full.md":
                detail_dir = data_root / "RTFMurych" / "raw" / "video-details"
                detailed = list(detail_dir.glob("*.json")) if detail_dir.is_dir() else []
                if not detailed:
                    failures.append("full.md: подробный JSON ни одного видео не сохранён")
                if "--detail-limit" not in command or "Локальные файлы" not in output:
                    failures.append("full.md: параметры подробного сбора или раздел локальных файлов отсутствуют")
                if not (output_root / "RTFMurych" / "media" / "videos").is_dir():
                    failures.append("full.md: каталог локальных материалов не создан")
            print(
                f"Проверен {template_name}: вкладки "
                f"{[tab['key'] for tab in tabs]}; "
                f"Markdown: {output_path}"
            )

    if failures:
        print("\nПроверка не пройдена:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("УСПЕХ: все четыре шаблона прошли live-сбор; full.md дополнительно проверил подробные метаданные трёх видео и локальные материалы.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
