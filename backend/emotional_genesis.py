"""Normal-mode conversational care policy. No diagnosis or claimed feelings.

The policy is derived from the current conversation history, so it requires no
new persistent tables and cannot leak private relationship settings across users.
"""
import re

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
