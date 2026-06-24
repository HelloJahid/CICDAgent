"""Deterministic tools the agent can call.

These functions are intentionally pure: no network, no AWS, no randomness. That
keeps the CI ``test`` job fast and lets us assert exact numbers in unit tests.
The agent (see ``agent.py``) wraps these with the Bedrock Converse API so a user
can ask in plain language and the model decides when to call them.

Domain: estimating daily passenger demand on Australian origin-to-destination
(OD) routes. This mirrors the running OD example in ``docs/ci_cd_pipeline.pdf``.
"""

from __future__ import annotations

import math

# Approximate resident populations for a handful of Australian cities and towns.
# Round figures are fine - this is illustrative cargo for the pipeline, not a
# production demand model.
CITY_POPULATION: dict[str, int] = {
    "albury": 56_000,
    "wagga wagga": 57_000,
    "bendigo": 100_000,
    "ballarat": 110_000,
    "toowoomba": 140_000,
    "brisbane": 2_600_000,
    "bunbury": 75_000,
    "perth": 2_100_000,
    "sydney": 5_300_000,
    "melbourne": 5_100_000,
    "canberra": 460_000,
    "geelong": 270_000,
}

# Road distances in kilometres for known city pairs. Keyed by a frozenset so the
# direction does not matter (Albury->Wagga is the same distance as Wagga->Albury).
DISTANCE_KM: dict[frozenset[str], int] = {
    frozenset({"albury", "wagga wagga"}): 128,
    frozenset({"bendigo", "ballarat"}): 121,
    frozenset({"toowoomba", "brisbane"}): 128,
    frozenset({"bunbury", "perth"}): 175,
    frozenset({"sydney", "melbourne"}): 878,
    frozenset({"sydney", "canberra"}): 286,
    frozenset({"melbourne", "geelong"}): 75,
}

# Calibration constant for the gravity model below. Chosen so regional pairs land
# in the low hundreds of passengers per day, matching the PDF's sample figures.
_GRAVITY_K = 0.32


def _normalise(name: str) -> str:
    """Lower-case and collapse whitespace so 'Wagga  Wagga ' matches the table."""
    return " ".join(name.strip().lower().split())


def list_routes() -> dict:
    """Return the OD routes the assistant currently has data for.

    The agent calls this when a user asks what is available, or to recover after
    asking about an unknown route.
    """
    routes = []
    for pair in DISTANCE_KM:
        a, b = sorted(pair)
        routes.append({"origin": a.title(), "destination": b.title()})
    return {"routes": sorted(routes, key=lambda r: (r["origin"], r["destination"]))}


def estimate_demand(origin: str, destination: str) -> dict:
    """Estimate daily passenger demand between two cities.

    Uses a simple, deterministic gravity model:

        pax/day = round(K * sqrt(pop_origin * pop_destination) / distance_km)

    Returns a structured result. When a city or the route distance is unknown the
    result carries ``"known": False`` and a reason, so the agent can explain the
    gap rather than inventing a number.
    """
    o = _normalise(origin)
    d = _normalise(destination)

    if o == d:
        return {
            "known": False,
            "reason": "Origin and destination are the same place.",
            "origin": origin,
            "destination": destination,
        }

    missing = [name for name, key in ((origin, o), (destination, d)) if key not in CITY_POPULATION]
    if missing:
        return {
            "known": False,
            "reason": f"No population data for: {', '.join(missing)}.",
            "origin": origin,
            "destination": destination,
        }

    distance = DISTANCE_KM.get(frozenset({o, d}))
    if distance is None:
        return {
            "known": False,
            "reason": f"No route distance on file for {origin} to {destination}.",
            "origin": origin,
            "destination": destination,
        }

    pop_product = CITY_POPULATION[o] * CITY_POPULATION[d]
    estimated = round(_GRAVITY_K * math.sqrt(pop_product) / distance)

    if estimated >= 1500:
        category = "high"
    elif estimated >= 300:
        category = "medium"
    else:
        category = "low"

    return {
        "known": True,
        "origin": origin.title(),
        "destination": destination.title(),
        "distance_km": distance,
        "estimated_daily_pax": estimated,
        "demand_category": category,
    }


# Registry the agent uses to dispatch a tool name to its implementation.
TOOL_FUNCTIONS = {
    "estimate_demand": estimate_demand,
    "list_routes": list_routes,
}
