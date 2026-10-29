"""Collect the visual baselines into one page for review (ADR 0002 §1).

    uv run python tools/gallery.py                 # candidates: new since origin/dev
    uv run python tools/gallery.py --since dev     # candidates: new since another ref

Each row is one scene: the library's baseline, its plain-Manim twin (the test of the
same name with the suffix ``__manim``) when there is one, and the ``actual`` and
``diff`` images a failing run left in ``tests/visual/_out/``. The caption is the test's
docstring. A baseline that git does not have at the ``--since`` ref is a *candidate*:
nobody has reviewed it yet. The videos of `tools/demos.py` come first, captioned by
their docstrings. The page is written to ``tests/visual/_out/gallery.html``.
"""

from __future__ import annotations

import argparse
import ast
import html
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
VISUAL = ROOT / "tests" / "visual"
BASELINES = VISUAL / "baselines"
OUT = VISUAL / "_out"
DEMOS = OUT / "demos"
TWIN = "__manim"

STYLE = """
:root { --bg: #fafaf9; --fg: #1c1917; --muted: #78716c; --card: #fff; --line: #e7e5e4;
  --accent: #b45309; }
@media (prefers-color-scheme: dark) { :root { --bg: #1c1917; --fg: #f5f5f4;
  --muted: #a8a29e; --card: #292524; --line: #44403c; --accent: #f59e0b; } }
body { margin: 0; padding: 16px; background: var(--bg); color: var(--fg);
  font: 15px/1.5 system-ui, sans-serif; }
h1 { font-size: 20px; margin: 0 0 4px; }
p.lead { color: var(--muted); margin: 0 0 16px; }
section { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 12px; margin: 0 0 16px; }
h2 { font-size: 15px; margin: 0; font-family: ui-monospace, monospace; }
.badge { font: 12px system-ui; color: var(--accent); border: 1px solid var(--accent);
  border-radius: 4px; padding: 0 6px; margin-left: 8px; }
.caption { color: var(--muted); margin: 4px 0 8px; white-space: pre-wrap; }
.row { display: flex; flex-wrap: wrap; gap: 12px; }
figure { margin: 0; flex: 1 1 360px; max-width: 100%; }
figure img, figure video { width: 100%; height: auto; border: 1px solid var(--line);
  background: #000; }
figcaption { font-size: 12px; color: var(--muted); }
"""


def docstrings() -> dict[tuple[str, str], str]:
    """Map (module, test) to the test function's docstring."""
    found = {}
    for path in VISUAL.glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                found[(path.stem, node.name)] = ast.get_docstring(node) or ""
    return found


def demo_captions() -> dict[str, str]:
    """Map each demo function of `tools/demos.py` to its docstring."""
    tree = ast.parse((ROOT / "tools" / "demos.py").read_text(encoding="utf-8"))
    return {
        node.name: ast.get_docstring(node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }


def demos() -> list[str]:
    """One section per rendered demo video."""
    captions = demo_captions()
    sections = []
    for video in sorted(DEMOS.glob("*.mp4"), key=lambda v: v.stat().st_mtime):
        source = html.escape(video.relative_to(OUT).as_posix())
        caption = html.escape(captions.get(video.stem, ""))
        sections.append(
            f"<section><h2>demo::{html.escape(video.stem)}</h2>"
            f'<p class="caption">{caption}</p><div class="row"><figure>'
            f'<video src="{source}" controls loop muted playsinline preload="metadata">'
            "</video></figure></div></section>"
        )
    return sections


def reviewed(since: str) -> set[str]:
    """Baseline paths, relative to the repository, that git has at ``since``."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", since, "--", "tests/visual/baselines"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split()) if result.returncode == 0 else set()


def figure(path: Path, label: str) -> str:
    """One image with its label, linked relative to the page."""
    source = html.escape(path.relative_to(OUT.parent).as_posix())
    return (
        f'<figure><img src="../{source}" alt="{html.escape(label)}" loading="lazy">'
        f"<figcaption>{html.escape(label)}</figcaption></figure>"
    )


def main() -> int:
    """Write the gallery and print its path."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--since", default="origin/dev")
    since = parser.parse_args().since
    known = reviewed(since)
    captions = docstrings()
    sections = demos()
    for baseline in sorted(BASELINES.glob("*/*.png")):
        module, name = baseline.parent.name, baseline.stem
        if name.endswith(TWIN):
            continue
        figures = [figure(baseline, "manim-plots")]
        twin = baseline.with_name(name + TWIN + ".png")
        if twin.exists():
            figures.append(figure(twin, "plain Manim"))
        for kind in ("actual", "diff"):
            extra = OUT / module / f"{name}.{kind}.png"
            if extra.exists():
                figures.append(figure(extra, f"last failing run: {kind}"))
        relative = baseline.relative_to(ROOT).as_posix()
        badge = "" if relative in known else '<span class="badge">candidate</span>'
        caption = html.escape(captions.get((module, name), ""))
        sections.append(
            f"<section><h2>{html.escape(module)}::{html.escape(name)}{badge}</h2>"
            f'<p class="caption">{caption}</p><div class="row">{"".join(figures)}'
            "</div></section>"
        )
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Visual baselines</title><style>{STYLE}</style></head><body>"
        "<h1>Visual baselines</h1>"
        f'<p class="lead">{len(sections)} scenes. <em>candidate</em>: not in git at '
        f"<code>{html.escape(since)}</code>, so not yet reviewed.</p>"
        f"{''.join(sections)}</body></html>"
    )
    OUT.mkdir(exist_ok=True)
    target = OUT / "gallery.html"
    target.write_text(page, encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
