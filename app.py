"""
Interactive exploration tool for the hospital MAS -- lets you adjust
capacity and surge size, then see the negotiation log and swimlane
chart update live. This is a SECONDARY demo aid; main.py + the saved
PNGs remain the primary presentation artifact.

Run with:
    streamlit run app.py
"""

import streamlit as st

from models import Patient, Specialty
from er_agent import ERAgent
from surgery_agent import SurgeryAgent
from icu_agent import ICUAgent
from clinic_agent import ClinicAgent
from negotiation import ContractNetProtocol, NegotiationLog
from visualize import plot_swimlane

st.set_page_config(page_title="Hospital Multi-Agent System", layout="wide")
st.title("Multi-Agent Hospital Resource & Patient-Flow ")
st.caption("Adjust capacity and surge size, then run the negotiation and see what happens.")

st.markdown("""
    <style>
    [data-testid="stToolbar"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ---- Sidebar controls (ALL of them, before the button) ----
st.sidebar.header("Hospital Capacity")
num_or_rooms = st.sidebar.slider("OR rooms", min_value=1, max_value=10, value=1)
num_icu_beds = st.sidebar.slider("ICU beds", min_value=1, max_value=10, value=2)

st.sidebar.header("Pre-scheduled Patients")
num_prescheduled = st.sidebar.slider("Routine patients already booked", 0, 10, 2)

st.sidebar.header("Clinic Walk-ins")
num_mild_walkins = st.sidebar.slider("Mild walk-ins (stay with Clinic)", 0, 5, 2)
num_severe_walkins = st.sidebar.slider("Severe walk-ins (escalate to ER)", 0, 5, 1)

st.sidebar.header("Mass-Casualty Surge")
num_surge = st.sidebar.slider("Number of emergency patients arriving at once", 0, 15, 3)
surge_acuity = st.sidebar.select_slider(
    "Surge acuity (1 = most urgent)", options=[1, 2, 3], value=1
)

run_button = st.sidebar.button("Run Simulation", type="primary")

# ---- Run simulation on button press ----
if run_button:
    er = ERAgent()
    surgery = SurgeryAgent(num_rooms=num_or_rooms)
    icu = ICUAgent(total_beds=num_icu_beds)
    clinic = ClinicAgent(num_rooms=1)
    log = NegotiationLog()
    protocol = ContractNetProtocol(er, surgery, icu, clinic, log)

    results = []

    # Clinic walk-ins -- mix of mild (stays with Clinic) and severe (escalates to ER)
    clinic.walkins = (
        [Patient(name=f"Mild-Walkin-{i+1}", acuity=4, duration=20, patient_type="walk-in")
         for i in range(num_mild_walkins)]
        + [Patient(name=f"Severe-Walkin-{i+1}", acuity=1, duration=50, icu_duration=200, patient_type="walk-in")
           for i in range(num_severe_walkins)]
    )
    escalated = protocol.run_clinic_escalations()
    for p in escalated:
        er.receive(p)
        ok = protocol.request_or("ER", p)
        results.append((p, ok))

    clinic.run_day()  # schedule whichever walk-ins Clinic kept for itself

    # pre-scheduled routine patients
    for i in range(num_prescheduled):
        p = Patient(name=f"Routine-{i+1}", acuity=4, duration=90, icu_duration=180)
        protocol.request_or("ER", p)

    # the surge
    for i in range(num_surge):
        p = Patient(name=f"Surge-{i+1}", acuity=surge_acuity,
                     specialty=Specialty.TRAUMA, duration=80,
                     icu_duration=240, patient_type="emergency")
        er.receive(p)
        ok = protocol.request_or("ER", p)
        results.append((p, ok))

    # ---- Summary ----
    st.subheader("Summary")
    allocated = sum(1 for _, ok in results if ok)
    denied = len(results) - allocated
    col1, col2, col3 = st.columns(3)
    col1.metric("Patients allocated (surge + escalated)", allocated)
    col2.metric("Patients denied", denied)
    col3.metric("Total negotiation messages", len(log.messages))

    if denied > 0:
        st.warning(f"{denied} patient(s) could not be allocated even after negotiation -- "
                    f"capacity is genuinely exceeded. Try increasing OR rooms or ICU beds.")

    # ---- Clinic's own schedule (non-escalated walk-ins) ----
    if clinic.assigned or clinic.unassigned:
        st.subheader("Clinic's Own Schedule (non-escalated walk-ins)")
        col4, col5 = st.columns(2)
        col4.metric("Walk-ins Clinic scheduled itself", len(clinic.assigned))
        col5.metric("Walk-ins Clinic could not fit", len(clinic.unassigned))

    # ---- Swimlane chart ----
    st.subheader("Negotiation Timeline")
    chart_path = "app_output_swimlane.png"
    plot_swimlane(log, "Live Simulation", chart_path)
    st.image(chart_path)

    # ---- Log table ----
    st.subheader("Negotiation Log")
    log_rows = [
        {"t": m.round_id, "From": m.sender, "To": m.receiver,
         "Type": m.performative, "Patient": str(m.patient), "Detail": m.detail}
        for m in log.messages
    ]
    st.dataframe(log_rows, use_container_width=True)

else:
    st.info("Set your parameters on the left, then click **Run Simulation**.")