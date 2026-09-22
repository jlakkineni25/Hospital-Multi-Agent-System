import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Patient
from negotiation import ContractNetProtocol, NegotiationLog
from er_agent import ERAgent
from surgery_agent import SurgeryAgent
from icu_agent import ICUAgent
from clinic_agent import ClinicAgent

er = ERAgent()
surgery = SurgeryAgent(num_rooms=1)
icu = ICUAgent(total_beds=2)
clinic = ClinicAgent(num_rooms=1)
log = NegotiationLog()
protocol = ContractNetProtocol(er, surgery, icu, clinic, log)

p1 = Patient(name="A", acuity=3, duration=60, icu_duration=120)
protocol.request_or("ER", p1)

log.print_all()