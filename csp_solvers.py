"""
Local CSP models, one per agent, each solved with OR-Tools CP-SAT.

This is the "Search Strategy / Algorithmic Modeling" piece: every agent
reasons about ITS OWN resource pool only. No agent ever sees another
agent's internal schedule directly -- they only exchange Messages.
"""

from ortools.sat.python import cp_model


class SurgeryScheduler:
    """
    Local CSP for the Surgery/OR Agent.

    Variables : an interval per patient, per OR room (only one is "active")
    Hard constraints : no two surgeries overlap in the same OR;
                        each surgery must start within its allowed window
    Soft preference   : minimize total start-time (serve everyone as early
                         as possible), weighted by inverse acuity so urgent
                         patients are pulled earlier
    """

    def __init__(self, num_rooms: int, horizon_minutes: int = 24 * 60):
        self.num_rooms = num_rooms
        self.horizon = horizon_minutes

    def solve(self, patients, forced_first=None):
        """
        patients: list[Patient] to schedule this round.
        forced_first: optional Patient that MUST be scheduled at t=0 in some
                      room (used when an emergency wins the negotiation).
        Returns: dict patient_id -> (room_idx, start_min) or None if infeasible.
        """
        if not patients:
            return {}

        model = cp_model.CpModel()
        starts, ends, intervals, room_of = {}, {}, {}, {}
        all_intervals_per_room = {r: [] for r in range(self.num_rooms)}

        for p in patients:
            starts[p.id] = model.NewIntVar(0, self.horizon, f"start_{p.id}")
            ends[p.id] = model.NewIntVar(0, self.horizon, f"end_{p.id}")
            room_of[p.id] = model.NewIntVar(0, self.num_rooms - 1, f"room_{p.id}")
            model.Add(ends[p.id] == starts[p.id] + p.duration)

            # per-room optional intervals + exactly one active
            room_intervals = []
            for r in range(self.num_rooms):
                is_in_room = model.NewBoolVar(f"p{p.id}_room{r}")
                iv = model.NewOptionalIntervalVar(
                    starts[p.id], p.duration, ends[p.id], is_in_room, f"iv_{p.id}_{r}"
                )
                all_intervals_per_room[r].append(iv)
                room_intervals.append(is_in_room)
            model.Add(sum(room_intervals) == 1)
            for r, is_in_room in enumerate(room_intervals):
                model.Add(room_of[p.id] == r).OnlyEnforceIf(is_in_room)

            if forced_first is not None and p.id == forced_first.id:
                model.Add(starts[p.id] == 0)

        for r in range(self.num_rooms):
            model.AddNoOverlap(all_intervals_per_room[r])

        # soft objective: urgent patients (low acuity number) weighted heavier
        model.Minimize(sum((6 - p.acuity) * starts[p.id] for p in patients))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2.0
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        return {p.id: (solver.Value(room_of[p.id]), solver.Value(starts[p.id])) for p in patients}


class ICUCapacity:
    """
    Local CSP for the ICU Agent: a cumulative-resource (bed count) check.
    Not a full solver call for every query -- ICU just needs to answer
    "can I fit a stay of length D starting at time T given my current
    occupancy?" which is a capacity/availability check.
    """

    def __init__(self, total_beds: int):
        self.total_beds = total_beds
        self.occupied = []  # list of (start, end) reserved intervals

    def can_accept(self, start: int, duration: int) -> bool:
        end = start + duration
        events = []
        for (s, e) in self.occupied:
            events.append((s, 1))
            events.append((e, -1))
        events.append((start, 1))
        events.append((end, -1))
        events.sort()
        cur = 0
        peak = 0
        for _, delta in events:
            cur += delta
            peak = max(peak, cur)
        return peak <= self.total_beds

    def reserve(self, start: int, duration: int):
        self.occupied.append((start, start + duration))

    def free_slot_after(self, earliest: int, duration: int, search_window: int = 24 * 60):
        """Find the earliest start >= earliest that fits, scanning in 15-min steps."""
        t = earliest
        while t < earliest + search_window:
            if self.can_accept(t, duration):
                return t
            t += 15
        return None

class ClinicScheduler:
    """
    Local CSP for the Clinic Agent.
    Hard constraints : appointment patients occupy fixed, pre-booked slots.
    Soft-fit problem  : walk-ins are inserted into whatever gaps remain
                        between appointments across a small number of rooms.
    """

    def __init__(self, num_rooms: int, day_minutes: int = 8 * 60):
        self.num_rooms = num_rooms
        self.day_minutes = day_minutes

    def schedule(self, appointments, walkins):
        """
        appointments: list[(Patient, fixed_start)] -- hard constraints
        walkins: list[Patient] -- soft-fit, best effort
        Returns: (assigned: dict pid -> (room, start), unassigned: list[Patient])
        """
        model = cp_model.CpModel()
        starts, ends, room_of = {}, {}, {}
        rooms_iv = {r: [] for r in range(self.num_rooms)}
        placed_bool = {}

        all_patients = [p for p, _ in appointments] + walkins
        fixed = {p.id: t for p, t in appointments}

        for p in all_patients:
            starts[p.id] = model.NewIntVar(0, self.day_minutes, f"s_{p.id}")
            ends[p.id] = model.NewIntVar(0, self.day_minutes, f"e_{p.id}")
            model.Add(ends[p.id] == starts[p.id] + p.duration)

            if p.id in fixed:
                model.Add(starts[p.id] == fixed[p.id])
                placed_bool[p.id] = model.NewConstant(1)
            else:
                placed_bool[p.id] = model.NewBoolVar(f"placed_{p.id}")

            room_of[p.id] = model.NewIntVar(0, self.num_rooms - 1, f"room_{p.id}")
            per_room_bools = []
            for r in range(self.num_rooms):
                b = model.NewBoolVar(f"p{p.id}_r{r}")
                iv = model.NewOptionalIntervalVar(starts[p.id], p.duration, ends[p.id], b, f"iv_{p.id}_{r}")
                rooms_iv[r].append(iv)
                per_room_bools.append(b)
                model.Add(room_of[p.id] == r).OnlyEnforceIf(b)
            model.Add(sum(per_room_bools) == 1).OnlyEnforceIf(placed_bool[p.id])
            model.Add(sum(per_room_bools) == 0).OnlyEnforceIf(placed_bool[p.id].Not())

        for r in range(self.num_rooms):
            model.AddNoOverlap(rooms_iv[r])

        # maximize how many walk-ins get placed; appointments are already forced
        walkin_place_vars = [placed_bool[p.id] for p in walkins]
        model.Maximize(sum(walkin_place_vars))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2.0
        status = solver.Solve(model)

        assigned, unassigned = {}, []
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for p in all_patients:
                if solver.Value(placed_bool[p.id]):
                    assigned[p.id] = (solver.Value(room_of[p.id]), solver.Value(starts[p.id]))
                else:
                    unassigned.append(p)
        else:
            unassigned = list(walkins)
        return assigned, unassigned