"""
Surgery Agent -- owns the OR rooms and negotiates over surgical slots.
"""

from models import Patient
from csp_solvers import SurgeryScheduler


class SurgeryAgent:
    name = "Surgery"

    def __init__(self, num_rooms: int = 2):
        self.scheduler = SurgeryScheduler(num_rooms=num_rooms)
        self.committed: list[Patient] = []      # patients already on the schedule
        self.schedule: dict[int, tuple] = {}     # pid -> (room, start)

    def evaluate_request(self, patient: Patient):
        """
        Try to fit `patient` alongside everything already committed.
        Returns (can_fit, displaced, result) where `displaced` is a list of
        (patient, delay_minutes) for EVERY already-committed patient whose
        start time got pushed later as a result -- whether that happened
        through natural re-optimization or a forced priority override.
        """
        trial = self.committed + [patient]
        result = self.scheduler.solve(trial)

        if result is not None:
            start = result[patient.id][1]
            fits_soon = start <= 30 if patient.acuity <= 2 else start <= 180
        else:
            fits_soon = False

        if result is None or not fits_soon:
            if patient.acuity > 2:
                return (False, [], None)
            result = self.scheduler.solve(trial, forced_first=patient)
            if result is None:
                return (False, [], None)

        # compare every committed patient's OLD start time (from self.schedule)
        # against their NEW start time in this proposed result -- this catches
        # displacement caused by natural re-optimization too, not just forcing
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