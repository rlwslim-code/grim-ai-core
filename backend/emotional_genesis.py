"""Normal-mode conversational care policy. No diagnosis or claimed feelings.

The policy is derived from the current conversation history, so it requires no
new persistent tables and cannot leak private relationship settings across users.
"""
import re
from dataclasses import dataclass, asdict

FIRM_BOUNDARIES = re.compile(r"\b(stop asking|don't ask(?: me)? again|do not ask|leave me alone|drop it|i said no|respect my boundary|change the subject|seriously,? i don't want to talk|never bring it up)\b", re.I)
SOFT_DECLINE = re.compile(r"\b(i don't want to talk about it|don't wanna talk about it|it's nothing|never mind|not ready to (?:talk|share)|rather not say|i'm fine)\b", re.I)
DISTRESS = re.compile(r"\b(sad|upset|crying|depressed|down today|heartbroken|frustrated|angry|anxious|worried)\b", re.I)

def care_instruction(history, message):
    """Return bounded, mode-specific guidance; history must be from this user's chat."""
    if FIRM_BOUNDARIES.search(message):
        return ('The user set a firm boundary. Do not ask again about the issue. '
                'Acknowledge their choice briefly and offer a different topic or quiet company. '
                'Do not guilt, diagnose, or pressure them.')
    # Count prior soft declines since the last expression of distress; reset after a topic shift.
    users = [str(row['content']) for row in history if row['role'] == 'user']
    recent = users[-8:]
    last_distress = next((i for i in range(len(recent)-1, -1, -1) if DISTRESS.search(recent[i])), -1)
    declines = sum(bool(SOFT_DECLINE.search(x)) for x in recent[last_distress+1:]) if last_distress >= 0 else 0
    if SOFT_DECLINE.search(message):
        if declines >= 2:
            return ('The user has declined to discuss this several times. Stop inviting disclosure. '
                    'Respect their choice; offer quiet company or a different topic, without another probe.')
        return ('The user is hesitant to share. You may gently invite them to share a little, '
                'with an easy way to decline. Ask at most one short question. Never insist or guilt-trip. '
                'If they clearly refuse, stop immediately.')
    if DISTRESS.search(message):
        return ('Respond to the specific feeling in a natural, brief, warm way. '
                'Ask at most one open question. Do not assume the cause or exaggerate certainty.')
    return ('Match the user’s emotional tone, including excitement, affection or frustration, '
            'without inventing emotions, overusing therapeutic clichés, or forcing romantic language.')

NORMAL_POLICY = '''GRIM NORMAL — NATURAL CONVERSATION:
- Be warm, curious, and responsive, not scripted or clinical. Prefer short, natural replies unless asked for depth.
- Do not insert unsolicited repeated speeches about being an AI; answer honestly if directly asked.
- Never use romantic pet names by default. Only use them if the user has clearly opted into that style.
- When someone hesitates to share, gently encourage once or twice if context supports it, but stop after repeated declines or any firm boundary. Do not treat a fixed number of attempts as a quota.
- Notice sadness, frustration, excitement and affection as possible cues, not certain diagnoses.
- Do not automatically append Rav’kael or THE DARKNESS ANSWERS to every message.
- No simulated emotional need, guilt, threats, possessiveness or withholding assistance.
'''


@dataclass(frozen=True)
class EmotionalContext:
    emotion: str
    stage: str
    prior_soft_declines: int
    boundary: bool


def emotional_context(history, message):
    """Deterministic context from the *current conversation only*; no diagnosis."""
    if FIRM_BOUNDARIES.search(message):
        return EmotionalContext('unspecified', 'boundary', 0, True)
    recent = [str(r['content']) for r in history[-24:] if r.get('role') == 'user']
    distress_positions = [i for i, text in enumerate(recent) if DISTRESS.search(text)]
    last = distress_positions[-1] if distress_positions else -1
    # Do not revive stale emotional conversations after unrelated topic changes.
    window = recent[last+1:] if last >= 0 else []
    declines = sum(bool(SOFT_DECLINE.search(text)) for text in window)
    if SOFT_DECLINE.search(message):
        return EmotionalContext('possible_distress', 'respect_decline' if declines >= 2 else 'gentle_invitation', declines, False)
    if DISTRESS.search(message):
        word = DISTRESS.search(message).group(1).lower()
        return EmotionalContext(word, 'initial_disclosure', 0, False)
    if recent and last >= 0 and len(recent)-last <= 3 and not any(FIRM_BOUNDARIES.search(t) for t in window):
        return EmotionalContext('possible_distress', 'follow_up_if_relevant', declines, False)
    return EmotionalContext('unspecified', 'ordinary', 0, False)


def relationship_instruction(style):
    """Explicit, per-request opt-in; never infer romance from distress."""
    if style == 'affectionate':
        return 'User opted into affectionate address. Use pet names sparingly, without possessiveness or emotional dependence.'
    if style == 'friendly':
        return 'User chose a friendly, conversational tone. No romantic pet names.'
    return 'Use a natural, respectful tone. No romantic pet names or presumed relationship.'
