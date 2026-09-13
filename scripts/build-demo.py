"""Assemble a <=3-minute MP4 from authentic, explicitly supplied browser screenshots.

No screenshots are generated, retouched, or captured by this script. FFmpeg only
scales/pads the provided frames and adds captions in a separate footer. Captions
must be reviewed against the actual screenshots before publishing the video.

Optional dependency: python -m pip install imageio-ffmpeg==0.6.0

Example:
  python scripts/build-demo.py --screenshots .runtime/screenshots \
    --manifest docs/demo-scenes.json --output .runtime/demo/ScopeProof-demo.mp4

Without a manifest, all supported screenshots are used in filename order, with a
neutral caption. --check validates the inputs without rendering a video.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp"}
WIDTH, HEIGHT, SCREEN_HEIGHT, FPS = 1080, 1280, 1120, 24


def ffmpeg_executable() -> str:
    explicit = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if explicit and Path(explicit).is_file():
        return str(Path(explicit).resolve())
    if installed := shutil.which("ffmpeg"):
        return installed
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise ValueError("FFmpeg is unavailable. Run: python -m pip install imageio-ffmpeg==0.6.0") from exc


def font_file(override: Path | None) -> Path:
    candidates = [override] if override else [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise ValueError("No usable TrueType font found. Supply --font /absolute/path/font.ttf.")


def load_scenes(directory: Path, manifest: Path | None, default_duration: float) -> list[dict]:
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("--screenshots must be a directory of actual captured screenshots.")
    if manifest:
        raw = json.loads(manifest.read_text(encoding="utf-8-sig"))
        scenes = raw["scenes"] if isinstance(raw, dict) else raw
    else:
        scenes = [{"file": image.name, "title": "ScopeProof", "caption": "Authentic browser screenshot. Review the application state shown above.", "seconds": default_duration}
                  for image in sorted(directory.iterdir()) if image.suffix.lower() in SUPPORTED and image.is_file()]
    if not isinstance(scenes, list) or not scenes or len(scenes) > 30:
        raise ValueError("Provide between 1 and 30 screenshot scenes.")
    resolved = []
    for number, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or not isinstance(scene.get("file"), str):
            raise ValueError(f"Scene {number} requires a screenshot filename.")
        image = (directory / scene["file"]).resolve(strict=True)
        if not image.is_relative_to(directory) or not image.is_file() or image.suffix.lower() not in SUPPORTED:
            raise ValueError(f"Scene {number} must reference a PNG/JPEG/WebP inside the screenshot directory.")
        duration = float(scene.get("seconds", default_duration))
        if not math.isfinite(duration) or not 1 <= duration <= 45:
            raise ValueError(f"Scene {number} duration must be between 1 and 45 seconds.")
        title, caption = scene.get("title", "ScopeProof"), scene.get("caption", "Authentic browser screenshot.")
        if not isinstance(title, str) or not isinstance(caption, str):
            raise ValueError(f"Scene {number} title and caption must be text.")
        title = " ".join(title.split())
        caption = " ".join(caption.split())
        if not title or len(title) > 72 or not caption or len(caption) > 190:
            raise ValueError(f"Scene {number}: use a title of 1-72 characters and a caption of 1-190 characters.")
        wrapped = textwrap.wrap(caption, width=84, break_long_words=True)
        if len(wrapped) > 3:
            raise ValueError(f"Scene {number}: shorten the caption to fit the footer.")
        resolved.append({"file": image, "relative_file": str(image.relative_to(directory)), "title": title,
                         "caption": caption, "wrapped_caption": "\n".join(wrapped), "seconds": duration,
                         "sha256": hashlib.sha256(image.read_bytes()).hexdigest()})
    total = sum(scene["seconds"] for scene in resolved)
    if total > 180:
        raise ValueError(f"Scene durations total {total:.1f}s; the maximum is 180 seconds.")
    return resolved


def invoke(command: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise ValueError("FFmpeg failed; no substitute scene was created:\n" + result.stderr[-4000:])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/demo/ScopeProof-demo.mp4")
    parser.add_argument("--seconds", type=float, default=12.0, help="Default time per screenshot without a scene duration.")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validate actual screenshot inputs and print the scene plan; do not render.")
    args = parser.parse_args()
    try:
        scenes = load_scenes(args.screenshots, args.manifest, args.seconds)
        total = sum(scene["seconds"] for scene in scenes)
        ffmpeg = ffmpeg_executable()
        font = font_file(args.font)
        output = args.output.resolve()
        if output.suffix.lower() != ".mp4":
            raise ValueError("The output must use the .mp4 extension.")
        if output.exists() and not args.overwrite and not args.check:
            raise ValueError("Output already exists. Review it first or explicitly pass --overwrite.")
        plan = {"status": "validated", "duration_seconds": total, "scene_count": len(scenes), "output": str(output),
                "scenes": [{k: str(v) if isinstance(v, Path) else v for k, v in scene.items()} for scene in scenes]}
        if args.check:
            print(json.dumps(plan, indent=2))
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="scopeproof-video-", dir=output.parent) as working:
            temp = Path(working)
            shutil.copyfile(font, temp / "font.ttf")
            clips = []
            for index, scene in enumerate(scenes, 1):
                (temp / "title.txt").write_text(scene["title"], encoding="utf-8")
                (temp / "caption.txt").write_text(scene["wrapped_caption"], encoding="utf-8")
                (temp / "count.txt").write_text(f"{index:02d} / {len(scenes):02d}", encoding="utf-8")
                # Captions are drawn only in the reserved footer; screenshot pixels are not retouched.
                filters = (f"scale={WIDTH}:{SCREEN_HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
                           f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:0:color=0x091321,setsar=1,"
                           f"drawtext=fontfile=font.ttf:textfile=title.txt:expansion=none:fontcolor=0x8AE6D2:fontsize=26:x=28:y={SCREEN_HEIGHT + 14},"
                           f"drawtext=fontfile=font.ttf:textfile=caption.txt:expansion=none:fontcolor=white:fontsize=21:line_spacing=5:x=28:y={SCREEN_HEIGHT + 58},"
                           f"drawtext=fontfile=font.ttf:textfile=count.txt:expansion=none:fontcolor=0x8FA8BA:fontsize=18:x=w-tw-26:y={SCREEN_HEIGHT + 21}")
                clip = f"scene-{index:02d}.mp4"
                invoke([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS),
                        "-i", str(scene["file"]), "-t", str(scene["seconds"]), "-vf", filters,
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-r", str(FPS), "-threads", "2", clip], temp)
                clips.append(clip)
                print(f"Encoded scene {index}/{len(scenes)} from {scene['relative_file']}", flush=True)
            (temp / "scenes.txt").write_text("".join(f"file '{clip}'\n" for clip in clips), encoding="utf-8")
            assembled = temp / "assembled.mp4"
            invoke([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "1", "-i", "scenes.txt",
                    "-c", "copy", "-movflags", "+faststart", "-t", "180", str(assembled)], temp)
            # Decode the completed video, catching corrupted inputs/outputs before delivery.
            invoke([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(assembled), "-f", "null", "-"], temp)
            shutil.copyfile(assembled, output)
        receipt = {"created_at": datetime.now(timezone.utc).isoformat(), "status": "rendered_and_decode_verified",
                   "duration_seconds": total, "scene_count": len(scenes), "size_bytes": output.stat().st_size,
                   "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                   "note": "Captioned screenshot walkthrough, not a real-time screen recording. Only supplied screenshots were used; no UI states were fabricated.",
                   "scenes": [{"file": scene["relative_file"], "source_sha256": scene["sha256"], "seconds": scene["seconds"],
                               "title": scene["title"], "caption": scene["caption"]} for scene in scenes]}
        receipt_path = output.with_suffix(".sources.json")
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(output), "receipt": str(receipt_path), "duration_seconds": total, "size_bytes": output.stat().st_size}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"Demo not built: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
