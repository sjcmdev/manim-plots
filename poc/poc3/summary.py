"""Print the measured report inputs without rerunning animations."""

import json

import numpy as np

from poc3.model import ROOT
from poc3.test_animations import AX_ANIMATIONS
from poc3.test_containers import CASES


def read(name):
    return json.loads((ROOT / "results" / f"{name}.json").read_text(encoding="utf-8"))


def main():
    axes = []
    events = []
    for name in [*AX_ANIMATIONS, "RotateTAU"]:
        row = read(f"k2_{name}")
        events.extend(row["context_events"])
        axes.append(
            {
                "name": name,
                **{
                    k: row[k]
                    for k in [
                        "permanent",
                        "max_frame_error",
                        "max_motion",
                        "reattach_error",
                        "pixel_channel_difference",
                        "axis_error",
                    ]
                },
            }
        )
    containers = []
    for name in [
        *(f"static_{case}" for case in CASES),
        "animation_animate",
        "animation_Rotate",
    ]:
        row = read(f"k3_{name}")
        containers.append(
            {"name": name, **{k: v for k, v in row.items() if k != "writer_events"}}
        )
    suspend = []
    writes = []
    for axis in [False, True]:
        for row in read(f"k1_table_{axis}"):
            suspend.extend(event["stack_ns"] for event in row["suspends"])
            writes.extend(event["stack_ns"] for event in row["writes"])
    summary = {"K2": axes, "K3": containers}
    for label, values in [
        ("suspend_stack_us", np.array(suspend) / 1000),
        ("write_stack_us", np.array(writes) / 1000),
        ("simulation_ms", np.array([event["simulation_ns"] for event in events]) / 1e6),
    ]:
        summary[label] = {
            "count": len(values),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)),
            "max": float(np.max(values)),
        }
    for name in [
        "g6_False",
        "g6_True",
        "g6_micro",
        "k1_stack_cost",
        "k4_fadeout",
        "k4_larger_target",
        "k4_local",
        "k4_bounds",
        "k4_growth",
        "k4_nonaffine_local",
        "k5_callable",
    ]:
        row = read(name)
        if isinstance(row, dict):
            row.pop("frames", None)
        summary[name] = row
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
