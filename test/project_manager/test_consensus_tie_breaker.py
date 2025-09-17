from src.task_manager.consensus import ConsensusCalculator, ValidationInput


def test_tie_breaker_returns_partial_on_exact_tie():
    calc = ConsensusCalculator(model_weights={
        'claude-3-5-sonnet': 1.0,
        'gpt-4': 1.0,
        'default': 1.0,
    }, use_cache=False)

    validations = [
        ValidationInput(validator_id='claude-3-5-sonnet', outcome='validated', confidence=80),
        ValidationInput(validator_id='gpt-4', outcome='rejected', confidence=80),
    ]

    result = calc.calculate_consensus(validations)
    assert result.outcome == 'partial'
    assert result.agreement_level in ('weak', 'moderate', 'strong', 'unanimous')
