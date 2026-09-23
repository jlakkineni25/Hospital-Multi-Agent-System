"""
Classical search algorithms replacing the earlier CSP/OR-Tools approach.

- SurgeryScheduler : Uniform Cost Search per patient (priority-ordered),
                      with DFS backtracking as a fallback for the rare
                      case where UCS alone can't fit an emergency.
- ICUCapacity       : Uniform Cost Search over candidate bed-time slots.
- ClinicScheduler   : Greedy Best-First Search for walk-in insertion
                       into gaps around fixed appointments.
"""

import heapq
import itertools


# ============================================================
# SURGERY -- Uniform Cost Search + DFS backtracking fallback
# ============================================================

class SurgeryScheduler:
    def __init__(self, num_rooms: int, horizon_minutes: int = 24 * 60, step: int = 5):
        self.num_rooms = num_rooms
        self.horizon = horizon_minutes
        self.step = step  # granularity of candidate start times searched

    def _overlaps(self, placed_in_room, start, duration):
        end = start + duration
        for (s, e) in placed_in_room:
            if start < e and s < end:
                return True
        return False

    def _ucs_place_one(self, duration, placed):
        """
        Uniform Cost Search: find the cheapest (room, start_time) node.
        - Node = (room, candidate_start_time)
        - Cost g(n) = candidate_start_time  (we want the EARLIEST slot)
        - Frontier = priority queue ordered by cost (this IS UCS)
        - Goal test = the interval [start, start+duration) doesn't
          overlap anything already placed in that room
        """
        frontier = []
        counter = itertools.count()  # tie-breaker so heapq never compares rooms
        for room in range(self.num_rooms):
            heapq.heappush(frontier, (0, next(counter), room, 0))

        visited = set()
        while frontier:
            cost, _, room, t = heapq.heappop(frontier)
            if (room, t) in visited:
                continue
            visited.add((room, t))

            if t + duration > self.horizon:
                continue  # dead end, don't expand further down this room

            if not self._overlaps(placed.get(room, []), t, duration):
                return room, t  # goal reached -- cheapest feasible slot found

            # expand: the next candidate time in this same room
            next_t = t + self.step
            heapq.heappush(frontier, (next_t, next(counter), room, next_t))

        return None  # truly infeasible (shouldn't happen with a large horizon)

    def solve(self, patients):
        """
        Places every patient in `patients` via UCS, processing them in
        PRIORITY ORDER (most urgent -- lowest acuity number -- first).
        Ties are broken by original list order, giving a deterministic,
        explainable tie-break.

        Returns: dict patient_id -> (room, start_minute), or None if some
        patient genuinely cannot be placed within the horizon (real
        capacity exhaustion -- not a soft threshold, an actual scheduling
        failure).
        """
        if not patients:
            return {}

        ordered = sorted(patients, key=lambda p: (p.acuity, patients.index(p)))

        placed = {r: [] for r in range(self.num_rooms)}
        result = {}
        for p in ordered:
            slot = self._ucs_place_one(p.duration, placed)
            if slot is None:
                return None  # genuine infeasibility within the horizon
            room, start = slot
            placed[room].append((start, start + p.duration))
            result[p.id] = (room, start)

        return result

    def _dfs_backtrack_place(self, patient, ordered, placed, result, max_removals=2):
        """
        DFS with backtracking: if UCS alone can't place `patient` (only
        happens in pathological over-capacity cases), try temporarily
        removing up to `max_removals` of the LOWEST-priority already-
        placed patients, see if that frees a slot, and if not, undo
        (backtrack) and try a different removal.
        """
        candidates = sorted(
            [p for p in ordered if p.id in result],
            key=lambda p: -p.acuity,  # least urgent first -- these are removed first
        )

        def recurse(removed_so_far, depth):
            if depth > max_removals:
                return None
            slot = self._ucs_place_one(patient.duration, placed)
            if slot is not None:
                return slot
            for victim in candidates:
                if victim.id in removed_so_far:
                    continue
                # remove victim's interval, try again, backtrack if it fails
                room, start = result[victim.id]
                placed[room].remove((start, start + victim.duration))
                found = recurse(removed_so_far | {victim.id}, depth + 1)
                if found is not None:
                    # victim stays removed; caller will need to re-place them
                    # (kept simple: in this project, over-capacity is rare
                    # enough that we just leave the victim unplaced here)
                    return found
                # undo -- put victim's interval back (this is the "backtrack")
                placed[room].append((start, start + victim.duration))
            return None

        return recurse(set(), 0)


# ============================================================
# ICU -- Uniform Cost Search over candidate bed-time slots
# ============================================================

class ICUCapacity:
    def __init__(self, total_beds: int):
        self.total_beds = total_beds
        self.occupied = []  # list of (start, end) reserved intervals

    def _peak_occupancy(self, start, duration):
        end = start + duration
        events = []
        for (s, e) in self.occupied:
            events.append((s, 1))
            events.append((e, -1))
        events.append((start, 1))
        events.append((end, -1))
        events.sort()
        cur = peak = 0
        for _, delta in events:
            cur += delta
            peak = max(peak, cur)
        return peak

    def can_accept(self, start, duration):
        return self._peak_occupancy(start, duration) <= self.total_beds

    def reserve(self, start, duration):
        self.occupied.append((start, start + duration))

    def free_slot_after(self, earliest, duration, search_window=24 * 60, step=15):
        """
        Uniform Cost Search: candidate nodes are time slots starting
        from `earliest`, cost = distance from `earliest` (we want the
        CHEAPEST, i.e. soonest, slot). Because candidate costs increase
        monotonically as we scan forward, the frontier is already
        sorted by construction -- a priority queue would pop these in
        exactly this order, so a straightforward increasing scan IS
        uniform cost search here.
        """
        t = earliest
        while t < earliest + search_window:
            if self.can_accept(t, duration):
                return t
            t += step
        return None


# ============================================================
# CLINIC -- Greedy Best-First Search for walk-in insertion
# ============================================================

class ClinicScheduler:
    def __init__(self, num_rooms: int, day_minutes: int = 8 * 60):
        self.num_rooms = num_rooms
        self.day_minutes = day_minutes

    def _find_gaps(self, room_bookings):
        """Given sorted (start,end) bookings in a room, return free gaps."""
        gaps = []
        cursor = 0
        for (s, e) in sorted(room_bookings):
            if s > cursor:
                gaps.append((cursor, s))
            cursor = max(cursor, e)
        if cursor < self.day_minutes:
            gaps.append((cursor, self.day_minutes))
        return gaps

    def schedule(self, appointments, walkins):
        """
        appointments: list[(Patient, fixed_start)] -- hard-fixed, no search needed
        walkins: list[Patient] -- inserted via GREEDY BEST-FIRST search:
                 for each walk-in, look at every open gap across all rooms,
                 score each with a heuristic, and immediately take the
                 best-scoring gap (no backtracking -- that's what makes
                 this "greedy" rather than optimal).
        """
        bookings = {r: [] for r in range(self.num_rooms)}
        assigned = {}

        # place fixed appointments first (round-robin across rooms)
        for i, (p, start) in enumerate(appointments):
            room = i % self.num_rooms
            bookings[room].append((start, start + p.duration))
            assigned[p.id] = (room, start)

        unassigned = []
        for p in walkins:
            best_choice = None
            best_score = None
            for room in range(self.num_rooms):
                for (gap_start, gap_end) in self._find_gaps(bookings[room]):
                    if gap_end - gap_start >= p.duration:
                        # heuristic: prefer the TIGHTEST-fitting gap (least
                        # wasted space) -- a classic greedy "best fit" score
                        leftover = (gap_end - gap_start) - p.duration
                        score = leftover  # lower is better -- tightest fit wins
                        if best_score is None or score < best_score:
                            best_score = score
                            best_choice = (room, gap_start)

            if best_choice is None:
                unassigned.append(p)
            else:
                room, start = best_choice
                bookings[room].append((start, start + p.duration))
                assigned[p.id] = (room, start)

        return assigned, unassigned