from agents.negotiation import NegotiationAgent, NegotiationLearningAgent


def test_counteroffer_rejects_non_finite_and_invalid_limits():
    quote = {"commercials": {"indicative_buyer_price": 100}}
    assert NegotiationAgent().evaluate_counteroffer(quote, float("nan"))["status"] == "invalid_counteroffer"
    assert NegotiationAgent().evaluate_counteroffer(quote, 90, -1)["status"] == "invalid_discount_limit"


def test_learning_requires_minimum_sample_and_never_changes_policy():
    agent = NegotiationLearningAgent()
    assert agent.summarize([
        {"outcome": "won", "currency": "EUR", "incoterm": "FCA", "payment_terms": "advance", "accepted_unit_price": 12},
        {"outcome": "lost", "currency": "EUR", "incoterm": "FCA", "payment_terms": "advance"},
    ])["status"] == "insufficient_history"
    result = agent.summarize([
        {"outcome": "won", "currency": "EUR", "incoterm": "FCA", "payment_terms": "advance", "accepted_unit_price": 12},
        {"outcome": "won", "currency": "EUR", "incoterm": "FCA", "payment_terms": "advance", "accepted_unit_price": 10},
        {"outcome": "lost", "currency": "EUR", "incoterm": "FCA", "payment_terms": "advance"},
    ])
    assert result["segments"][0]["sample_size"] == 3
    assert result["segments"][0]["win_rate_pct"] == 66.67
    assert result["segments"][0]["average_won_unit_price"] == 11
    assert result["automatic_price_adjustment"] is False
