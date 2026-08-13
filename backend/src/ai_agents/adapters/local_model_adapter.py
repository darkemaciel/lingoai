"""Deterministic, network-free stand-in for a real LLM-backed agent adapter.

Per research.md §1 and §9: ``LocalModelAdapter`` backs local dev and CI when
no external provider key is configured, and is the adapter used by default
in unit/contract tests (NFR-7) so those tests never depend on network
access, API keys, or non-reproducible model output. All behavior below is a
pure function of its input (turn counts, message content, simple keyword
checks) — there is no hidden mutable state and no call to any external
service.

This is explicitly a **deterministic stand-in, not real NLP/LLM judgment**.
The heuristics exist only to produce varied-but-reproducible outputs so
downstream code (and its tests) can exercise every branch of the contract
shape (``is_complete=True/False``, ``scored=True/False``,
``performance_score`` across a range) without a live model.

``LocalModelAdapter`` implements all three agent ports
(``AssessmentAgentPort``, ``ConversationAgentPort``,
``ProgressionSignalAgentPort``) as one class, since it is a single
deterministic mock backend, not three independently swappable providers.
Method names are distinct per port (``process_turn`` /
``process_message`` / ``evaluate``) precisely so one class can satisfy all
three Protocols without a same-name/different-signature collision.
"""

from ai_agents.ports.assessment_agent_port import (
    AssessmentTurnInput,
    AssessmentTurnOutput,
    SkillSignal,
    SkillSignals,
)
from ai_agents.ports.conversation_agent_port import (
    ConversationTurnInput,
    ConversationTurnOutput,
)
from ai_agents.ports.progression_signal_agent_port import (
    ProgressionSignalInput,
    ProgressionSignalOutput,
)

# Number of student responses collected before a placement session is
# considered complete. Kept as a small named constant (not a magic number)
# per Constitution §5/§6 guidance to make tunable thresholds explicit.
ASSESSMENT_TURNS_BEFORE_COMPLETE = 3

_CANNED_ASSESSMENT_PROMPTS = [
    "Tell me a bit about yourself and why you're learning this language.",
    "Describe your daily routine in a few sentences.",
    "What did you do last weekend? Tell me about it.",
]

_CANNED_CONVERSATION_REPLIES = [
    "That's interesting — can you tell me more about that?",
    "Great, I understand. Let's keep going!",
    "Nice! What happened next?",
]


class LocalModelAdapter:
    """Deterministic implementation of all three agent ports."""

    # ------------------------------------------------------------------
    # AssessmentAgentPort
    # ------------------------------------------------------------------
    async def process_turn(self, input: AssessmentTurnInput) -> AssessmentTurnOutput:
        """Advance a placement conversation by one turn.

        Deterministic rule: count how many student turns have occurred so
        far (turns already in ``conversation_so_far`` with
        ``sender="student"``, plus the current ``latest_student_response``
        itself). Once that count reaches ``ASSESSMENT_TURNS_BEFORE_COMPLETE``,
        the session is marked complete and canned but plausible
        ``skill_signals`` are returned. Otherwise a canned next prompt is
        returned, cycling through ``_CANNED_ASSESSMENT_PROMPTS`` by turn
        index.
        """
        prior_student_turns = sum(
            1 for turn in input.conversation_so_far if turn.sender == "student"
        )
        # +1 for the latest_student_response, which represents the turn
        # just submitted and is not yet reflected in conversation_so_far.
        student_turns_so_far = prior_student_turns + 1

        if student_turns_so_far >= ASSESSMENT_TURNS_BEFORE_COMPLETE:
            has_audio = input.audio_transcript is not None
            return AssessmentTurnOutput(
                next_prompt_text=None,
                is_complete=True,
                skill_signals=SkillSignals(
                    reading=SkillSignal(cefr_level="B1", confidence=0.7),
                    writing=SkillSignal(cefr_level="B1", confidence=0.7),
                    speaking=SkillSignal(cefr_level="B1", confidence=0.65) if has_audio else None,
                    listening=SkillSignal(cefr_level="B1", confidence=0.65) if has_audio else None,
                ),
                strengths_summary=(
                    "Consistent use of basic vocabulary and correct simple-sentence structure."
                ),
                weaknesses_summary=(
                    "Limited range of verb tenses; would benefit from more complex sentence practice."
                ),
            )

        prompt_index = min(prior_student_turns, len(_CANNED_ASSESSMENT_PROMPTS) - 1)
        return AssessmentTurnOutput(
            next_prompt_text=_CANNED_ASSESSMENT_PROMPTS[prompt_index],
            is_complete=False,
            skill_signals=None,
            strengths_summary=None,
            weaknesses_summary=None,
        )

    # ------------------------------------------------------------------
    # ConversationAgentPort
    # ------------------------------------------------------------------
    async def process_message(self, input: ConversationTurnInput) -> ConversationTurnOutput:
        """Produce a reply to one learning-loop conversation turn.

        Deterministic rules (stand-ins for real NLP, not real judgment):
        - ``scored``: True on every 2nd turn (even count of prior history
          entries), so tests can assert both branches deterministically
          from input shape alone.
        - ``performance_score`` (only when ``scored``): a simple
          keyword/length heuristic — an apologetic ("sorry") or very short
          (< 3 words) student message scores low (0.4); otherwise it
          scores high (0.85).
        - ``skill``: the first skill in ``learner_context.skills`` if any
          is present, else ``"conversation"``.
        """
        reply_index = len(input.conversation_history) % len(_CANNED_CONVERSATION_REPLIES)
        reply_text = _CANNED_CONVERSATION_REPLIES[reply_index]

        scored = len(input.conversation_history) % 2 == 0
        if not scored:
            return ConversationTurnOutput(
                reply_text=reply_text,
                scored=False,
                skill=None,
                performance_score=None,
                feedback_text=None,
            )

        words = input.student_message.strip().split()
        is_weak_response = "sorry" in input.student_message.lower() or len(words) < 3
        performance_score = 0.4 if is_weak_response else 0.85

        skill = (
            input.learner_context.skills[0].skill
            if input.learner_context.skills
            else "conversation"
        )

        feedback_text = (
            "Don't worry — try expanding your answer a bit more next time."
            if is_weak_response
            else "Well expressed! Your sentence structure was clear and accurate."
        )

        return ConversationTurnOutput(
            reply_text=reply_text,
            scored=True,
            skill=skill,
            performance_score=performance_score,
            feedback_text=feedback_text,
        )

    # ------------------------------------------------------------------
    # ProgressionSignalAgentPort
    # ------------------------------------------------------------------
    async def evaluate(self, input: ProgressionSignalInput) -> ProgressionSignalOutput:
        """Judge one open-ended student response against its rubric.

        Deterministic stand-in, not real NLP: if ``rubric`` contains a
        ``"keywords"`` list, ``performance_score`` is the fraction of
        those keywords (case-insensitive) that appear anywhere in
        ``student_response``. Otherwise, it falls back to a length-ratio
        heuristic: ``len(student_response.split()) / rubric.get(
        "expected_min_words", 5)``, clamped to ``[0, 1]``. Either way the
        result is a pure function of the input, so it is reproducible in
        tests without any real language judgment.
        """
        keywords = input.rubric.get("keywords") if isinstance(input.rubric, dict) else None
        response_lower = input.student_response.lower()

        if keywords:
            matched = sum(1 for kw in keywords if str(kw).lower() in response_lower)
            performance_score = matched / len(keywords)
        else:
            expected_min_words = (
                input.rubric.get("expected_min_words", 5) if isinstance(input.rubric, dict) else 5
            )
            word_count = len(input.student_response.split())
            performance_score = word_count / expected_min_words if expected_min_words else 0.0

        performance_score = max(0.0, min(1.0, performance_score))

        if performance_score >= 0.8:
            feedback_text = "Excellent response — you covered the key points clearly."
        elif performance_score >= 0.4:
            feedback_text = "Good attempt — you covered some key points, but could add more detail."
        else:
            feedback_text = "Let's revisit this — try to address the prompt more directly."

        return ProgressionSignalOutput(
            performance_score=performance_score,
            feedback_text=feedback_text,
        )
