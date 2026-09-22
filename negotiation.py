"""
The negotiation layer: a contract-net protocol connecting ER / Clinic
(requesters) to Surgery and ICU (resource-holding responders).

This is the piece that makes the system genuinely MULTI-agent rather than
a single script directly calling functions on four objects: every
allocation decision is the result of a request -> evaluate ->
propose/refuse -> accept exchange, fully logged, with an explicit
termination rule so negotiation can never hang forever.
"""

from models import Message, ResourceType, Patient


class NegotiationLog:
    def __init__(self):
        self.messages: list[Message] = []

    def add(self, msg: Message):
        self.messages.append(msg)

    def print_all(self):
        for m in self.messages:
            print(m.as_log_line())


class ContractNetProtocol:
    MAX_ROUNDS = 3  # termination rule: never negotiate forever

    def __init__(self, er_agent, surgery_agent, icu_agent, clinic_agent, log: NegotiationLog):
        self.er = er_agent
        self.surgery = surgery_agent
        self.icu = icu_agent
        self.clinic = clinic_agent
        self.log = log
        self.clock = 0

    def _tick(self):
        self.clock += 1
        return self.clock

    def request_or(self, requester_name: str, patient: Patient) -> bool:
        """
        Returns True only if BOTH the OR slot AND (when needed) the ICU
        recovery bed were successfully secured. An OR-only success with a
        failed ICU negotiation counts as an incomplete allocation -- a
        patient can't be considered safely placed without a guaranteed
        recovery bed.
        """
        self.log.add(Message(self._tick(), requester_name, "Surgery", "cfp",
                              ResourceType.OR_ROOM, patient, patient.acuity,
                              detail=f"requesting OR, acuity={patient.acuity}"))

        for attempt in range(1, self.MAX_ROUNDS + 1):
            can_fit, displaced, result = self.surgery.evaluate_request(patient)

            if not can_fit:
                self.log.add(Message(self._tick(), "Surgery", requester_name, "refuse",
                                      ResourceType.OR_ROOM, patient, patient.acuity,
                                      detail=f"attempt {attempt}: no feasible slot, even forced"))
                continue

            if displaced:
                for bumped_p, delay in sorted(displaced, key=lambda x: -x[1]):
                    self.log.add(Message(self._tick(), "Surgery", requester_name, "propose",
                                          ResourceType.OR_ROOM, patient, patient.acuity,
                                          detail=f"reschedule effect: {bumped_p} pushed back {delay}min "
                                                 f"(priority {patient.acuity} vs {bumped_p.acuity})"))

            start = result[patient.id][1]
            self.log.add(Message(self._tick(), "Surgery", requester_name, "propose",
                                  ResourceType.OR_ROOM, patient, patient.acuity,
                                  detail=f"proposal: start=t+{start}min"
                                         + (f" ({len(displaced)} patient(s) rescheduled)" if displaced else ", no conflicts")))

            self.surgery.commit(patient, result)
            self.log.add(Message(self._tick(), requester_name, "Surgery", "accept",
                                  ResourceType.OR_ROOM, patient, patient.acuity,
                                  detail="allocation accepted"))

            icu_ok = True
            if patient.icu_needed:
                room, start = result[patient.id]
                icu_ok = self._request_icu(requester_name, patient, earliest_start=start + patient.duration)
            return icu_ok

        self.log.add(Message(self._tick(), "Surgery", requester_name, "reject",
                              ResourceType.OR_ROOM, patient, patient.acuity,
                              detail=f"no capacity after {self.MAX_ROUNDS} rounds -- request denied"))
        return False

    def _request_icu(self, requester_name: str, patient: Patient, earliest_start: int) -> bool:
        self.log.add(Message(self._tick(), "Surgery", "ICU", "cfp",
                              ResourceType.ICU_BED, patient, patient.acuity,
                              detail=f"post-op bed needed from t+{earliest_start}min, "
                                     f"{patient.icu_duration}min"))

        result = self.icu.evaluate_request(earliest_start, patient.icu_duration)
        if result is None:
            self.log.add(Message(self._tick(), "ICU", "Surgery", "reject",
                                  ResourceType.ICU_BED, patient, patient.acuity,
                                  detail="no ICU bed available -- surgery proceeds but recovery bed is AT RISK"))
            return False

        slot, delay = result
        detail = f"bed available at t+{slot}min" if delay == 0 else \
                  f"bed available at t+{slot}min (recovery delayed {delay}min vs. ideal)"
        self.log.add(Message(self._tick(), "ICU", "Surgery", "propose",
                              ResourceType.ICU_BED, patient, patient.acuity, detail=detail))
        self.icu.commit(patient, slot, patient.icu_duration)
        self.log.add(Message(self._tick(), "Surgery", "ICU", "accept",
                              ResourceType.ICU_BED, patient, patient.acuity,
                              detail="bed reservation confirmed"))
        return True

    def run_clinic_escalations(self):
        """Clinic Agent escalates severe walk-ins to ER rather than handling them locally."""
        escalations = self.clinic.triage_walkins()
        for p in escalations:
            p.patient_type = "emergency"
            self.log.add(Message(self._tick(), "Clinic", "ER", "cfp",
                                  ResourceType.OR_ROOM, p, p.acuity,
                                  detail="walk-in severity exceeds clinic threshold -- escalating to ER"))
            self.er.receive(p)
        return escalations