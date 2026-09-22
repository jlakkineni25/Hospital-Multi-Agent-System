# Multi-Agent Hospital Resource & Patient-Flow Management System

A multi-agent system (MAS) where four autonomous agents — **ER**, **Surgery**, **ICU**, and **Clinic** — negotiate over shared hospital resources (operating rooms, ICU beds) using a contract-net protocol. Each agent reasons locally with its own OR-Tools CSP (Constraint Satisfaction Problem) model; no agent has direct access to another agent's internal state. All coordination happens through explicit, logged messages.

Built as a case study for **Foundations of AI**, demonstrating PEAS formulation, environment analysis, CSP-based search strategy, and genuine multi-agent negotiation.

## Why this is genuinely multi-agent, not a centralized solver

Each agent solves **only its own local CSP**. Coordination happens entirely through a contract-net negotiation protocol:

1. **Request** — ER (or Clinic, on escalation) sends a `cfp` for an OR slot.
2. **Local evaluation** — Surgery tries to fit the patient into its own schedule. If a high-acuity (emergency) patient doesn't fit cleanly, it attempts a **priority override** — forcing the patient to the front and seeing who gets displaced.
3. **Commit** — on acceptance, the agent updates its own state, then (for surgical patients) triggers a **downstream negotiation** with ICU for a post-op recovery bed.
4. **Termination rule** — if no allocation is possible after 3 rounds, the request is explicitly rejected rather than negotiating forever — this is what prevents a live demo (or a real system) from hanging.

Patients are deliberately **not** agents — they have no sensors or actions of their own. They're data a requesting agent (ER or Clinic) advocates for during negotiation, mirroring how real hospital departments actually operate.

## Project Structure

​```
hospital_mas/
├── models.py            Patient (data), Message (one negotiation event)
├── csp_solvers.py        SurgeryScheduler, ICUCapacity, ClinicScheduler (OR-Tools CP-SAT)
├── er_agent.py             ERAgent
├── surgery_agent.py         SurgeryAgent
├── icu_agent.py               ICUAgent
├── clinic_agent.py              ClinicAgent
├── negotiation.py                 ContractNetProtocol, NegotiationLog
├── simulate.py                      baseline_scenario(), stress_test_scenario()
├── visualize.py                       Swimlane timeline chart
├── main.py                              Entry point: runs both scenarios, saves output/
├── app.py                                 Interactive Streamlit explorer (secondary demo tool)
├── tests/                                   Standalone sanity checks per component
└── PROJECT_NOTES.md                           Rubric mapping
​```


## Setup

```bash
pip install ortools matplotlib streamlit
```

## Usage

### Run the two demo scenarios (baseline + mass-casualty stress test)

```bash
python main.py
```

Prints the full negotiation log for both scenarios and saves swimlane charts + JSON-style logs to `output/`.

### Run the interactive explorer

```bash
streamlit run app.py
```

Adjust OR rooms, ICU beds, patient load, and surge severity with sliders, then run the simulation live — see the negotiation log, swimlane chart, and allocation summary update in real time.

### Run the test suite

```bash
python tests/test_solver.py
python tests/test_negotiation.py
python tests/test_clinic.py
python tests/test_clinic_agent.py
python tests/test_escalation.py
python tests/test_visualize.py
```

## Architecture at a Glance

| Agent | Owns | Negotiates Over |
|---|---|---|
| **ER** | Patient intake | Initiates OR requests |
| **Surgery** | OR rooms, schedule | Bids/accepts OR slots; triggers ICU negotiation |
| **ICU** | Bed capacity | Confirms/delays/rejects recovery bed requests |
| **Clinic** | Appointments, walk-ins | Schedules autonomously; escalates severe walk-ins to ER |

## Known Limitations (disclosed, not hidden)

- **ICU bottleneck is reported, not resolved** — the system surfaces recovery-bed delays honestly but doesn't attempt to free up capacity (e.g., early-discharge negotiation). Flagged as future work.
- **No deterministic tie-breaker** for patients with identical acuity — ordering among equal-priority patients currently depends on CP-SAT solver internals rather than an explicit rule (e.g., earliest-arrival-wins).
- **Centralized solving would find a more globally optimal schedule** — this is a deliberate tradeoff, not an oversight: the distributed design trades some optimality for department autonomy and no single point of failure, which mirrors how real hospital departments actually operate.

See `PROJECT_NOTES.md` for the full rubric mapping and prepared Q&A answers.