from backend.emotional_genesis import emotional_context, relationship_instruction

def test_sadness_initial():
    assert emotional_context([], "I'm sad").stage == 'initial_disclosure'

def test_gentle_decline():
    assert emotional_context([{'role':'user','content':"I'm sad"}], "I don't want to talk about it").stage == 'gentle_invitation'

def test_stop_after_repeated_declines():
    history=[{'role':'user','content':x} for x in ["I'm sad", "I don't want to talk about it", "It's nothing"]]
    assert emotional_context(history,"I don't want to talk about it").stage == 'respect_decline'

def test_firm_boundary():
    assert emotional_context([], 'Stop asking me').boundary

def test_affection_requires_opt_in():
    assert 'No romantic pet names' in relationship_instruction('neutral')
    assert 'opted into' in relationship_instruction('affectionate')
