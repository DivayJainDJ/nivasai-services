from app.complaint_router.officer_selector import select_officer_for_department


def test_selects_active_lowest_load_officer(patch_router_firestore):
    result = select_officer_for_department(
        department="Roads & Infrastructure",
        complaint_lat=12.9716,
        complaint_lng=77.5946,
        complaint_zone="south",
    )
    assert result is not None
    assert result.officerId == "officer_road_2"
    assert result.currentLoad == 1


def test_filters_department_only(patch_router_firestore):
    result = select_officer_for_department(
        department="Electricity Board",
        complaint_lat=12.97,
        complaint_lng=77.59,
    )
    assert result is not None
    assert result.officerId == "officer_elec_1"


def test_returns_none_when_no_officer(patch_router_firestore):
    result = select_officer_for_department(
        department="Public Works",
        complaint_lat=12.97,
        complaint_lng=77.59,
    )
    assert result is None
