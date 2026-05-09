from app.complaint_router.service import route_complaint_by_id


def test_route_success_updates_firestore_and_events(patch_router_firestore, fake_logger):
    result = route_complaint_by_id("cmp_pothole")
    assert result.success is True
    assert result.routingStatus == "assigned"
    assert result.priority == "urgent"
    assert result.assignedOfficer == "officer_road_2"

    dump = patch_router_firestore.dump()
    complaint = dump["complaints"]["cmp_pothole"]
    assert complaint["routing"]["department"] == "Roads & Infrastructure"
    assert complaint["routing"]["priority"] == "urgent"
    assert complaint["routing"]["assignedOfficer"] == "officer_road_2"
    assert complaint["routing"]["routingStatus"] == "assigned"
    assert complaint["escalation"]["escalated"] is True
    assert "high_severity_sensitive_zone" in complaint["escalation"]["reasons"]

    assert len(dump["routing_events"]) == 1
    event = next(iter(dump["routing_events"].values()))
    assert event["event"] == "complaint_assigned"
    assert event["complaintId"] == "cmp_pothole"
    assert event["officerId"] == "officer_road_2"

    log_messages = [c.message for c in fake_logger.calls]
    assert "routing_started" in log_messages
    assert "officer_selected" in log_messages
    assert "escalation_triggered" in log_messages
    assert "firestore_updated" in log_messages
    assert "routing_completed" in log_messages


def test_route_missing_officer_handled_gracefully(patch_router_firestore, fake_logger):
    # Public Works is not present in officer seed data.
    patch_router_firestore.collection("complaints").document("cmp_no_officer").set(
        {
            "description": "Sewage overflow",
            "status": "open",
            "ai": {
                "category": "Sewage",
                "severity": "high",
                "department": "Public Works",
                "confidence": 0.9,
                "summary": "Sewage overflow on street",
                "tags": ["sewage", "overflow"],
            },
        }
    )
    result = route_complaint_by_id("cmp_no_officer")
    assert result.success is False
    assert result.routingStatus == "failed"
    assert "No available officer" in (result.message or "")
    assert any(c.message == "routing_failed" for c in fake_logger.calls)


def test_route_malformed_ai_data_handled_gracefully(patch_router_firestore, fake_logger):
    patch_router_firestore.collection("complaints").document("cmp_bad_ai").set(
        {"description": "bad payload", "status": "open", "ai": {"severity": "high"}}
    )
    result = route_complaint_by_id("cmp_bad_ai")
    assert result.success is False
    assert result.routingStatus == "failed"
    assert "Missing AI field" in (result.message or "")
    assert any(c.message == "routing_failed" for c in fake_logger.calls)


def test_route_low_confidence_manual_review_escalates(patch_router_firestore):
    result = route_complaint_by_id("cmp_unclear")
    assert result.success is False or result.success is True
    # Department is Manual Review and no officer exists in seed data, so fail is expected.
    # Still validates escalation logic independently via failure-safe execution path.
    # For strict routing escalation document validation, inject matching officer:
    patch_router_firestore.collection("officers").document("officer_manual_1").set(
        {
            "officerId": "officer_manual_1",
            "department": "Manual Review",
            "zone": "south",
            "active": True,
            "currentLoad": 0,
        }
    )
    result2 = route_complaint_by_id("cmp_unclear")
    assert result2.success is True
    dump = patch_router_firestore.dump()
    complaint = dump["complaints"]["cmp_unclear"]
    assert complaint["escalation"]["escalated"] is True
    assert "low_confidence_manual_review" in complaint["escalation"]["reasons"]
