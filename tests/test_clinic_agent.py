import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Patient
from clinic_agent import ClinicAgent

clinic = ClinicAgent(num_rooms=1)
clinic.appointments = [(Patient(name="Appt-A", duration=30), 60)]
clinic.walkins = [
    Patient(name="Mild case", acuity=4, duration=20),
    Patient(name="Severe case", acuity=1, duration=20),
]

escalated = clinic.triage_walkins()
print("Escalated to ER:", escalated)
print("Remaining walk-ins:", clinic.walkins)

assigned, unassigned = clinic.run_day()
print("Assigned:", assigned)
print("Unassigned:", unassigned)