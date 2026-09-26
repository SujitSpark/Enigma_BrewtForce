"""
Emission Factor Data Architecture, Classification, Validation, and India-First Registry Module.

Defines schemas and data structures for external emission factors with mandatory
source metadata, verification status tracking, exact gas basis (CO2 vs CO2e),
single vs range representation, classification tags, and India-first query capabilities.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Union
from .units import EMISSION_UNITS


VALID_CLASSIFICATIONS = {
    "INDIA_PRIMARY",
    "INDIA_SECONDARY",
    "INTERNATIONAL_REFERENCE",
    "NOT_SUITABLE",
    "SYNTHETIC_DEMO",
}

VALID_VERIFICATION_STATUSES = {
    "VERIFIED_PRIMARY",
    "VERIFIED_SECONDARY",
    "INTERNATIONAL_REFERENCE",
    "NOT_VERIFIED",
    "SYNTHETIC_DEMO",
}

VALID_GAS_BASES = {"CO2", "CO2e"}

VALID_VALUE_TYPES = {"single_value", "range"}

DISALLOWED_GEOGRAPHIES = {"global", "international", "world", "worldwide"}


class NoIndiaFactorAvailableError(KeyError):
    """
    Exception raised when no verified Indian emission factor is available
    for a requested material or process.
    """

    def __init__(self, material: str, message: Optional[str] = None):
        self.code = "NO_INDIA_FACTOR_AVAILABLE"
        self.material = material
        msg = (
            message
            or f"NO_INDIA_FACTOR_AVAILABLE: No verified Indian emission factor found for material/process '{material}'."
        )
        super().__init__(msg)


class UnverifiedFactorError(ValueError):
    """
    Exception raised when an unverified factor is attempted to be registered
    or used in calculations.
    """

    def __init__(self, factor_name: str, message: Optional[str] = None):
        self.code = "UNVERIFIED_FACTOR_REJECTED"
        self.factor_name = factor_name
        msg = (
            message
            or f"UNVERIFIED_FACTOR_REJECTED: Factor '{factor_name}' is marked as NOT_VERIFIED and cannot be used for calculations."
        )
        super().__init__(msg)


@dataclass(frozen=True)
class EmissionFactor:
    """
    Schema for an externally supplied emission factor with mandatory source metadata,
    exact gas basis (CO2 vs CO2e), single vs range representation, and verification status.

    Attributes:
        factor_id (str): Unique identifier for the factor.
        factor_name (str): Descriptive name for the factor.
        unit (str): Emission factor unit (e.g. 'kg CO2 / kWh' or 'kg CO2e / tonne').
        source (str): Mandatory citation of source organization.
        value (float, optional): Numerical factor value. Required for single_value factors.
        minimum_value (float, optional): Lower bound for range-valued factors.
        maximum_value (float, optional): Upper bound for range-valued factors.
        value_type (str): Value representation mode ('single_value' or 'range').
        original_value_text (str, optional): Verbatim published value text from primary source.
        gas_basis (str): Gas basis indicator ('CO2' or 'CO2e').
        applicable_material (str, optional): Target material.
        applicable_process (str, optional): Target process.
        geographic_scope (str, optional): Exact region/country (e.g. 'India', 'UK', 'USA').
        classification (str): Factor classification ('INDIA_PRIMARY', 'INDIA_SECONDARY', 'INTERNATIONAL_REFERENCE', 'NOT_SUITABLE').
        source_title (str, optional): Exact publication title.
        source_url (str, optional): Reference URL or DOI.
        year (int | str, optional): Publication or reference year/version.
        methodology (str, optional): Underlying calculation methodology.
        system_boundary (str, optional): Exact system boundary.
        uncertainty (float, optional): Estimated uncertainty percentage.
        is_official_government (bool): Flag confirming if source is an official government dataset.
        limitations (str, optional): Known boundaries or limitations.
        verification_status (str): Verification status ('VERIFIED_PRIMARY', 'VERIFIED_SECONDARY', 'INTERNATIONAL_REFERENCE', 'NOT_VERIFIED').
    """
    factor_id: str = ""
    factor_name: str = ""
    unit: str = ""
    source: str = ""
    value: Optional[float] = None
    minimum_value: Optional[float] = None
    maximum_value: Optional[float] = None
    value_type: str = "single_value"
    original_value_text: Optional[str] = None
    gas_basis: str = "CO2e"
    applicable_material: Optional[str] = None
    applicable_process: Optional[str] = None
    geographic_scope: Optional[str] = None
    classification: str = "INTERNATIONAL_REFERENCE"
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    year: Optional[Union[int, str]] = None
    methodology: Optional[str] = None
    system_boundary: Optional[str] = None
    uncertainty: Optional[float] = None
    is_official_government: bool = False
    limitations: Optional[str] = None
    verification_status: str = "INTERNATIONAL_REFERENCE"
    is_synthetic: bool = False

    def __post_init__(self):
        if not self.factor_id and self.factor_name:
            object.__setattr__(self, "factor_id", self.factor_name.replace(" ", "_"))
        if self.classification == "SYNTHETIC_DEMO" or self.verification_status == "SYNTHETIC_DEMO":
            object.__setattr__(self, "is_synthetic", True)

    def validate(self) -> None:
        """
        Validate metadata completeness, verification status, gas basis, range bounds, classification, and geography.

        Raises:
            ValueError: If mandatory metadata is missing or rules are violated.
            TypeError: If types are incorrect.
        """
        if self.is_synthetic:
            if self.verification_status in {"VERIFIED_PRIMARY", "VERIFIED_SECONDARY"}:
                raise ValueError(
                    f"Emission factor '{self.factor_name}': synthetic factors CANNOT be marked as verified status '{self.verification_status}'."
                )
            if self.is_official_government:
                raise ValueError(
                    f"Emission factor '{self.factor_name}': synthetic factors CANNOT be claimed as official government data."
                )

        if not self.factor_id or not isinstance(self.factor_id, str) or not self.factor_id.strip():
            raise ValueError("Emission factor must have a non-empty 'factor_id'.")

        if not self.factor_name or not isinstance(self.factor_name, str) or not self.factor_name.strip():
            raise ValueError("Emission factor must have a non-empty 'factor_name'.")

        if not self.unit or not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError(f"Emission factor '{self.factor_name}': must specify a non-empty 'unit'.")

        if not self.source or not isinstance(self.source, str) or not self.source.strip():
            raise ValueError(
                f"Emission factor '{self.factor_name}': missing mandatory 'source' (organization) metadata."
            )

        if not self.geographic_scope or not isinstance(self.geographic_scope, str) or not self.geographic_scope.strip():
            raise ValueError(
                f"Emission factor '{self.factor_name}': missing mandatory 'geographic_scope' metadata."
            )

        geo_clean = self.geographic_scope.strip().lower()
        if any(disallowed in geo_clean for disallowed in DISALLOWED_GEOGRAPHIES):
            raise ValueError(
                f"Emission factor '{self.factor_name}': invalid geographic_scope '{self.geographic_scope}'. "
                f"Generic scopes like 'Global' or 'International' are prohibited. Must specify exact geography (e.g. 'India', 'UK', 'USA')."
            )

        if self.classification not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"Emission factor '{self.factor_name}': invalid classification '{self.classification}'. "
                f"Must be one of {sorted(list(VALID_CLASSIFICATIONS))}."
            )

        if self.verification_status not in VALID_VERIFICATION_STATUSES:
            raise ValueError(
                f"Emission factor '{self.factor_name}': invalid verification_status '{self.verification_status}'. "
                f"Must be one of {sorted(list(VALID_VERIFICATION_STATUSES))}."
            )

        # Rule checks for verification_status vs classification
        if self.classification == "INDIA_PRIMARY":
            if geo_clean != "india":
                raise ValueError(
                    f"Emission factor '{self.factor_name}': classification is INDIA_PRIMARY but geographic_scope is '{self.geographic_scope}'."
                )
            if self.verification_status != "VERIFIED_PRIMARY":
                raise ValueError(
                    f"Emission factor '{self.factor_name}': INDIA_PRIMARY factors require verification_status='VERIFIED_PRIMARY'."
                )

        if self.classification == "INDIA_SECONDARY":
            if geo_clean != "india":
                raise ValueError(
                    f"Emission factor '{self.factor_name}': classification is INDIA_SECONDARY but geographic_scope is '{self.geographic_scope}'."
                )
            if self.verification_status not in {"VERIFIED_PRIMARY", "VERIFIED_SECONDARY"}:
                raise ValueError(
                    f"Emission factor '{self.factor_name}': INDIA_SECONDARY factors require verification_status in ('VERIFIED_PRIMARY', 'VERIFIED_SECONDARY')."
                )

        # Verification metadata completeness
        if self.verification_status in {"VERIFIED_PRIMARY", "VERIFIED_SECONDARY"}:
            if not self.source_title or not isinstance(self.source_title, str) or not self.source_title.strip():
                raise ValueError(
                    f"Emission factor '{self.factor_name}': verified factors require a non-empty 'source_title'."
                )

        if self.gas_basis not in VALID_GAS_BASES:
            raise ValueError(
                f"Emission factor '{self.factor_name}': invalid gas_basis '{self.gas_basis}'. "
                f"Must be one of {sorted(list(VALID_GAS_BASES))}."
            )

        norm_u = self.unit.strip().lower()
        if "/" in norm_u:
            emiss_part = norm_u.split("/")[0].strip()
            if emiss_part in EMISSION_UNITS:
                parsed_gas, _ = EMISSION_UNITS[emiss_part]
                if self.gas_basis != parsed_gas:
                    raise ValueError(
                        f"Emission factor '{self.factor_name}': gas_basis '{self.gas_basis}' conflicts with unit '{self.unit}' (which specifies '{parsed_gas}')."
                    )

        if self.value_type not in VALID_VALUE_TYPES:
            raise ValueError(
                f"Emission factor '{self.factor_name}': invalid value_type '{self.value_type}'. "
                f"Must be one of {sorted(list(VALID_VALUE_TYPES))}."
            )

        if self.value_type == "single_value":
            if self.value is None or isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise TypeError(f"Emission factor '{self.factor_name}': 'value' must be numeric for single_value factors.")
            if self.value < 0:
                raise ValueError(f"Emission factor '{self.factor_name}': 'value' cannot be negative (got {self.value}).")
        elif self.value_type == "range":
            if self.minimum_value is None or self.maximum_value is None:
                raise ValueError(f"Emission factor '{self.factor_name}': range-valued factor must specify both minimum_value and maximum_value.")
            if self.minimum_value < 0 or self.maximum_value < 0:
                raise ValueError(f"Emission factor '{self.factor_name}': range bounds cannot be negative.")
            if self.minimum_value > self.maximum_value:
                raise ValueError(f"Emission factor '{self.factor_name}': minimum_value ({self.minimum_value}) cannot exceed maximum_value ({self.maximum_value}).")

    def to_dict(self) -> Dict[str, Any]:
        """Convert emission factor and metadata to dictionary representation."""
        return asdict(self)


class EmissionFactorRegistry:
    """
    Registry for storing and querying emission factors with an India-First selection policy
    and strict verification status enforcement.
    """

    def __init__(self):
        self._factors: Dict[str, EmissionFactor] = {}

    def register(self, factor: EmissionFactor) -> None:
        """Register a validated emission factor in the repository."""
        factor.validate()
        if factor.verification_status == "NOT_VERIFIED":
            raise UnverifiedFactorError(factor.factor_name)
        self._factors[factor.factor_name] = factor

    def get(self, factor_name: str) -> EmissionFactor:
        """Retrieve an emission factor by exact name."""
        if factor_name not in self._factors:
            raise KeyError(f"Emission factor '{factor_name}' not found in registry.")
        return self._factors[factor_name]

    def list_factors(self) -> List[EmissionFactor]:
        """List all registered emission factors."""
        return list(self._factors.values())

    def clear(self) -> None:
        """Clear all registered emission factors."""
        self._factors.clear()

    def query(
        self,
        geography: Optional[str] = None,
        classification: Optional[str] = None,
        applicable_material: Optional[str] = None,
        verification_status: Optional[str] = None,
        include_synthetic: bool = False,
    ) -> List[EmissionFactor]:
        """Query factors filtered by geography, classification, material, and/or verification status."""
        results = list(self._factors.values())

        if not include_synthetic and (classification != "SYNTHETIC_DEMO" and verification_status != "SYNTHETIC_DEMO"):
            results = [f for f in results if not f.is_synthetic and f.classification != "SYNTHETIC_DEMO" and f.verification_status != "SYNTHETIC_DEMO"]

        if geography:
            g_target = geography.strip().lower()
            results = [
                f for f in results
                if f.geographic_scope and f.geographic_scope.strip().lower() == g_target
            ]

        if classification:
            c_target = classification.strip().upper()
            results = [f for f in results if f.classification.strip().upper() == c_target]

        if verification_status:
            v_target = verification_status.strip().upper()
            results = [f for f in results if f.verification_status.strip().upper() == v_target]

        if applicable_material:
            m_target = applicable_material.strip().lower()
            results = [
                f for f in results
                if f.applicable_material and m_target in f.applicable_material.strip().lower()
            ]

        return results

    def find_factor(
        self,
        applicable_material: str,
        geography: str = "India",
        classification: Optional[str] = None,
        allow_international_fallback: bool = False,
    ) -> EmissionFactor:
        """Find an appropriate emission factor adhering to India-First rules."""
        target_geo = geography.strip().lower()

        if target_geo == "india":
            indian_factors = self.query(
                geography="India",
                classification=classification,
                applicable_material=applicable_material,
            )

            if indian_factors:
                if not classification:
                    primary = [f for f in indian_factors if f.classification == "INDIA_PRIMARY"]
                    if primary:
                        return primary[0]
                return indian_factors[0]

            if not allow_international_fallback:
                raise NoIndiaFactorAvailableError(material=applicable_material)

        matches = self.query(
            geography=geography if target_geo != "india" else None,
            classification=classification,
            applicable_material=applicable_material,
        )

        if matches:
            return matches[0]

        raise KeyError(
            f"No emission factor found for material '{applicable_material}' with geography '{geography}'."
        )
