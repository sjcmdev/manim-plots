"""The release's files and the built package (rows RL-1 to RL-3 of
`docs/acceptance/14-docs-release.md`).

RL-3 builds the sdist and the wheel and installs the wheel into a fresh environment
outside the repository: slow and networked, so it carries the `release` marker and runs
with `uv run python tools/check.py --release`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
UV = os.environ.get("UV", "uv")
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_rl1_the_changelog_has_an_unreleased_section_with_the_matrix():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Keep a Changelog" in text
    assert re.search(r"^## \[Unreleased\]", text, re.MULTILINE)
    for version in ("0.21.0", "0.22.0", "3.12"):
        assert version in text, version


def test_rl2_the_readme_links_are_absolute():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)\s]+)\)", text)
    assert targets
    relative = [t for t in targets if not re.match(r"(https?://|mailto:|#)", t)]
    assert not relative, relative


def test_rl2_the_project_urls():
    urls = PYPROJECT["project"]["urls"]
    assert urls["Repository"] == "https://github.com/sjcmdev/manim-plots"
    assert urls["Issues"] == "https://github.com/sjcmdev/manim-plots/issues"
    assert urls["Documentation"].startswith("https://github.com/sjcmdev/manim-plots")


def test_rl4_the_version_is_still_a_development_one():
    assert PYPROJECT["project"]["version"].endswith(".dev0")


def run(*cmd: str, cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, (cmd, result.stdout[-2000:], result.stderr[-2000:])
    return result.stdout


SMOKE = """
import numpy as np
from manim import Scene, tempconfig
import manim_plots as mp

class First(Scene):
    def construct(self):
        ax = mp.Axes()
        self.add(ax, ax.plot(np.sin))

with tempconfig({"dry_run": True, "disable_caching": True, "media_dir": "media"}):
    First().render()
print(mp.__version__)
"""


@pytest.mark.release
def test_rl3_the_built_wheel_installs_and_draws_outside_the_repository():
    with tempfile.TemporaryDirectory(prefix="manim-plots-release-") as tmp:
        out = Path(tmp)
        run(UV, "build", "--out-dir", str(out / "dist"), cwd=ROOT)
        (wheel,) = (out / "dist").glob("*.whl")
        (sdist,) = (out / "dist").glob("*.tar.gz")
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
        assert any(n.endswith("LICENSE") for n in names), names
        assert "manim_plots/py.typed" in names
        with tarfile.open(sdist) as archive:
            members = archive.getnames()
        assert any(n.endswith("/LICENSE") for n in members)
        assert any(n.endswith("manim_plots/py.typed") for n in members)
        venv = out / "venv"
        major, minor = sys.version_info[:2]
        run(UV, "venv", str(venv), "--python", f"{major}.{minor}", cwd=out)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(UV, "pip", "install", "--python", str(python), str(wheel), cwd=out)
        version = run(str(python), "-I", "-c", SMOKE, cwd=out).strip().splitlines()[-1]
        assert version == PYPROJECT["project"]["version"]
