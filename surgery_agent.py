"""
Surgery Agent -- owns the OR rooms and negotiates over surgical slots.
Uses Uniform Cost Search (via SurgeryScheduler) to place patients,
most urgent first, with DFS backtracking as a fallback.
"""

from models import Patient
from csp_solvers import SurgeryScheduler


class SurgeryAgent:
    name = "Surgery"

    def __init__(self, num_rooms: int = 2, horizon_minutes: int = 24 * 60):
        self.scheduler = SurgeryScheduler(num_rooms=num_rooms, horizon_minutes=horizon_minutes)
        self.committed: list[Patient] = []
        self.schedule: dict[int, tuple] = {}

    def evaluate_request(self, patient: Patient):
        """
        Dry-run: re-run priority-ordered UCS placement for everyone
        (committed + this new patient) and see what comes out. Because
        SurgeryScheduler.solve() always processes patients most-urgent
        first, a high-acuity patient naturally lands in the earliest slot
        NOT already claimed by an equal-or-higher priority patient -- this
        is the correct, expected outcome of priority-ordered search, not
        a failure. We only refuse when placement is genuinely infeasible
        (the horizon is exceeded).
        """
        trial = self.committed + [patient]
        result = self.scheduler.solve(trial)

        if result is None:
            return (False, [], None)  # genuinely infeasible

        displaced = []
        for p in self.committed:
            old_start = self.schedule[p.id][1]
            new_start = result[p.id][1]
            if new_start > old_start:
                displaced.append((p, new_start - old_start))

        return (True, displaced, result)

    def commit(self, patient: Patient, new_schedule: dict):
        self.committed.append(patient)
        self.schedule.update(new_schedule)