"""
Unit Validation and Conversion Module for Impact Engine.

Provides unit parsing, normalization, dimensional verification, gas basis (CO2 vs CO2e)
tracking, and conversion factors to ensure mathematical and physical consistency.
"""

from typing import Tuple, Dict

# Mass base unit: kg
MASS_UNITS: Dict[str, float] = {
    "kg": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "t": 1000.0,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "metric tonne": 1000.0,
    "metric tonnes": 1000.0,
}

# Distance base unit: km
DISTANCE_UNITS: Dict[str, float] = {
    "km": 1.0,
    "kilometer": 1.0,
    "kilometers": 1.0,
    "m": 0.001,
    "meter": 0.001,
    "meters": 0.001,
    "mi": 1.60934,
    "mile": 1.60934,
    "miles": 1.60934,
}

# Emissions base units mapped to (gas_basis, conversion_factor_to_base_kg)
EMISSION_UNITS: Dict[str, Tuple[str, float]] = {
    # CO2e basis
    "kg co2e": ("CO2e", 1.0),
    "kgco2e": ("CO2e", 1.0),
    "kg co2-eq": ("CO2e", 1.0),
    "g co2e": ("CO2e", 0.001),
    "gco2e": ("CO2e", 0.001),
    "t co2e": ("CO2e", 1000.0),
    "tco2e": ("CO2e", 1000.0),
    "tonne co2e": ("CO2e", 1000.0),
    "tonnes co2e": ("CO2e", 1000.0),
    # Direct CO2 basis
    "kg co2": ("CO2", 1.0),
    "kgco2": ("CO2", 1.0),
    "g co2": ("CO2", 0.001),
    "gco2": ("CO2", 0.001),
    "t co2": ("CO2", 1000.0),
    "tco2": ("CO2", 1000.0),
    "tonne co2": ("CO2", 1000.0),
    "tonnes co2": ("CO2", 1000.0),
}


def normalize_unit_string(unit: str) -> str:
    """Normalize a unit string by trimming whitespace and lowercasing."""
    if not unit or not isinstance(unit, str) or not unit.strip():
        raise ValueError("Unit must be a non-empty string.")
    return unit.strip().lower()


def parse_mass_unit(unit_str: str) -> Tuple[str, float]:
    """Parse mass unit string into normalized string and conversion factor to kg."""
    norm = normalize_unit_string(unit_str)
    if norm not in MASS_UNITS:
        raise ValueError(
            f"Invalid or unsupported mass unit: '{unit_str}'. Supported mass units: {sorted(list(MASS_UNITS.keys()))}"
        )
    return norm, MASS_UNITS[norm]


def parse_distance_unit(unit_str: str) -> Tuple[str, float]:
    """Parse distance unit string into normalized string and conversion factor to km."""
    norm = normalize_unit_string(unit_str)
    if norm not in DISTANCE_UNITS:
        raise ValueError(
            f"Invalid or unsupported distance unit: '{unit_str}'. Supported distance units: {sorted(list(DISTANCE_UNITS.keys()))}"
        )
    return norm, DISTANCE_UNITS[norm]


def parse_material_factor_unit(unit_str: str) -> Tuple[str, str, float, str, float]:
    """
    Parse material emission factor unit string (e.g. 'kg CO2e / tonne' or 'kg CO2 / kWh').

    Returns:
        Tuple[gas_basis, emissions_unit, emissions_to_kg_factor, mass_or_energy_unit, mass_to_kg_factor]

    Raises:
        ValueError: If unit format is invalid or units are unsupported.
    """
    norm = normalize_unit_string(unit_str)
    if "/" not in norm:
        raise ValueError(
            f"Invalid material emission factor unit '{unit_str}': expected format 'emissions_unit / mass_or_energy_unit'."
        )

    parts = [p.strip() for p in norm.split("/")]
    if len(parts) != 2:
        raise ValueError(f"Invalid material emission factor unit '{unit_str}': contains multiple slashes.")

    emissions_str, mass_str = parts[0], parts[1]

    if emissions_str not in EMISSION_UNITS:
        raise ValueError(
            f"Unsupported emissions unit '{emissions_str}' in factor unit '{unit_str}'. Supported emissions units: {sorted(list(EMISSION_UNITS.keys()))}"
        )

    gas_basis, emiss_to_kg = EMISSION_UNITS[emissions_str]

    # Handle energy denominator like kWh / MWh or mass denominator like tonne / kg
    if mass_str == "kwh":
        return gas_basis, emissions_str, emiss_to_kg, "kwh", 1.0
    elif mass_str == "mwh":
        return gas_basis, emissions_str, emiss_to_kg, "mwh", 1000.0

    if mass_str not in MASS_UNITS:
        raise ValueError(
            f"Unsupported mass/energy unit '{mass_str}' in factor unit '{unit_str}'."
        )

    return (
        gas_basis,
        emissions_str,
        emiss_to_kg,
        mass_str,
        MASS_UNITS[mass_str],
    )


def parse_transport_factor_unit(unit_str: str) -> Tuple[str, str, float, str, float, str, float]:
    """
    Parse transport emission factor unit string (e.g. 'kg CO2e / tonne-km').

    Returns:
        Tuple[gas_basis, emissions_unit, emissions_to_kg_factor, mass_unit, mass_to_kg_factor, distance_unit, distance_to_km_factor]

    Raises:
        ValueError: If unit format is invalid or units are unsupported.
    """
    norm = normalize_unit_string(unit_str)
    if "/" not in norm:
        raise ValueError(
            f"Invalid transport emission factor unit '{unit_str}': expected format 'emissions_unit / mass_unit-distance_unit'."
        )

    parts = [p.strip() for p in norm.split("/")]
    if len(parts) != 2:
        raise ValueError(f"Invalid transport emission factor unit '{unit_str}': contains multiple slashes.")

    emissions_str, denom_str = parts[0], parts[1]
    denom_clean = denom_str.replace("(", "").replace(")", "")

    if emissions_str not in EMISSION_UNITS:
        raise ValueError(
            f"Unsupported emissions unit '{emissions_str}' in factor unit '{unit_str}'"
        )

    gas_basis, emiss_to_kg = EMISSION_UNITS[emissions_str]

    if "-" in denom_clean:
        denom_parts = [p.strip() for p in denom_clean.split("-")]
    elif "*" in denom_clean:
        denom_parts = [p.strip() for p in denom_clean.split("*")]
    else:
        raise ValueError(
            f"Invalid transport factor unit denominator '{denom_str}': expected mass and distance separated by '-' or '*'."
        )

    if len(denom_parts) != 2:
        raise ValueError(
            f"Invalid transport factor unit denominator '{denom_str}': expected 2 components (mass and distance)."
        )

    comp1, comp2 = denom_parts[0], denom_parts[1]

    if comp1 in MASS_UNITS and comp2 in DISTANCE_UNITS:
        mass_str, dist_str = comp1, comp2
    elif comp1 in DISTANCE_UNITS and comp2 in MASS_UNITS:
        mass_str, dist_str = comp2, comp1
    else:
        raise ValueError(
            f"Invalid transport factor denominator '{denom_str}': must contain one valid mass unit and one valid distance unit."
        )

    return (
        gas_basis,
        emissions_str,
        emiss_to_kg,
        mass_str,
        MASS_UNITS[mass_str],
        dist_str,
        DISTANCE_UNITS[dist_str],
    )
