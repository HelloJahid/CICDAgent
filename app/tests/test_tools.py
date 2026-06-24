"""Unit tests for the deterministic tools.

Because the gravity model is pure and deterministic, we can assert exact values.
"""

import math

from app.tools import (
    _GRAVITY_K,
    CITY_POPULATION,
    DISTANCE_KM,
    estimate_demand,
    list_routes,
)


def _expected(origin: str, destination: str) -> int:
    pop = CITY_POPULATION[origin] * CITY_POPULATION[destination]
    dist = DISTANCE_KM[frozenset({origin, destination})]
    return round(_GRAVITY_K * math.sqrt(pop) / dist)


def test_known_route_returns_deterministic_estimate():
    result = estimate_demand("Albury", "Wagga Wagga")
    assert result["known"] is True
    assert result["origin"] == "Albury"
    assert result["destination"] == "Wagga Wagga"
    assert result["distance_km"] == 128
    assert result["estimated_daily_pax"] == _expected("albury", "wagga wagga")
    assert result["demand_category"] in {"low", "medium", "high"}


def test_route_is_direction_independent():
    forward = estimate_demand("Bendigo", "Ballarat")
    reverse = estimate_demand("Ballarat", "Bendigo")
    assert forward["estimated_daily_pax"] == reverse["estimated_daily_pax"]


def test_name_normalisation_handles_case_and_whitespace():
    messy = estimate_demand("  albury ", "WAGGA   WAGGA")
    clean = estimate_demand("Albury", "Wagga Wagga")
    assert messy["estimated_daily_pax"] == clean["estimated_daily_pax"]


def test_big_city_pair_is_high_demand():
    result = estimate_demand("Sydney", "Melbourne")
    assert result["known"] is True
    assert result["demand_category"] == "high"


def test_unknown_city_is_flagged_not_invented():
    result = estimate_demand("Atlantis", "Sydney")
    assert result["known"] is False
    assert "Atlantis" in result["reason"]
    assert "estimated_daily_pax" not in result


def test_known_cities_without_route_distance_are_flagged():
    # Both cities exist, but this pair has no distance on file.
    result = estimate_demand("Bunbury", "Canberra")
    assert result["known"] is False
    assert "distance" in result["reason"].lower()


def test_same_origin_and_destination_flagged():
    result = estimate_demand("Perth", "perth")
    assert result["known"] is False


def test_list_routes_returns_sorted_known_pairs():
    routes = list_routes()["routes"]
    assert {"origin": "Albury", "destination": "Wagga Wagga"} in routes
    assert routes == sorted(routes, key=lambda r: (r["origin"], r["destination"]))
    assert len(routes) == len(DISTANCE_KM)
