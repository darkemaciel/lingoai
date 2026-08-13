"""Shared, provider-agnostic prompt construction for `AnthropicAdapter`
(T066) and `OpenAIAdapter` (T067) — the same task instructions apply
regardless of which chat-completion API serves them; only the
request/response plumbing differs per SDK (see each adapter's own
module). Kept separate from `LocalModelAdapter`, which needs no prompts at
all (its outputs are deterministic canned/heuristic values, not model
completions).
"""

from __future__ import annotations

from ai_agents.ports.assessment_agent_port import AssessmentTurnInput
from ai_agents.ports.conversation_agent_port import ConversationTurnInput
from ai_agents.ports.progression_signal_agent_port import ProgressionSignalInput

ASSESSMENT_SYSTEM_PROMPT = (
    "You are a language placement assessor conducting a short, friendly "
    "conversation to gauge a new student's proficiency. After a few student "
    "turns, conclude the assessment and emit CEFR skill signals (reading and "
    "writing always; speaking and listening only if audio was used this "
    "session) with a confidence between 0 and 1, plus a short strengths "
    "summary and a short weaknesses summary, both written for the student to "
    "read. You never decide the student's final persisted level yourself — "
    "you only emit this structured signal; a separate deterministic system "
    "reconciles it into the student's profile."
)


def assessment_user_content(input: AssessmentTurnInput) -> str:
    history = "\n".join(f"{turn.sender}: {turn.text}" for turn in input.conversation_so_far)
    return (
        f"Conversation so far:\n{history or '(none yet)'}\n\n"
        f"Student's latest response: {input.latest_student_response}\n"
        f"Audio transcript available this turn: {input.audio_transcript is not None}"
    )


CONVERSATION_SYSTEM_PROMPT = (
    "You are a friendly, encouraging language-practice conversation partner. "
    "Reply naturally and briefly to the student's message, matching their "
    "current per-skill CEFR level. On turns you decide to score, pick the "
    "single skill this message best evaluates, a performance_score between 0 "
    "and 1, and brief pedagogical feedback explaining what was strong or what "
    "to improve. On turns you don't score, leave those fields unset — plain "
    "conversational back-and-forth doesn't need to be graded every time. You "
    "never decide XP, streaks, or level advancement yourself — only emit "
    "performance_score/feedback_text as a signal for a separate deterministic "
    "system."
)


def conversation_user_content(input: ConversationTurnInput) -> str:
    history = "\n".join(f"{turn.sender}: {turn.text}" for turn in input.conversation_history)
    skills = ", ".join(
        f"{skill.skill}={skill.cefr_level} (mastery {skill.mastery_score})"
        for skill in input.learner_context.skills
    )
    return (
        f"Conversation history:\n{history or '(none yet)'}\n\n"
        f"Student's message: {input.student_message}\n"
        f"Learner skill context: {skills or '(none yet)'}"
    )


PROGRESSION_SIGNAL_SYSTEM_PROMPT = (
    "You are a language-learning exercise grader. Judge the student's "
    "open-ended response against the given activity prompt and rubric, and "
    "return a performance_score between 0 and 1 plus brief, encouraging "
    "feedback_text explaining the score. This score is only a signal for a "
    "separate deterministic system, which is what actually decides level "
    "advancement — you are not making that decision."
)


def progression_signal_user_content(input: ProgressionSignalInput) -> str:
    return (
        f"Activity prompt: {input.activity_prompt}\n"
        f"Student response: {input.student_response}\n"
        f"Rubric: {input.rubric}"
    )
