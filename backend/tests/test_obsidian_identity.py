from backend.providers import personality, EMOTIONS, MODES


def test_obsidian_never_instructs_apologies_or_emotion():
    prompt = personality('OBSIDIAN').lower()
    assert 'do not apologize' in prompt
    assert 'no simulated emotions' in prompt
    assert 'do not call yourself an instrument' in prompt
    assert 'do not pretend a chat message changed the setting' in prompt
    assert EMOTIONS['OBSIDIAN']['intensity'] == 0


def test_other_modes_remain_available():
    assert {'OBSIDIAN', 'BLOODLINE', 'ABYSS'} == set(MODES)
    assert 'execution-focused' in personality('BLOODLINE')


def test_unsupported_mode_is_rejected():
    try:
        personality('UNKNOWN')
    except ValueError:
        pass
    else:
        raise AssertionError('Unsupported mode accepted')
