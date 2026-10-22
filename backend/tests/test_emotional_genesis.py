from backend.emotional_genesis import care_instruction, NORMAL_POLICY

def test_distress_invites_once():
    assert 'one open question' in care_instruction([], 'I feel sad today')

def test_soft_decline_gently_invites():
    assert 'gently invite' in care_instruction([{'role':'user','content':'I feel sad today'}], "I don't want to talk about it")

def test_repeated_declines_stop():
    history=[{'role':'user','content':x} for x in ['I feel sad today',"I don't want to talk about it", "It's nothing"]]
    assert 'Stop inviting disclosure' in care_instruction(history, "I don't want to talk about it")

def test_firm_boundary_immediate_stop():
    assert 'Do not ask again' in care_instruction([], 'Stop asking me')

def test_no_default_romance():
    assert 'Never use romantic pet names by default' in NORMAL_POLICY
