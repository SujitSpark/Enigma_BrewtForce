"""
Environmental Impact, Economic Benefit, and Government Scheme Matching Engine Package.
"""

from .emission_factor import (
    EmissionFactor,
    EmissionFactorRegistry,
    NoIndiaFactorAvailableError,
    UnverifiedFactorError,
    VALID_CLASSIFICATIONS,
    VALID_VERIFICATION_STATUSES,
    VALID_GAS_BASES,
    VALID_VALUE_TYPES,
)
from .data_loader import (
    load_emission_factors,
    load_synthetic_emission_factors,
    DEFAULT_DATASET_PATH,
    DEFAULT_SYNTHETIC_DATASET_PATH,
)
from .data_classification import (
    DataClassification,
    SYNTHETIC_DATA_DISCLAIMER,
    SCHEME_MATCHING_DISCLAIMER,
)
from .impact_calculator import (
    EnvironmentalImpactCalculator,
    EnvironmentalImpactResult,
    EnvironmentalImpactRangeResult,
    calculate_environmental_impact,
    calculate_environmental_impact_range,
)
from .economic_calculator import (
    EconomicBenefitCalculator,
    EconomicBenefitResult,
    calculate_economic_benefit,
)
from .scheme_matcher import (
    SchemeMatcher,
    SchemeMatchResult,
    ApplicabilityStatus,
)
from .units import (
    parse_mass_unit,
    parse_distance_unit,
    parse_material_factor_unit,
    parse_transport_factor_unit,
)

__all__ = [
    "EmissionFactor",
    "EmissionFactorRegistry",
    "NoIndiaFactorAvailableError",
    "UnverifiedFactorError",
    "VALID_CLASSIFICATIONS",
    "VALID_VERIFICATION_STATUSES",
    "VALID_GAS_BASES",
    "VALID_VALUE_TYPES",
    "EnvironmentalImpactCalculator",
    "EnvironmentalImpactResult",
    "EnvironmentalImpactRangeResult",
    "calculate_environmental_impact",
    "calculate_environmental_impact_range",
    "EconomicBenefitCalculator",
    "EconomicBenefitResult",
    "calculate_economic_benefit",
    "SchemeMatcher",
    "SchemeMatchResult",
    "ApplicabilityStatus",
    "DataClassification",
    "SYNTHETIC_DATA_DISCLAIMER",
    "SCHEME_MATCHING_DISCLAIMER",
    "load_emission_factors",
    "load_synthetic_emission_factors",
    "DEFAULT_DATASET_PATH",
    "DEFAULT_SYNTHETIC_DATASET_PATH",
    "parse_mass_unit",
    "parse_distance_unit",
    "parse_material_factor_unit",
    "parse_transport_factor_unit",
]
