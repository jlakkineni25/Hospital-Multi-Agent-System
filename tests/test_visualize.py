import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulate import stress_test_scenario
from visualize import plot_swimlane

log, state, results = stress_test_scenario()
plot_swimlane(log, "Stress Test: Mass-Casualty Surge", "stress_test_swimlane.png")
print("Saved chart.")