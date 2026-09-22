"""
ER Agent -- initiates OR requests on behalf of incoming patients.
Currently the simplest agent: it just holds an intake list. Its real
role is as a REQUESTER in the negotiation protocol (see negotiation.py).
"""

from models import Patient


class ERAgent:
    name = "ER"

    def __init__(self):
        self.intake: list[Patient] = []

    def receive(self, patient: Patient):
        self.intake.append(patient)