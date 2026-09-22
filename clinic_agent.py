"""
Clinic Agent -- schedules its own appointments/walk-ins autonomously,
and escalates severe walk-ins to ER rather than negotiating for an OR
itself.
"""

from csp_solvers import ClinicScheduler


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