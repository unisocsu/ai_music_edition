#!/usr/bin/env python3
"""Submit a complete song-generation task to the local ACE-Step API."""
from __future__ import annotations

import json
import os
import time
import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_URL = "http://127.0.0.1:8001"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    audio_url = os.environ.get("AUDIO_URL", "").strip()
    lyrics = os.environ.get("LYRICS", "").strip()
    style = os.environ.get("STYLE", "pop arrangement").strip()
    duration = int(os.environ.get("DURATION", "30"))
    model = os.environ.get("MODEL_NAME", "acestep-v15-turbo")

    if duration not in (15, 30, 45, 60):
        raise ValueError("Duration must be 15, 30, 45, or 60 seconds.")
    if audio_url and urlparse(audio_url).scheme != "https":
        raise ValueError("A melody URL must start with https://")

    (out / "lyrics.txt").write_text(lyrics, encoding="utf-8")
    metadata = {
        "engine": "ACE-Step 1.5",
        "mode": "cover" if audio_url else "text2music",
        "model": model,
        "duration_seconds": duration,
        "style": style,
        "lyrics_language": "he",
        "input_audio_url_supplied": bool(audio_url),
        "notice": (
            "Audio generation is model-dependent. Hebrew pronunciation and exact melody preservation "
            "are not guaranteed. CPU inference may take a long time."
        ),
    }
    (out / "request.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    files = None
    input_path = None
    try:
        payload = {
            "prompt": style,
            "lyrics": lyrics or "[Instrumental]",
            "vocal_language": "he",
            "audio_format": "wav",
            "audio_duration": str(duration),
            "model": model,
            "task_type": "cover" if audio_url else "text2music",
            "thinking": "false",
            "inference_steps": "8",
            "guidance_scale": "1.0",
            "batch_size": "1",
            "use_random_seed": "true",
            "audio_cover_strength": "0.85",
        }

        if audio_url:
            input_path = out / "source_melody"
            with requests.get(audio_url, stream=True, timeout=(30, 180), allow_redirects=True) as response:
                response.raise_for_status()
                final_url = response.url
                if urlparse(final_url).scheme != "https":
                    raise ValueError("Audio download redirected away from HTTPS; refusing it.")
                content_type = response.headers.get("content-type", "").lower()
                total = 0
                with input_path.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            total += len(chunk)
                            if total > 100 * 1024 * 1024:
                                raise ValueError("Input audio exceeds 100 MB.")
                            f.write(chunk)
            if total == 0:
                raise ValueError("Downloaded audio file is empty.")
            # ACE-Step decodes audio content; an extension is not required by the API.
            files = {"src_audio": (input_path.name, input_path.open("rb"), content_type or "application/octet-stream")}

        print("Submitting generation task to ACE-Step API...", flush=True)
        response = requests.post(
            f"{BASE_URL}/release_task",
            data=payload,
            files=files,
            timeout=180,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(f"API rejected generation task: {body['error']}")
        data = body.get("data") or {}
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError(f"API did not return a task_id: {body}")
        (out / "task.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

        deadline = time.time() + 5 * 60 * 60
        while time.time() < deadline:
            result_response = requests.post(
                f"{BASE_URL}/query_result",
                json={"task_id_list": [task_id]},
                timeout=60,
            )
            result_response.raise_for_status()
            result_body = result_response.json()
            items = result_body.get("data") or []
            if items:
                item = items[0]
                status = item.get("status")
                print(f"Generation status: {status}", flush=True)
                if status == 2:
                    raise RuntimeError(f"ACE-Step generation failed: {item.get('result', item)}")
                if status == 1:
                    raw_result = item.get("result", "[]")
                    try:
                        result_items = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                    except json.JSONDecodeError:
                        result_items = []
                    if not result_items:
                        raise RuntimeError(f"Generation completed but no audio file was listed: {item}")
                    generated = next((x for x in result_items if x.get("file")), None)
                    if not generated:
                        raise RuntimeError(f"No downloadable audio path in result: {result_items}")
                    audio_path = generated["file"]
                    download_url = urljoin(BASE_URL + "/", audio_path.lstrip("/"))
                    audio_response = requests.get(download_url, timeout=(30, 300))
                    audio_response.raise_for_status()
                    target = out / "generated_song.wav"
                    target.write_bytes(audio_response.content)
                    if not target.stat().st_size:
                        raise RuntimeError("The API returned an empty audio file.")
                    (out / "generation_result.json").write_text(
                        json.dumps({"task": item, "audio_url": download_url, "audio_file": target.name},
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(f"Saved {target} ({target.stat().st_size} bytes)", flush=True)
                    return 0
            time.sleep(20)

        raise TimeoutError("Generation did not finish within 5 hours.")
    except Exception as exc:
        (out / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise
    finally:
        if files:
            files["src_audio"][1].close()
        if input_path and input_path.exists():
            input_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
