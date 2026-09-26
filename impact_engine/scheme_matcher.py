"""
Government Scheme Matching Architecture Module.

Provides preliminary structural matching of industrial symbiosis projects against
government energy, waste utilization, and resource-efficiency schemes.

NOTE: Real eligibility is NOT claimed. All matching is based on explicit structural rules
and is intended for architectural evaluation and preliminary screening only.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional

from .data_classification import DataClassification, SCHEME_MATCHING_DISCLAIMER

DEFAULT_SCHEME_DATASET_PATH = Path(__file__).parent / "data" / "synthetic_schemes.json"


class ApplicabilityStatus:
    """Applicability status enum values for scheme matching."""
    POTENTIALLY_APPLICABLE = "POTENTIALLY_APPLICABLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_MORE_DATA = "NEEDS_MORE_DATA"


@dataclass(frozen=True)
class SchemeMatchResult:
    """
    Structured result returned by the Government Scheme Matcher.

    Attributes:
        scheme_id (str): Unique scheme identifier.
        scheme_name (str): Title of the scheme.
        matched_conditions (List[str]): List of project attributes satisfying scheme criteria.
        unmet_conditions (List[str]): List of scheme criteria explicitly violated by project.
        missing_information (List[str]): Required scheme parameters omitted in project profile.
        applicability_status (str): Overall matching status ('POTENTIALLY_APPLICABLE', 'INELIGIBLE', 'NEEDS_MORE_DATA').
        source (str): Source organization publishing the scheme.
        source_url (str): Citation link to official notification or documentation.
        last_verified_date (str): Date when scheme metadata was verified.
        disclaimer (str): Explicit mandatory legal & architectural disclaimer.
        data_classification (str): Data traceability tag (e.g. 'SYNTHETIC_DEMO_DATA').
    """
    scheme_id: str
    scheme_name: str
    matched_conditions: List[str]
    unmet_conditions: List[str]
    missing_information: List[str]
    applicability_status: str
    source: str
    source_url: str
    last_verified_date: str
    disclaimer: str = SCHEME_MATCHING_DISCLAIMER
    data_classification: str = DataClassification.SYNTHETIC_DEMO_DATA.value
    is_synthetic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert scheme match result to dictionary representation."""
        return asdict(self)


class SchemeMatcher:
    """
    Engine for structurally matching project profiles against registered government schemes.
    """

    def __init__(self, scheme_dataset_path: Optional[Path] = None):
        self._schemes: List[Dict[str, Any]] = []
        self._dataset_path = scheme_dataset_path or DEFAULT_SCHEME_DATASET_PATH
        self._load_schemes()

    def _load_schemes(self) -> None:
        """Load scheme records from JSON dataset."""
        if not self._dataset_path.exists():
            return

        with open(self._dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._schemes = data.get("schemes", [])

    def match_project(
        self,
        material: str,
        process: Optional[str] = None,
        quantity_tonnes: Optional[float] = None,
        distance_km: Optional[float] = None,
        geography: Optional[str] = "India",
    ) -> List[SchemeMatchResult]:
        """
        Evaluate project profile against all loaded schemes.

        Args:
            material (str): Target material/by-product name.
            process (str, optional): Target industrial process.
            quantity_tonnes (float, optional): Projected annual quantity in tonnes.
            distance_km (float, optional): Transport distance in km.
            geography (str, optional): Project location/country.

        Returns:
            List[SchemeMatchResult]: Match results for all evaluated schemes.
        """
        results = []
        m_lower = material.strip().lower()

        for scheme in self._schemes:
            matched = []
            unmet = []
            missing = []

            # Material Check
            target_materials = [m.lower() for m in scheme.get("target_materials", [])]
            if any(tm in m_lower or m_lower in tm for tm in target_materials):
                matched.append(f"Material '{material}' matches target materials: {scheme.get('target_materials')}")
            else:
                unmet.append(f"Material '{material}' is not listed under target materials: {scheme.get('target_materials')}")

            # Process Check
            req_processes = scheme.get("required_processes", [])
            if req_processes:
                if process:
                    p_lower = process.strip().lower()
                    if any(rp.lower() in p_lower or p_lower in rp.lower() for rp in req_processes):
                        matched.append(f"Process '{process}' matches required processes: {req_processes}")
                    else:
                        unmet.append(f"Process '{process}' does not match required processes: {req_processes}")
                else:
                    missing.append(f"Process not specified (Scheme requires one of: {req_processes})")

            # Quantity Check
            min_qty = scheme.get("min_quantity_tonnes")
            if min_qty is not None:
                if quantity_tonnes is not None:
                    if quantity_tonnes >= min_qty:
                        matched.append(f"Quantity {quantity_tonnes} tonnes satisfies minimum requirement of {min_qty} tonnes")
                    else:
                        unmet.append(f"Quantity {quantity_tonnes} tonnes is below minimum threshold of {min_qty} tonnes")
                else:
                    missing.append(f"Quantity not specified (Scheme requires minimum {min_qty} tonnes)")

            # Distance Check
            max_dist = scheme.get("max_distance_km")
            if max_dist is not None:
                if distance_km is not None:
                    if distance_km <= max_dist:
                        matched.append(f"Distance {distance_km} km is within maximum allowed radius of {max_dist} km")
                    else:
                        unmet.append(f"Distance {distance_km} km exceeds maximum allowed radius of {max_dist} km")
                else:
                    missing.append(f"Transport distance not specified (Scheme specifies maximum radius of {max_dist} km)")

            # Geography Check
            target_geo = scheme.get("target_geography")
            if target_geo:
                if geography:
                    if geography.strip().lower() == target_geo.strip().lower():
                        matched.append(f"Geography '{geography}' matches target geography '{target_geo}'")
                    else:
                        unmet.append(f"Geography '{geography}' does not match scheme target '{target_geo}'")
                else:
                    missing.append(f"Geography not specified (Scheme applies to '{target_geo}')")

            # Determine Applicability Status
            if unmet:
                status = ApplicabilityStatus.INELIGIBLE
            elif missing:
                status = ApplicabilityStatus.NEEDS_MORE_DATA
            else:
                status = ApplicabilityStatus.POTENTIALLY_APPLICABLE

            is_synth = scheme.get("is_synthetic", True)
            d_class = (
                DataClassification.SYNTHETIC_DEMO_DATA.value
                if is_synth
                else DataClassification.VERIFIED_DATA.value
            )

            result = SchemeMatchResult(
                scheme_id=scheme.get("scheme_id", "UNKNOWN"),
                scheme_name=scheme.get("scheme_name", "Unnamed Scheme"),
                matched_conditions=matched,
                unmet_conditions=unmet,
                missing_information=missing,
                applicability_status=status,
                source=scheme.get("source", "Unknown Source"),
                source_url=scheme.get("source_url", ""),
                last_verified_date=scheme.get("last_verified_date", ""),
                disclaimer=SCHEME_MATCHING_DISCLAIMER,
                data_classification=d_class,
                is_synthetic=is_synth,
            )
            results.append(result)

        return results
