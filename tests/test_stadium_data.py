import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from stadium_data import (
    build_context_snapshot,
    build_ops_context_snapshot,
    crowd_alerts,
    crowd_density_for_gate,
    emergency_exit_for_gate,
    get_gate,
    get_section,
    list_incidents,
    log_incident,
    nearest_amenities,
    resolve_incident,
)


def test_get_section_found():
    section = get_section("203")
    assert section is not None
    assert section.nearest_gate == "B"


def test_get_section_not_found():
    assert get_section("999") is None


def test_get_gate_case_insensitive():
    gate = get_gate("a")
    assert gate is not None
    assert gate.code == "A"


def test_nearest_amenities_filters_by_type():
    results = nearest_amenities("A", amenity_type="restroom")
    assert all(a.type == "restroom" for a in results)
    assert all(a.near_gate == "A" for a in results)


def test_nearest_amenities_accessible_only():
    results = nearest_amenities("C", amenity_type="restroom", accessible_only=True)
    assert all(a.accessible for a in results)


def test_nearest_amenities_sorted_by_wait_time():
    results = nearest_amenities("B")
    waits = [a.current_wait_minutes for a in results]
    assert waits == sorted(waits)


def test_emergency_exit_lookup():
    assert "Gate A" in emergency_exit_for_gate("A")
    assert emergency_exit_for_gate("Z") is None


def test_build_context_snapshot_with_section():
    ctx = build_context_snapshot(section_code="103", accessibility_needs=True)
    assert ctx["section"]["code"] == "103"
    assert ctx["nearest_gate"]["code"] == "A"
    assert ctx["emergency_exit"] is not None


def test_build_context_snapshot_without_section():
    ctx = build_context_snapshot()
    assert ctx["section"] is None
    assert ctx["nearest_gate"] is None


def test_crowd_density_for_gate():
    assert crowd_density_for_gate("c") == 0.91


def test_crowd_density_unknown_gate():
    assert crowd_density_for_gate("Z") is None


def test_crowd_alerts_flags_high_density_gates():
    alerts = crowd_alerts()
    gates = {a["gate"] for a in alerts}
    assert "C" in gates  # 0.91, above the 0.85 threshold
    assert "A" not in gates  # 0.35, below threshold


def test_log_and_list_incident():
    incident = log_incident("C", "crowd_surge", "Queue backing up outside gate", "high")
    assert incident.gate == "C"
    assert incident.resolved is False

    active = list_incidents(gate="C", unresolved_only=True)
    assert any(i.id == incident.id for i in active)


def test_resolve_incident():
    incident = log_incident("D", "facility", "Spill near entrance", "low")
    assert resolve_incident(incident.id) is True
    active = list_incidents(gate="D", unresolved_only=True)
    assert not any(i.id == incident.id for i in active)


def test_resolve_nonexistent_incident_returns_false():
    assert resolve_incident(-1) is False


def test_build_ops_context_snapshot_for_gate():
    ctx = build_ops_context_snapshot(gate_code="C")
    assert ctx["crowd_density"] == 0.91
    assert ctx["gate"]["code"] == "C"


def test_build_ops_context_snapshot_global():
    ctx = build_ops_context_snapshot()
    assert "all_gates_crowd_density" in ctx
    assert "crowd_alerts" in ctx
