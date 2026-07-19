"""
stadium_data.py
----------------
Structured "ground truth" data for the stadium. In production this would be
backed by a real-time operations database / IoT feeds (turnstile counters,
POS wait-time sensors, staff dispatch systems, etc). For this challenge we
model it as an in-memory store with a clean access layer so the AI logic
never has to guess facts — it only reasons over verified data.

Keeping data access behind small, pure functions (rather than scattering
dict lookups through the app) is what makes this testable and safe to swap
for a real database later without touching the AI or web layers.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass(frozen=True)
class Gate:
    code: str
    name: str
    accessible: bool
    current_wait_minutes: int
    nearest_sections: list


@dataclass(frozen=True)
class Amenity:
    id: str
    type: str  # restroom, food, first_aid, prayer_room, nursing_room, info_desk
    name: str
    location: str
    accessible: bool
    current_wait_minutes: int
    near_gate: str


@dataclass(frozen=True)
class Section:
    code: str
    zone: str
    nearest_gate: str
    wheelchair_accessible: bool


@dataclass
class Incident:
    """A staff-logged operational incident (ops/tournament-operations vertical)."""

    id: int
    gate: str
    category: str  # crowd_surge, medical, security, facility, other
    description: str
    severity: str  # low, medium, high, critical
    reported_at: str
    resolved: bool = False


# ---------------------------------------------------------------------------
# In-memory dataset (mock "real-time" feed for FIFA World Cup 2026 vertical)
# ---------------------------------------------------------------------------

GATES = {
    "A": Gate("A", "Gate A - North Plaza", True, 6, ["101", "102", "103"]),
    "B": Gate("B", "Gate B - East Concourse", True, 14, ["201", "202", "203"]),
    "C": Gate("C", "Gate C - South Plaza", False, 22, ["301", "302", "303"]),
    "D": Gate("D", "Gate D - West Concourse", True, 4, ["401", "402", "403"]),
}

AMENITIES = [
    Amenity("r1", "restroom", "Restroom R1", "Near Gate A, Level 1", True, 2, "A"),
    Amenity("r2", "restroom", "Restroom R2", "Near Gate B, Level 2", True, 9, "B"),
    Amenity("r3", "restroom", "Restroom R3", "Near Gate C, Level 1", False, 15, "C"),
    Amenity("f1", "food", "North Grill", "Near Gate A, Level 1", True, 5, "A"),
    Amenity("f2", "food", "Global Street Food Court", "Near Gate B, Level 2", True, 20, "B"),
    Amenity("f3", "food", "South Tacos & More", "Near Gate C, Level 1", True, 12, "C"),
    Amenity("m1", "first_aid", "Medical Station 1", "Near Gate A, Level 1", True, 0, "A"),
    Amenity("m2", "first_aid", "Medical Station 2", "Near Gate C, Level 1", True, 0, "C"),
    Amenity("p1", "prayer_room", "Multi-Faith Prayer Room", "Near Gate D, Level 1", True, 0, "D"),
    Amenity("n1", "nursing_room", "Nursing / Family Room", "Near Gate B, Level 1", True, 0, "B"),
    Amenity("i1", "info_desk", "Fan Info Desk", "Main Concourse, Level 1", True, 3, "A"),
]

SECTIONS = {
    f"{n}": Section(str(n), zone, gate, wheelchair)
    for n, zone, gate, wheelchair in [
        (101, "North Lower", "A", True),
        (102, "North Lower", "A", True),
        (103, "North Upper", "A", False),
        (201, "East Lower", "B", True),
        (202, "East Lower", "B", True),
        (203, "East Upper", "B", False),
        (301, "South Lower", "C", True),
        (302, "South Lower", "C", False),
        (303, "South Upper", "C", False),
        (401, "West Lower", "D", True),
        (402, "West Lower", "D", True),
        (403, "West Upper", "D", False),
    ]
}

# Crowd density per gate, 0.0 (empty) - 1.0 (at capacity). Mock "IoT sensor" feed.
CROWD_DENSITY: dict[str, float] = {
    "A": 0.35,
    "B": 0.78,
    "C": 0.91,
    "D": 0.22,
}

CROWD_DENSITY_THRESHOLD_ALERT = 0.85  # above this, ops should consider crowd control

# Thread-safe in-memory incident log for stadium staff (ops vertical).
_incident_lock = Lock()
_incidents: list[Incident] = []
_incident_counter = 0


def log_incident(gate: str, category: str, description: str, severity: str) -> Incident:
    """Record a new operational incident. Thread-safe for concurrent staff reports."""
    global _incident_counter
    with _incident_lock:
        _incident_counter += 1
        incident = Incident(
            id=_incident_counter,
            gate=gate.strip().upper(),
            category=category.strip().lower(),
            description=description.strip(),
            severity=severity.strip().lower(),
            reported_at=datetime.now(UTC).isoformat(),
        )
        _incidents.append(incident)
        return incident


def list_incidents(gate: str | None = None, unresolved_only: bool = False) -> list[Incident]:
    with _incident_lock:
        results = list(_incidents)
    if gate:
        gate = gate.strip().upper()
        results = [i for i in results if i.gate == gate]
    if unresolved_only:
        results = [i for i in results if not i.resolved]
    return sorted(results, key=lambda i: i.reported_at, reverse=True)


def resolve_incident(incident_id: int) -> bool:
    with _incident_lock:
        for incident in _incidents:
            if incident.id == incident_id:
                incident.resolved = True
                return True
    return False


def crowd_density_for_gate(gate_code: str) -> float | None:
    return CROWD_DENSITY.get(str(gate_code).strip().upper())


def crowd_alerts() -> list[dict]:
    """Gates currently above the crowd-control threshold — for ops dashboards/AI alerts."""
    return [
        {"gate": g, "density": d}
        for g, d in CROWD_DENSITY.items()
        if d >= CROWD_DENSITY_THRESHOLD_ALERT
    ]


EMERGENCY_EXITS = {
    "A": "Emergency Exit EA-1 (North Plaza, ground level, 40m from Gate A)",
    "B": "Emergency Exit EB-1 (East Concourse, ground level, 25m from Gate B)",
    "C": "Emergency Exit EC-1 (South Plaza, ground level, 30m from Gate C)",
    "D": "Emergency Exit ED-1 (West Concourse, ground level, 20m from Gate D)",
}


# ---------------------------------------------------------------------------
# Access layer — the only functions the rest of the app should call
# ---------------------------------------------------------------------------


def build_ops_context_snapshot(gate_code: str | None = None) -> dict:
    """
    Structured snapshot for the tournament-operations (staff-facing) persona:
    crowd density, active incidents, and gate wait times. Kept separate from
    the fan-facing snapshot so each AI prompt only receives the data relevant
    to that persona's role.
    """
    if gate_code:
        gate = get_gate(gate_code)
        return {
            "gate": gate.__dict__ if gate else None,
            "crowd_density": crowd_density_for_gate(gate_code),
            "active_incidents": [
                i.__dict__ for i in list_incidents(gate_code, unresolved_only=True)
            ],
        }
    return {
        "all_gates_crowd_density": CROWD_DENSITY,
        "crowd_alerts": crowd_alerts(),
        "active_incidents": [i.__dict__ for i in list_incidents(unresolved_only=True)],
    }


def get_section(section_code: str) -> Section | None:
    return SECTIONS.get(str(section_code).strip())


def get_gate(gate_code: str) -> Gate | None:
    return GATES.get(str(gate_code).strip().upper())


def nearest_amenities(
    gate_code: str, amenity_type: str | None = None, accessible_only: bool = False, limit: int = 3
):
    """Return amenities near a gate, optionally filtered by type/accessibility."""
    gate_code = str(gate_code).strip().upper()
    results = [a for a in AMENITIES if a.near_gate == gate_code]
    if amenity_type:
        results = [a for a in results if a.type == amenity_type]
    if accessible_only:
        results = [a for a in results if a.accessible]
    results.sort(key=lambda a: a.current_wait_minutes)
    return results[:limit]


def emergency_exit_for_gate(gate_code: str) -> str | None:
    return EMERGENCY_EXITS.get(str(gate_code).strip().upper())


def build_context_snapshot(
    section_code: str | None = None, accessibility_needs: bool = False
) -> dict:
    """
    Assemble a compact, structured snapshot of *only the relevant* live data
    for a given fan's context. This is what gets embedded into the AI prompt
    — the model reasons over real numbers instead of hallucinating them.
    """
    section = get_section(section_code) if section_code else None
    gate = get_gate(section.nearest_gate) if section else None

    snapshot: dict[str, object] = {
        "section": section.__dict__ if section else None,
        "nearest_gate": gate.__dict__ if gate else None,
        "nearby_restrooms": [],
        "nearby_food": [],
        "medical_station": None,
        "emergency_exit": None,
    }

    if gate:
        snapshot["nearby_restrooms"] = [
            a.__dict__ for a in nearest_amenities(gate.code, "restroom", accessibility_needs)
        ]
        snapshot["nearby_food"] = [a.__dict__ for a in nearest_amenities(gate.code, "food")]
        medical = nearest_amenities(gate.code, "first_aid", limit=1)
        snapshot["medical_station"] = medical[0].__dict__ if medical else None
        snapshot["emergency_exit"] = emergency_exit_for_gate(gate.code)

    return snapshot
