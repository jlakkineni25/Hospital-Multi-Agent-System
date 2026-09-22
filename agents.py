"""
The agents. Each owns its own resource pool and solves its own local
CSP -- no agent ever inspects another agent's internal state directly.
All cross-agent interaction happens through Messages via the negotiation
protocol (we'll build that next).
"""

from models import Patient
from csp_solvers import SurgeryScheduler, ICUCapacity, ClinicScheduler

class SurgeryAgent:
    name = "Surgery"

    def __init__(self, num_rooms: int = 2):
        self.scheduler = SurgeryScheduler(num_rooms=num_rooms)
        self.committed: list[Patient] = []      # patients already on the schedule
        self.schedule: dict[int, tuple] = {}     # pid -> (room, start)

    def evaluate_request(self, patient: Patient):
        """
        Try to fit `patient` alongside everything already committed.
        Returns (can_fit, bumped_patients, result_schedule).
        """
        trial = self.committed + [patient]
        result = self.scheduler.solve(trial)
        if result is not None:
            start = result[patient.id][1]
            # "fits cleanly" if it doesn't have to wait past a same-day window
            fits_soon = start <= 30 if patient.acuity <= 2 else start <= 180
            if fits_soon:
                return (True, [], result)

        # doesn't fit soon enough (or at all) -- only emergencies get to
        # force a priority override; routine patients are simply refused
        if patient.acuity > 2:
            return (False, [], None)

        forced_result = self.scheduler.solve(trial, forced_first=patient)
        if forced_result is None:
            return (False, [], None)  # truly infeasible even forced

        bumped = sorted(
            self.committed,
            key=lambda p: forced_result[p.id][1],
            reverse=True,
        )[:1] if self.committed else []
        return (True, bumped, forced_result)

    def commit(self, patient: Patient, new_schedule: dict):
        self.committed.append(patient)
        self.schedule.update(new_schedule)


class ICUAgent:
    name = "ICU"

    def __init__(self, total_beds: int = 4):
        self.capacity = ICUCapacity(total_beds=total_beds)
        self.committed: list[Patient] = []

    def evaluate_request(self, earliest_start: int, duration: int):
        slot = self.capacity.free_slot_after(earliest_start, duration)
        if slot is None:
            return None
        delay = slot - earliest_start
        return slot, delay

    def commit(self, patient: Patient, start: int, duration: int):
        self.capacity.reserve(start, duration)
        self.committed.append(patient)


class ERAgent:
    name = "ER"

    def __init__(self):
        self.intake: list[Patient] = []

    def receive(self, patient: Patient):
        self.intake.append(patient)

class ClinicAgent:
    name = "Clinic"

    def __init__(self, num_rooms: int = 2):
        self.scheduler = ClinicScheduler(num_rooms=num_rooms)
        self.appointments: list = []   # (Patient, fixed_start)
        self.walkins: list = []
        self.assigned: dict = {}
        self.unassigned: list = []

    def run_day(self):
        self.assigned, self.unassigned = self.scheduler.schedule(self.appointments, self.walkins)
        return self.assigned, self.unassigned

    ESCALATION_ACUITY_THRESHOLD = 2  # walk-ins this urgent or worse get escalated to ER

    def triage_walkins(self):
        """Split walk-ins into ones Clinic keeps vs. ones that must escalate to ER."""
        keep, escalate = [], []
        for p in self.walkins:
            (escalate if p.acuity <= self.ESCALATION_ACUITY_THRESHOLD else keep).append(p)
        self.walkins = keep
        return escalate