import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Patient
from csp_solvers import SurgeryScheduler

scheduler = SurgeryScheduler(num_rooms=1)
patients = [
    Patient(name="A", acuity=3, duration=60),
    Patient(name="B", acuity=3, duration=90),
]
emergency = Patient(name="C-emergency", acuity=1, duration=30)
patients.append(emergency)

result = scheduler.solve(patients, forced_first=emergency)
print(result)