"""Render the examples in ``examples/`` into the videos and GIFs beside them.

    uv run python tools/examples.py          # every example
    uv run python tools/examples.py polar    # the examples whose name contains "polar"

Each ``examples/NN_name.py`` holds one Scene. Manim renders it at 720p30 into a scratch
media directory that git ignores; the video is copied to ``examples/NN_name.mp4`` and
ffmpeg, which must be on ``PATH``, makes ``examples/NN_name.gif`` for the README.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXAMPLES = ROOT / "examples"
MEDIA = ROOT / "tests" / "visual" / "_out" / "examples"
# 480 pixels wide at 12 frames per second, one palette per frame region that changes.
GIF = (
    "fps=12,scale=480:-1:flags=lanczos,split[a][b];"
    "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5"
    ":diff_mode=rectangle"
)


def render(script: Path) -> None:
    """Render one example and write its video and GIF next to it."""
    subprocess.run(
        [sys.executable, "-m", "manim", "render", "-qm", "--disable_caching",
         "--progress_bar", "none", "--verbosity", "WARNING", "--media_dir", str(MEDIA),
         "-o", script.stem, str(script)],
        check=True,
    )  # fmt: skip
    video = next(MEDIA.glob(f"videos/{script.stem}/*/{script.stem}.mp4"))
    shutil.copyfile(video, script.with_suffix(".mp4"))
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf", GIF,
         str(script.with_suffix(".gif"))],
        check=True,
    )  # fmt: skip


def main() -> int:
    """Render the examples named on the command line, or all, and report failures."""
    wanted = sys.argv[1:]
    failed = []
    for script in sorted(EXAMPLES.glob("[0-9][0-9]_*.py")):
        if wanted and not any(w in script.stem for w in wanted):
            continue
        try:
            render(script)
            print(script.with_suffix(".gif").relative_to(ROOT), flush=True)
        except (subprocess.CalledProcessError, StopIteration) as error:
            failed.append(script.stem)
            print(f"{script.stem} FAILED: {error!r}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
