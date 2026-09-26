"""
Emission Factor Data Loader Module.

Loads verified external emission factors from machine-readable JSON datasets
inside impact_engine/data/ and populates the EmissionFactorRegistry.
"""

import json
from pathlib import Path
from typing import Optional

from .emission_factor import EmissionFactor, EmissionFactorRegistry

DEFAULT_DATASET_PATH = Path(__file__).parent / "data" / "emission_factors.json"
DEFAULT_SYNTHETIC_DATASET_PATH = Path(__file__).parent / "data" / "synthetic_demo_factors.json"


def load_emission_factors(json_path: Optional[Path] = None) -> EmissionFactorRegistry:
    """
    Load verified emission factor dataset from JSON file into an EmissionFactorRegistry.

    Args:
        json_path (Path, optional): Path to the emission factors JSON dataset file.
                                   Defaults to impact_engine/data/emission_factors.json.

    Returns:
        EmissionFactorRegistry: Registry populated with validated external emission factors.

    Raises:
        FileNotFoundError: If dataset file does not exist.
        ValueError: If JSON file structure or factor validation fails.
    """
    path = json_path or DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Emission factor dataset file not found at '{path}'.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "factors" not in data or not isinstance(data["factors"], list):
        raise ValueError(f"Invalid dataset format in '{path}': expected top-level 'factors' array.")

    registry = EmissionFactorRegistry()
    for factor_dict in data["factors"]:
        val = float(factor_dict["value"]) if factor_dict.get("value") is not None else None
        min_val = float(factor_dict["minimum_value"]) if factor_dict.get("minimum_value") is not None else None
        max_val = float(factor_dict["maximum_value"]) if factor_dict.get("maximum_value") is not None else None

        source_org = factor_dict.get("source_organization") or factor_dict.get("source") or ""
        year_val = factor_dict.get("publication_year") if "publication_year" in factor_dict else factor_dict.get("year")

        factor = EmissionFactor(
            factor_id=factor_dict.get("factor_id", factor_dict["factor_name"]),
            factor_name=factor_dict["factor_name"],
            unit=factor_dict["unit"],
            source=source_org,
            value=val,
            minimum_value=min_val,
            maximum_value=max_val,
            value_type=factor_dict.get("value_type", "single_value"),
            original_value_text=factor_dict.get("original_value_text"),
            gas_basis=factor_dict.get("gas_basis", "CO2e"),
            source_url=factor_dict.get("source_url"),
            geographic_scope=factor_dict.get("geographic_scope"),
            applicable_material=factor_dict.get("applicable_material"),
            applicable_process=factor_dict.get("applicable_process"),
            year=year_val,
            uncertainty=factor_dict.get("uncertainty"),
            is_official_government=factor_dict.get("is_official_government", False),
            methodology=factor_dict.get("methodology"),
            system_boundary=factor_dict.get("system_boundary"),
            limitations=factor_dict.get("limitations"),
            classification=factor_dict.get("classification", "INTERNATIONAL_REFERENCE"),
            source_title=factor_dict.get("source_title"),
            verification_status=factor_dict.get("verification_status", "INTERNATIONAL_REFERENCE"),
            is_synthetic=factor_dict.get("is_synthetic", False),
        )
        registry.register(factor)

    return registry


def load_synthetic_emission_factors(json_path: Optional[Path] = None) -> EmissionFactorRegistry:
    """
    Load synthetic/demo emission factor dataset into a dedicated separate EmissionFactorRegistry.

    Args:
        json_path (Path, optional): Path to the synthetic JSON dataset file.
                                   Defaults to impact_engine/data/synthetic_demo_factors.json.

    Returns:
        EmissionFactorRegistry: Registry populated with synthetic demonstration factors.
    """
    path = json_path or DEFAULT_SYNTHETIC_DATASET_PATH
    return load_emission_factors(path)
