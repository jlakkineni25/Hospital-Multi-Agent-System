"""
Shared data models for the Multi-Agent Hospital Resource & Patient-Flow system.

Design note: Patients are NOT agents. They are plain data records owned and
reasoned about by whichever agent currently has them (ER, Clinic, etc). An
agent advocates for its patients in negotiation; the patient itself has no
sensors/actuators of its own.
"""

from dataclasses import dataclass, field
from enum import Enum
import itertools


class ResourceType(Enum):
    OR_ROOM = "operating_room"
    ICU_BED = "icu_bed"


class Specialty(Enum):
    GENERAL = "general"
    CARDIAC = "cardiac"
    ORTHO = "ortho"
    TRAUMA = "trauma"


_patient_ids = itertools.count(1)


@dataclass
class Patient:
    """A patient record. Data owned by an agent, never an agent itself."""
    id: int = field(default_factory=lambda: next(_patient_ids))
    name: str = ""
    acuity: int = 3            # 1 = most urgent (immediate), 5 = least urgent
    specialty: Specialty = Specialty.GENERAL
    duration: int = 60         # minutes needed in the OR
    icu_needed: bool = True
    icu_duration: int = 240    # minutes of ICU recovery needed
    arrival_time: int = 0      # minutes since simulation start
    patient_type: str = "scheduled"  # "scheduled" | "walk-in" | "emergency"

    def __repr__(self):
        return f"Patient#{self.id}({self.name}, acuity={self.acuity}, {self.specialty.value})"


@dataclass
class Message:
    """
    A single contract-net protocol message. Every negotiation event in the
    system is one of these, and every one gets logged -- this log is what
    makes the demo *explainable*, not just functional.
    """
    round_id: int
    sender: str
    receiver: str
    performative: str     # "cfp" | "propose" | "refuse" | "accept" | "reject" | "force-allocate"
    resource_type: ResourceType
    patient: Patient
    priority: int          # lower = more urgent (mirrors Patient.acuity)
    detail: str = ""       # human-readable reason, for the "why" log

    def as_log_line(self) -> str:
        return (f"[t={self.round_id:>3}] {self.sender:8s} -> {self.receiver:8s} "
                f"{self.performative:8s} | {self.patient} | {self.detail}")