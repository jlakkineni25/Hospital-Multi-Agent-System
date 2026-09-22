import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Patient
from csp_solvers import ClinicScheduler

scheduler = ClinicScheduler(num_rooms=1, day_minutes=200)  # short day

appts = [
    (Patient(name="Appt-A", duration=30), 60),
    (Patient(name="Appt-B", duration=30), 120),
]
walkins = [
    Patient(name="Walkin-1", duration=20),
    Patient(name="Walkin-2", duration=20),
    Patient(name="Walkin-3", duration=100),  # too big to fit anywhere
]

assigned, unassigned = scheduler.schedule(appts, walkins)
print("Assigned:", assigned)
print("Unassigned:", unassigned)