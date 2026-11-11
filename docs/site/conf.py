"""Sphinx configuration of the manim-plots user documentation (task 14, row DO-1)."""

from importlib.metadata import version as _version

project = "manim-plots"
author = "SirJamesClarkMaxwell"
copyright = "2026, SirJamesClarkMaxwell"
release = _version("manim-plots")
version = release

extensions = ["sphinx.ext.autodoc", "numpydoc"]
html_theme = "alabaster"
html_title = f"manim-plots {release}"
exclude_patterns = ["_build"]

autodoc_member_order = "bysource"
autodoc_typehints = "none"  # numpydoc renders the documented types
numpydoc_show_class_members = False
numpydoc_class_members_toctree = False
