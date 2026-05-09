from app.complaint_router.routing_engine import generate_routing_decision


def test_routing_priority_mapping_critical():
    decision = generate_routing_decision(department="Disaster Management", severity="critical")
    assert decision.priority == "emergency"
    assert decision.urgency == "immediate"
    assert decision.dispatchLevel == "rapid-response"
    assert decision.isEmergency is True


def test_routing_priority_mapping_high():
    decision = generate_routing_decision(department="Roads & Infrastructure", severity="high")
    assert decision.priority == "urgent"
    assert decision.urgency == "same-day"


def test_routing_priority_mapping_low_default():
    decision = generate_routing_decision(department="Manual Review", severity="unknown")
    assert decision.priority == "low"
    assert decision.urgency == "72-hours"
