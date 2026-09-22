"""
ICU Agent -- owns bed capacity and answers post-op recovery bed requests.
"""

from models import Patient
from csp_solvers import ICUCapacity


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