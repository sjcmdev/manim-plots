import pytest
from manim import tempconfig

from poc1.points import ROOT


@pytest.fixture(autouse=True)
def cairo_config():
    with tempconfig(
        {
            "renderer": "cairo",
            "pixel_width": 320,
            "pixel_height": 180,
            "frame_rate": 15,
            "write_to_movie": False,
            "save_last_frame": False,
            "preview": False,
            "disable_caching": True,
            "media_dir": str(ROOT / "media"),
            "progress_bar": "none",
            "verbosity": "ERROR",
        }
    ):
        yield
