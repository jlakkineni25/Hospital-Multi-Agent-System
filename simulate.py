"""
Two demo scenarios:
  1. baseline_scenario()    -- normal patient flow, smooth negotiation
  2. stress_test_scenario() -- a mass-casualty surge hits ER, plus a severe
                                walk-in escalates from Clinic
"""

from models import Patient, Specialty
from negotiation import ContractNetProtocol, NegotiationLog
from er_agent import ERAgent
from surgery_agent import SurgeryAgent
from icu_agent import ICUAgent
from clinic_agent import ClinicAgent


def baseline_scenario():
    er = ERAgent()
    surgery = SurgeryAgent(num_rooms=2)
    icu = ICUAgent(total_beds=4)
    clinic = ClinicAgent(num_rooms=2)
    log = NegotiationLog()
    protocol = ContractNetProtocol(er, surgery, icu, clinic, log)

    # -- Clinic's day: a couple of fixed appointments, one mild walk-in
    clinic.appointments = [
        (Patient(name="A. Rao", duration=30), 60),
        (Patient(name="B. Iyer", duration=45), 150),
    ]
    clinic.walkins = [
        Patient(name="C. Nair (walk-in)", acuity=4, duration=20, patient_type="walk-in"),
    ]
    protocol.run_clinic_escalations()  # none expected -- mild walk-in stays with Clinic
    clinic.run_day()

    # -- ER: a couple of moderate-acuity patients needing surgery
    patients = [
        Patient(name="D. Menon", acuity=3, specialty=Specialty.GENERAL,
                duration=90, icu_duration=180),
        Patient(name="E. Thomas", acuity=3, specialty=Specialty.ORTHO,
                duration=60, icu_duration=120),
    ]
    for p in patients:
        er.receive(p)
        protocol.request_or("ER", p)

    return log, (er, surgery, icu, clinic)


def stress_test_scenario():
    er = ERAgent()
    surgery = SurgeryAgent(num_rooms=1)
    icu = ICUAgent(total_beds=2)
    clinic = ClinicAgent(num_rooms=1)
    log = NegotiationLog()
    protocol = ContractNetProtocol(er, surgery, icu, clinic, log)

    # routine patients already booked before the surge hits
    pre_scheduled = [
        Patient(name="F. Pillai", acuity=4, duration=90, icu_duration=180),
        Patient(name="G. Krishnan", acuity=4, duration=120, icu_duration=240),
    ]
    for p in pre_scheduled:
        protocol.request_or("ER", p)

    # a severe walk-in at Clinic that must escalate
    clinic.walkins = [
        Patient(name="I. Subra (walk-in)", acuity=1, duration=50,
                icu_duration=200, patient_type="walk-in"),
    ]
    escalated = protocol.run_clinic_escalations()
    for p in escalated:
        protocol.request_or("ER", p)   # now negotiate for their OR too

    # the mass-casualty surge itself
    surge_patients = [
        Patient(name="J. Kumar (MVA)", acuity=1, specialty=Specialty.TRAUMA,
                duration=100, icu_duration=300, patient_type="emergency"),
        Patient(name="K. Devi (MVA)", acuity=1, specialty=Specialty.TRAUMA,
                duration=80, icu_duration=240, patient_type="emergency"),
        Patient(name="L. Suresh (MVA)", acuity=2, specialty=Specialty.TRAUMA,
                duration=70, icu_duration=180, patient_type="emergency"),
    ]
    results = []
    for p in surge_patients:
        er.receive(p)
        ok = protocol.request_or("ER", p)
        results.append((p, ok))

    return log, (er, surgery, icu, clinic), results


if __name__ == "__main__":
    print("=" * 70)
    print("BASELINE SCENARIO")
    print("=" * 70)
    log, _ = baseline_scenario()
    log.print_all()

    print()
    print("=" * 70)
    print("STRESS TEST -- MASS CASUALTY SURGE")
    print("=" * 70)
    log2, _, results = stress_test_scenario()
    log2.print_all()

    print()
    for p, ok in results:
        print(f"  {p}: {'ALLOCATED' if ok else 'DENIED (no capacity even after negotiation)'}")