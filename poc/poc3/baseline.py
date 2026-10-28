"""Reproduce the six pre-fix failures using the frozen, independent v2 copy."""

import json

from manim import tempconfig

from poc3 import baseline_model, scene, test_cost, test_fixes
from poc3.model import ROOT, record


def main():
    results = {}
    (ROOT / "media").mkdir(exist_ok=True)
    originals = []
    for module, name, value in [
        (test_fixes, "System", baseline_model.System),
        (test_fixes, "METRICS", baseline_model.METRICS),
        (test_fixes, "record", results.__setitem__),
        (test_cost, "System", baseline_model.System),
        (test_cost, "METRICS", baseline_model.METRICS),
        (test_cost, "record", results.__setitem__),
        (scene, "METRICS", baseline_model.METRICS),
    ]:
        originals.append((module, name, getattr(module, name)))
        setattr(module, name, value)
    try:
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
            failures = {}
            for name in [
                "test_k4_fadeout_cleanup",
                "test_k4_larger_target",
                "test_k4_local_placement",
                "test_k4_no_offplane_probe",
                "test_k4_placement_growth",
                "test_k4_cached_weights",
            ]:
                try:
                    getattr(test_fixes, name)()
                except (AssertionError, ValueError) as exc:
                    failures[name] = f"{type(exc).__name__}: {exc}"
            results["failures"] = failures
            test_cost.test_g6_600_frame_cost(True)
            results["g6_True"].pop("frames")
        record("baseline", results)
        print(json.dumps(results, indent=2))
        assert len(failures) == 6
    finally:
        for module, name, value in originals:
            setattr(module, name, value)


if __name__ == "__main__":
    main()
