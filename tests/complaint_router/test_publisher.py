from app.complaint_router.publisher import publish_routing_event


def test_publish_routing_event_persists_document(patch_router_firestore):
    event_id = publish_routing_event(
        {
            "event": "complaint_assigned",
            "complaintId": "cmp_pothole",
            "officerId": "officer_road_2",
            "department": "Roads & Infrastructure",
            "priority": "urgent",
        }
    )
    assert event_id is not None
    dump = patch_router_firestore.dump()
    assert len(dump["routing_events"]) == 1
    payload = dump["routing_events"][event_id]
    assert payload["event"] == "complaint_assigned"
    assert payload["complaintId"] == "cmp_pothole"
