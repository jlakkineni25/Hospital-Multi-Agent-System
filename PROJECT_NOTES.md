# Multi-Agent Hospital Resource & Patient-Flow Management System
## Rubric Mapping — Case Study (20 marks)

---

## 1. PEAS Formulation

| Agent | Performance Measure | Environment | Actuators | Sensors |
|---|---|---|---|---|
| **ER** (`er_agent.py`) | Get patients routed to care quickly | Incoming patient arrivals (stochastic) | `receive()` — intake a patient; initiate OR requests via negotiation | Patient acuity/urgency data on arrival |
| **Surgery** (`surgery_agent.py`) | Maximize patients served, minimize delay for high-acuity cases | Its own OR room schedule + incoming requests from ER | `commit()` — finalize a schedule; `evaluate_request()` proposes/refuses | Committed patient list, requested patient's acuity/duration |
| **ICU** (`icu_agent.py`) | Guarantee recovery beds without violating capacity | Bed occupancy over time | `commit()` — reserve a bed | Current bed reservations, incoming bed requests |
| **Clinic** (`clinic_agent.py`) | Serve appointments on time, absorb walk-ins where possible | Its own room schedule, appointment list, walk-in arrivals | `run_day()` — finalize schedule; `triage_walkins()` — escalate | Appointment times (fixed), walk-in acuity |

**Key point for Q&A:** every agent's Sensors/Actuators are scoped to its **own** state only — no agent reads another agent's internal data structure directly. All cross-agent information flows through `Message` objects (`models.py`).

---

## 2. Environment & Agent Analysis

- **Partially observable** — Surgery never sees ICU's bed occupancy directly, and vice versa; they only learn what the other reveals through a `cfp`/`propose` exchange (`negotiation.py`).
- **Dynamic** — ER patient arrivals and Clinic walk-ins happen unpredictably relative to each agent's existing plan; each `evaluate_request()` call re-solves from current state, not a fixed plan.
- **Stochastic** — patient acuity, duration, and arrival timing are not controlled by any single agent; the stress-test scenario (`simulate.py::stress_test_scenario`) deliberately models a surge of unpredictable high-acuity arrivals.
- **Multi-agent, mixed cooperative** — ER, Surgery, ICU, Clinic all share a global goal (treat patients) but have locally competing constraints (Surgery wants to protect its schedule, ER wants urgent care now). This is **cooperative, not adversarial** — no agent is trying to defeat another, but their local objectives can still conflict, which is exactly what negotiation resolves.

**Evidence of agent independence:** the honest fix we made (Sept — displacement logging) proves this: Surgery's CP-SAT solver freely re-optimizes across ALL committed patients on every request, without needing global oversight — see `surgery_agent.py::evaluate_request()`.

---

## 3. Search Strategy / Algorithmic Modeling

This is a **Distributed Constraint Satisfaction Problem (DCSP)**, not classical search (no A*, no BFS/DFS) — the right call because this is a resource-allocation/scheduling problem, not a pathfinding problem.

| Agent | CSP Structure | Why this shape |
|---|---|---|
| Surgery | Fully flexible — every patient's start time is a free variable; `NoOverlap` per room; objective = minimize acuity-weighted start time (`csp_solvers.py::SurgeryScheduler`) | Nobody's slot is fixed — emergencies can always compete for the front |
| ICU | Not a full CSP — a capacity sweep-line check (`csp_solvers.py::ICUCapacity`) | Bed occupancy is a simpler resource-counting problem, doesn't need a full solver call per query |
| Clinic | Mixed hard/soft — appointments are **hard-constrained** fixed slots; walk-ins are a **best-effort soft-fit** maximization (`csp_solvers.py::ClinicScheduler`) | Real clinics can't move a booked appointment; walk-ins are genuinely optional |

**Comparative justification (this is what earns "Exceeds Expectations" on this row):** Surgery's fully-flexible model and Clinic's hard/soft hybrid model are deliberately different CSP structures for two different real-world constraint types — not the same algorithm copy-pasted twice.

---

## 4. Tool/Package

- **Google OR-Tools (CP-SAT solver)** — used for all three schedulers. Chosen because it's a production-grade constraint solver; we don't hand-roll the actual search.
- **Custom contract-net negotiation protocol** (`negotiation.py`) — no off-the-shelf library does "agents negotiating over independent CSP solutions," so this layer is legitimately hand-written, on top of the OR-Tools solvers.
- **Matplotlib** — for the swimlane visualization (`visualize.py`), not part of the reasoning system, purely for demo/explanation.

---

## 5. Multi-Agent Execution & Interaction

This is proven directly by the negotiation log — every allocation is a **request → evaluate → propose → accept/refuse → commit** cycle (`negotiation.py::ContractNetProtocol`), not a single centralized solve.

**Concrete evidence to show live:**
- `output/stress_test_swimlane.png` — visually shows request/propose/accept arrows between all 4 agent lanes, plus the Clinic → ER escalation
- The **displacement logging** (`"reschedule effect: ... pushed back Nmin"`) — proves agents' decisions have visible, honest side-effects on each other, not silent internal bookkeeping
- The **termination rule** (`ContractNetProtocol.MAX_ROUNDS = 3`) — proves the negotiation can't hang forever; demonstrated when a request is `reject`ed after 3 failed attempts

**Interaction types demonstrated (deliberately more than one, for variety):**
1. **Peer negotiation** — ER ↔ Surgery ↔ ICU (bid/request/commit)
2. **Escalation** — Clinic → ER (a different pattern: handoff, not bidding)

---

## 6. Demo Quality & Testing Scenarios

Two scenarios, same code, different conditions:

| Scenario | Function | What it proves |
|---|---|---|
| Baseline | `simulate.py::baseline_scenario()` | Normal flow — clean negotiation, zero conflicts, zero displacement |
| Stress test | `simulate.py::stress_test_scenario()` | Genuine contention — 1 OR room, tight ICU beds, Clinic escalation + mass-casualty surge; produces real bumps, cascading ICU delays (up to 660min by the last patient), and visible negotiation volume growth |

**Run with:** `python main.py` — single command, produces both scenario logs + both swimlane PNGs into `output/`.

**Known, deliberately-disclosed limitations (mention these proactively in Q&A — it's stronger than waiting to be asked):**
1. ICU bottleneck is **reported honestly, not resolved** — the system doesn't attempt to free up ICU capacity (e.g., early discharge negotiation); it just tells you the delay. Framed as future work.
2. Same-acuity patients (e.g., two acuity-1 patients) don't have a deterministic tie-breaker (like earliest-arrival-wins) — solver internals decide ordering. Framed as a known extension.
3. A centralized solver would find a more globally-optimal schedule than this distributed version — this is a **deliberate tradeoff**, not an oversight (see Q&A answer below).

---

## Q&A — Ready Answers

**"Why not just use one centralized solver instead of 4 negotiating agents?"**
> A centralized solver would likely find a better global schedule. This system deliberately trades some of that optimality for department autonomy and no single point of failure — realistic, because in a real hospital, no department cedes full scheduling control to one central AI.

**"What happens if negotiation doesn't converge?"**
> `MAX_ROUNDS = 3` in `negotiation.py`. After 3 failed attempts, the request is explicitly rejected and logged — this is what prevents a live demo (or a real system) from hanging indefinitely.

**"Why isn't a Patient an agent?"**
> A patient has no sensors or independent actions — it's pure data (`models.py::Patient`, a dataclass) owned by whichever agent currently advocates for it (ER or Clinic). This mirrors real hospitals: patients don't negotiate for themselves, departments do.

**"Show me where the multi-agent part actually happens, not just multiple objects."**
> Point at any negotiation log segment — no agent ever calls another agent's internal method directly. Every interaction is a `Message` (`models.py`) passed through `ContractNetProtocol`. `SurgeryAgent` never reads `ICUAgent.capacity` directly, for example — it only knows what `ICUAgent.evaluate_request()` tells it.

**"What's the difference between Surgery's CSP and Clinic's CSP?"**
> Surgery's is fully flexible — every patient's slot can move to optimize priority. Clinic's is a hybrid — appointments are hard-locked, walk-ins are a soft-fit maximization. Two different constraint structures for two genuinely different real-world problems, not the same algorithm reused.

---

## File Reference

| File | Purpose |
|---|---|
| `models.py` | `Patient` (data), `Message` (negotiation event) |
| `csp_solvers.py` | `SurgeryScheduler`, `ICUCapacity`, `ClinicScheduler` — the CP-SAT/capacity logic |
| `er_agent.py`, `surgery_agent.py`, `icu_agent.py`, `clinic_agent.py` | One file per agent |
| `negotiation.py` | `ContractNetProtocol`, `NegotiationLog` — the coordination layer |
| `simulate.py` | `baseline_scenario()`, `stress_test_scenario()` |
| `visualize.py` | Swimlane timeline chart |
| `main.py` | Single entry point — runs everything, saves to `output/` |
| `tests/` | Standalone sanity checks for each component, run independently |