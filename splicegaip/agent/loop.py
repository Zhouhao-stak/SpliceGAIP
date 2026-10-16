"""The autonomous agent loop (OODA).

``run_autonomous`` replaces the scripted team run with a real decision loop:

    observe -> verify -> decide -> act -> (record) -> repeat

Guarantees:

* **bounded** — hard caps on steps, wall-clock and error count;
* **transparent** — every step stores the action, its rationale and the
  issues that triggered it, and the whole trace lands in the workflow log;
* **offline-capable** — the decision engine is rule-based, so the agent
  self-decides even with no model configured;
* **compatible** — the result object exposes the same attributes as
  :class:`splicegaip.team.TeamRunResult`, so the pipeline is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from splicegaip.tools.context import RunContext

from .actions import build_registry
from .decision import DecisionEngine
from .episodic import EpisodicMemory
from .interactive import ConfirmationGate
from .profile import build_profile, profile_text
from .session import save_state
from .skills_bridge import SkillBridge
from .state import Goal, StepRecord, start_timer
from .state import AgentState
from .verify import issue_summary, verify_state

MAX_STEPS_DEFAULT = 20
MAX_SECONDS_DEFAULT = 900.0
MAX_ERRORS_DEFAULT = 3


@dataclass
class AgentRunResult:
    """Outcome of one autonomous run (team-compatible attributes)."""

    mode: str = "agentic"
    messages: list[dict[str, str]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stopped_reason: str = "completed"
    elapsed_seconds: float = 0.0
    #: Decision trace (what the agent did and why).
    steps: list[StepRecord] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    goal: dict[str, Any] = field(default_factory=dict)
    goal_satisfied: bool = False
    unmet_criteria: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    accepted_limitations: list[dict[str, str]] = field(default_factory=list)
    #: Pre-registered hypothesis tests (Phase 2).
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    #: External skill usage (Phase 2).
    skills: dict[str, Any] = field(default_factory=dict)
    #: Human-in-the-loop confirmations (Phase 2).
    confirmations: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "stopped_reason": self.stopped_reason,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "tool_calls": len(self.tool_calls),
            "goal": self.goal,
            "goal_satisfied": self.goal_satisfied,
            "unmet_criteria": list(self.unmet_criteria),
            "params": dict(self.params),
            "profile": dict(self.profile),
            "issues": list(self.issues),
            "accepted_limitations": list(self.accepted_limitations),
            "steps": [step.as_dict() for step in self.steps],
            "decisions": list(self.decisions),
            "hypotheses": list(self.hypotheses),
            "skills": dict(self.skills),
            "confirmations": dict(self.confirmations),
        }


def _agent_settings(settings: Any) -> Any:
    """Return the ``agent`` config block (or a default-like namespace)."""
    block = getattr(settings, "agent", None)
    if block is not None:
        return block

    class _Defaults:
        max_steps = MAX_STEPS_DEFAULT
        max_seconds = MAX_SECONDS_DEFAULT
        max_errors = MAX_ERRORS_DEFAULT
        adaptive_thresholds = True
        target_significant = 100
        reflection = True
        llm_advisory = True
        episodic = True
        autonomy = "auto"
        hypothesis_testing = True

        class skills:  # noqa: N801 - minimal namespace mirroring SkillSettings
            enabled = False
            max_calls = 0
            timeout = 10.0

    return _Defaults()


def _build_goal(context: RunContext) -> Goal:
    """Derive the goal from the query (and the pre-run intent, if present)."""
    from splicegaip.agents.policy import classify_query

    analysis_type, description = classify_query(context.query)
    understanding = getattr(context, "understanding", None)
    if isinstance(understanding, dict):
        resolved = str(understanding.get("analysis_type") or "").strip()
        if resolved:
            analysis_type = resolved
        goal_text = str(understanding.get("goal") or "").strip()
        if goal_text:
            description = goal_text
    return Goal(analysis_type=analysis_type, description=description)


class AutonomousAgent:
    """Runs the observe-decide-act-verify loop for one analysis."""

    def __init__(
        self,
        context: RunContext,
        settings: Any | None = None,
        *,
        confirm_handler: Any | None = None,
        state: AgentState | None = None,
        followup: list[tuple[str, dict[str, Any]]] | None = None,
    ) -> None:
        self.context = context
        self.settings = settings or context.settings
        self.config = _agent_settings(self.settings)
        self.registry = build_registry()
        # A provided ``state`` means we are *resuming* a prior run: keep its
        # blackboard and skip the first-observation seed/sense steps.
        self.resuming = state is not None
        self.state = state if state is not None else AgentState(
            context=context, goal=_build_goal(context)
        )
        self.followup = list(followup or [])
        self.result = AgentRunResult(mode="agentic")
        #: Budgeted bridge to the async external skills (Phase 2).
        self.bridge = SkillBridge.from_settings(self.settings)
        self.state.bridge = self.bridge
        #: Human-in-the-loop gate (``autonomy: assisted``).
        self.gate = ConfirmationGate.from_settings(self.settings, handler=confirm_handler)

    # -- setup ------------------------------------------------------------
    def _seed_params(self) -> None:
        analysis = self.context.settings.analysis
        self.state.params.update(
            {
                "fdr": analysis.fdr_threshold,
                "delta_psi": analysis.delta_psi_threshold,
                "top_n": analysis.top_candidates,
                "strategy": "configured",
            }
        )

    def _sense(self) -> None:
        """First observation: profile the dataset before any decision."""
        context = self.context
        state = self.state
        state.profile = build_profile(context)
        state.observe()
        text = profile_text(state.profile)
        state.steps.append(
            StepRecord(
                index=len(state.steps),
                action="profile_dataset",
                args={},
                status="ok",
                message=text,
                rationale="Sense the dataset before deciding anything.",
                source="rule",
                seconds=0.0,
            )
        )
        state.note_action("profile_dataset")
        context.log("agent", "profile_dataset", "ok", text[:400])
        self.result.tool_calls.append({"agent": "autonomous", "tool": "profile_dataset", "result": text})

    def _load_experience(self) -> None:
        if not getattr(self.config, "episodic", True):
            return
        memory = EpisodicMemory(self.context.settings.paths.memory_db)
        if not memory.ensure():
            return
        hint = memory.suggest_params(
            self.context.dataset.source_format, len(self.context.dataset.events)
        )
        if hint:
            self.state.facts["episodic_hint"] = hint
            self.context.log(
                "agent",
                "episodic_hint",
                "ok",
                f"Previous comparable run used {hint}; it will bias threshold selection.",
            )
        self._memory = memory

    # -- execution --------------------------------------------------------
    def _run_followup_step(self, action_name: str, args: dict[str, Any], elapsed: Any) -> None:
        """Execute one follow-up action as a traceable step."""
        state = self.state
        started = elapsed()
        status, message = self._execute(action_name, args)
        state.steps.append(
            StepRecord(
                index=len(state.steps),
                action=action_name,
                args=dict(args),
                status=status,
                message=message,
                rationale="Follow-up request.",
                source="followup",
                seconds=max(elapsed() - started, 0.0),
                issues=[issue.code for issue in state.blockers()],
            )
        )
        state.note_action(action_name)
        self.context.log("agent", action_name, status, f"[followup] {message[:300]}")

    def _persist(self) -> None:
        """Snapshot the decision state for a future follow-up (best-effort)."""
        try:
            if self.context.output_dir is not None:
                save_state(self.state, self.context.output_dir)
        except Exception as error:  # noqa: BLE001 - persistence must never break a run
            self.context.log("agent", "save_state", "warning", str(error)[:200])

    def _execute(self, name: str, args: dict[str, Any]) -> tuple[str, str]:
        action = self.registry.get(name)
        if action is None:
            return "error", f"Unknown action: {name}"
        missing = [fact for fact in action.requires if not self.state.facts.get(fact)]
        if missing:
            return "skipped", f"Preconditions not met for {name}: missing {', '.join(missing)}"
        try:
            message = action.func(self.context, self.state, **args)
        except Exception as error:  # noqa: BLE001 - one broken action must not kill the run
            return "error", f"{name} failed: {error}"
        return "ok", str(message or "")

    def run(self) -> AgentRunResult:
        context = self.context
        state = self.state
        result = self.result
        elapsed = start_timer()

        if not self.resuming:
            self._seed_params()
            self._sense()
        else:
            # Resume: the blackboard is already populated; just refresh facts.
            state.observe()
        self._load_experience()

        # Follow-up intent runs as a short prefix before the normal loop
        # re-satisfies the tail criteria (interpret + report).
        for action_name, args in self.followup:
            self._run_followup_step(action_name, args, elapsed)

        engine = DecisionEngine(
            state,
            self.settings,
            llm_advisory=bool(getattr(self.config, "llm_advisory", True)),
            gate=self.gate,
        )
        errors = 0
        while len(state.steps) < int(getattr(self.config, "max_steps", MAX_STEPS_DEFAULT)):
            if elapsed() > float(getattr(self.config, "max_seconds", MAX_SECONDS_DEFAULT)):
                result.stopped_reason = "time budget exhausted"
                break
            state.iteration += 1
            state.observe()
            verify_state(state)

            decision = engine.decide()
            result.decisions.append(decision.as_dict())
            if decision.kind == "stop" or decision.action is None:
                result.stopped_reason = decision.rationale or "agent decided to stop"
                break

            started = elapsed()
            status, message = self._execute(decision.action, decision.args)
            if status == "error":
                errors += 1
            step = StepRecord(
                index=len(state.steps),
                action=decision.action,
                args=dict(decision.args),
                status=status,
                message=message,
                rationale=decision.rationale,
                source=decision.source,
                seconds=max(elapsed() - started, 0.0),
                issues=[issue.code for issue in state.blockers()],
            )
            state.steps.append(step)
            state.note_action(decision.action)
            result.tool_calls.append(
                {
                    "agent": "autonomous",
                    "tool": decision.action,
                    "arguments": str(decision.args),
                    "result": message[:500],
                }
            )
            context.log(
                "agent",
                decision.action,
                status,
                f"[{decision.source}] {decision.rationale} :: {message[:300]}",
            )
            if decision.action == "filter_significant_events" and status == "ok":
                state.facts["filtered_with"] = {
                    "fdr": state.params.get("fdr"),
                    "delta_psi": state.params.get("delta_psi"),
                }
            memory = getattr(self, "_memory", None)
            if memory is not None:
                memory.record(
                    project_id=context.project_id,
                    source_format=context.dataset.source_format,
                    event_count=len(context.dataset.events),
                    action=decision.action,
                    args=decision.args,
                    status=status,
                    message=message,
                    significant=len(context.significant_events),
                    params=dict(state.params),
                )
            if errors >= int(getattr(self.config, "max_errors", MAX_ERRORS_DEFAULT)):
                result.stopped_reason = f"error budget exhausted ({errors} failures)"
                break
        else:
            result.stopped_reason = f"step budget exhausted ({len(state.steps)} steps)"

        # Safety net: never leave a run without a report.
        state.observe()
        if not state.facts.get("reported"):
            status, message = self._execute("generate_report", {})
            state.steps.append(
                StepRecord(
                    index=len(state.steps),
                    action="generate_report",
                    args={},
                    status=status,
                    message=message,
                    rationale="Safety net: a run must end with a report.",
                    source="safety_net",
                    seconds=0.0,
                )
            )
            context.log("agent", "generate_report", status, "safety net :: " + message[:200])

        result = self._finalize(elapsed())
        self._persist()
        return result

    # -- finalize ---------------------------------------------------------
    def _finalize(self, seconds: float) -> AgentRunResult:
        state = self.state
        context = self.context
        result = self.result
        state.observe()
        verify_state(state)
        satisfied, unmet = state.goal.evaluate(state)

        result.elapsed_seconds = seconds
        result.steps = list(state.steps)
        result.issues = [issue.as_dict() for issue in state.sorted_issues()]
        result.goal = state.goal.as_dict()
        result.goal_satisfied = satisfied
        result.unmet_criteria = unmet
        result.params = dict(state.params)
        result.profile = dict(state.profile)
        result.accepted_limitations = list(state.facts.get("accepted_limitations", []))

        # Step 3: persist top candidates into lab knowledge base and prepare for report
        if state.facts.get("interpreted") and not state.facts.get("knowledge_persisted"):
            try:
                from .actions import consult_knowledge, persist_knowledge
                
                # First consult the knowledge base
                consult_msg = consult_knowledge(context, state, min_projects=2)
                
                # Then persist current run's top candidates
                persist_knowledge(context, state, top_n=10)
                
                # Store recurrent genes in context.external for the report
                recurrent = state.facts.get("recurrent_genes", [])
                if recurrent:
                    context.external["recurrent_genes"] = recurrent
                
                state.facts["knowledge_persisted"] = True
            except Exception:  # noqa: BLE001 - best effort, never crash the run
                pass

        # Phase 2 payloads: what the agent tested, which external services it
        # used, and every decision a human was asked to confirm.
        result.hypotheses = [item.as_dict() for item in context.hypotheses]
        result.skills = self.bridge.as_dict()
        result.confirmations = self.gate.as_dict()
        result.messages = [
            {
                "source": "autonomous_agent",
                "content": (
                    f"goal={state.goal.description}; satisfied={satisfied}; "
                    f"steps={len(state.steps)}; issues={issue_summary(state.issues)}; "
                    f"params={state.params}"
                ),
            }
        ]

        # The report methods section and the API both read ``context.plan``.
        context.plan = {
            "goal": state.goal.description,
            "analysis_type": state.goal.analysis_type,
            "generated_by": "SpliceGAIP autonomous agent",
            "workflow": [
                {
                    "step": step.index + 1,
                    "agent": "autonomous_agent",
                    "action": step.action,
                    "rationale": step.rationale,
                    "source": step.source,
                    "status": step.status,
                }
                for step in state.steps
            ],
            "required_files": [str(context.dataset.source_dir)],
            "expected_outputs": [
                "dataset profile",
                "filtered significant events",
                "ranked candidates",
                "figures",
                "HTML/PDF report",
            ],
            "parameters": dict(state.params),
            "potential_limitations": [
                issue.message for issue in state.sorted_issues() if issue.severity in {"blocker", "warning"}
            ]
            + [
                item.interpretation
                for item in context.hypotheses
                if item.verdict == "rejected"
                and item.code in {"coverage_confound", "event_type_bias"}
            ]
            or ["none identified"],
            "accepted_limitations": result.accepted_limitations,
            "hypothesis_tests": result.hypotheses,
            "external_skills": self.bridge.summary_line(),
            "human_confirmations": self.gate.summary_line(),
        }
        if hasattr(context.memory, "save_plan"):
            try:
                context.memory.save_plan(context.project_id, context.plan)
            except Exception:  # noqa: BLE001
                pass
        context.log(
            "agent",
            "run_finished",
            "ok" if satisfied else "warning",
            f"satisfied={satisfied} unmet={unmet} steps={len(state.steps)} reason={result.stopped_reason}",
        )
        return result


def run_autonomous(
    context: RunContext,
    settings: Any | None = None,
    *,
    confirm_handler: Any | None = None,
    state: AgentState | None = None,
    followup: list[tuple[str, dict[str, Any]]] | None = None,
) -> AgentRunResult:
    """Run the autonomous agent for ``context`` (synchronous entry point).

    ``confirm_handler`` is called with a
    :class:`~splicegaip.agent.interactive.PendingDecision` whenever
    ``autonomy: assisted`` needs a human answer. ``state`` + ``followup`` are
    used to *resume* a prior run with a follow-up intent (see
    :mod:`splicegaip.agent.session`).
    """
    return AutonomousAgent(
        context,
        settings,
        confirm_handler=confirm_handler,
        state=state,
        followup=followup,
    ).run()
