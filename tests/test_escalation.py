import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Patient
from er_agent import ERAgent
from surgery_agent import SurgeryAgent
from icu_agent import ICUAgent
from clinic_agent import ClinicAgent
from negotiation import ContractNetProtocol, NegotiationLog

er = ERAgent()
surgery = SurgeryAgent(num_rooms=1)
icu = ICUAgent(total_beds=2)
clinic = ClinicAgent(num_rooms=1)
log = NegotiationLog()
protocol = ContractNetProtocol(er, surgery, icu, clinic, log)

clinic.walkins = [Patient(name="Severe walk-in", acuity=1, duration=50, icu_duration=200)]

escalated = protocol.run_clinic_escalations()
print("ER intake after escalation:", er.intake)
log.print_all()