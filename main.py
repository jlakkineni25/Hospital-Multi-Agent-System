"""
Run both demo scenarios end-to-end and produce the artifacts you'd show
live: printed negotiation logs + swimlane timeline images.

    python main.py
"""

import json
import os

from simulate import baseline_scenario, stress_test_scenario
from visualize import plot_swimlane

OUT_DIR = "output"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 72)
    print("SCENARIO 1: BASELINE -- normal patient flow")
    print("=" * 72)
    log1, state1 = baseline_scenario()
    log1.print_all()
    plot_swimlane(log1, "Baseline: Normal Patient Flow",
                  os.path.join(OUT_DIR, "baseline_swimlane.png"))

    print()
    print("=" * 72)
    print("SCENARIO 2: STRESS TEST -- mass casualty surge")
    print("=" * 72)
    log2, state2, results = stress_test_scenario()
    log2.print_all()
    print()
    print("Outcome:")
    for p, ok in results:
        status = "ALLOCATED" if ok else "DENIED (no capacity even after negotiation)"
        print(f"  - {p.name:20s} (acuity {p.acuity}): {status}")
    plot_swimlane(log2, "Stress Test: Mass-Casualty Surge",
                  os.path.join(OUT_DIR, "stress_test_swimlane.png"))

    print()
    print(f"Artifacts written to: {OUT_DIR}/")
    for fn in sorted(os.listdir(OUT_DIR)):
        print(f"  - {fn}")


if __name__ == "__main__":
    main()