"""
Environmental Impact Calculator Module.

Calculates physical net environmental benefit (in CO2 or CO2e) of material recycling/reuse
using externally supplied, traceable emission factors, strict gas basis tracking (CO2 vs CO2e),
verification status validation, unit validation, and range-based scenario modeling.

Formulas:
    Virgin emissions avoided = quantity * virgin_material_emission_factor
    Processing emissions     = quantity * processing_emission_factor
    Transport emissions      = quantity * distance * transport_emission_factor
    Net environmental benefit = virgin emissions avoided - processing emissions - transport emissions

Range Calculation Formulas:
    Net benefit min (worst case) = virgin_avoided_min - processing_max - transport_max
    Net benefit max (best case)  = virgin_avoided_max - processing_min - transport_min

Validation & Methodological Integrity:
    - Enforces verification status. Rejects NOT_VERIFIED factors from calculation engine.
    - Enforces gas basis consistency (CO2 vs CO2e). Rejects mixing CO2 and CO2e without verified conversion.
    - Preserves range-valued metadata and provides explicit best/worst case range calculations.
    - Preserves verbatim published factor metadata.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Union, Tuple

from .emission_factor import EmissionFactor, UnverifiedFactorError
from .units import (
    parse_mass_unit,
    parse_distance_unit,
    parse_material_factor_unit,
    parse_transport_factor_unit,
)


from .data_classification import DataClassification, SYNTHETIC_DATA_DISCLAIMER


@dataclass
class EnvironmentalImpactResult:
    """
    Structured result for single-value environmental impact calculation.

    Attributes:
        virgin_emissions_avoided (float): Avoided emissions from virgin material (kg CO2 or kg CO2e).
        processing_emissions (float): Emissions from material processing (kg CO2 or kg CO2e).
        transport_emissions (float): Emissions from transportation (kg CO2 or kg CO2e).
        net_co2e_benefit (float): Net environmental benefit (kg CO2 or kg CO2e).
        emissions_gas_basis (str): Gas basis indicator ('CO2' or 'CO2e').
        is_estimated (bool): Always True, confirming estimation status.
        label (str): Classification label marking result as an estimate.
        factor_sources (Dict[str, Dict[str, Any]]): Traceable metadata for all input factors.
        assumptions (Dict[str, Any]): Calculation metadata, unit details, and disclaimers.
        data_classification (str): Data classification tag (e.g. 'CALCULATED_OUTPUT' or 'SYNTHETIC_DEMO_DATA').
        is_synthetic (bool): True if any underlying factor is synthetic/demo.
        disclaimer (str, optional): Legal/methodology disclaimer.
    """
    virgin_emissions_avoided: float
    processing_emissions: float
    transport_emissions: float
    net_co2e_benefit: float
    emissions_gas_basis: str = "CO2e"
    is_estimated: bool = True
    label: str = "ESTIMATED environmental impact, not an official carbon credit"
    factor_sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    data_classification: str = DataClassification.CALCULATED_OUTPUT.value
    is_synthetic: bool = False
    disclaimer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result dataclass instance to a standard Python dictionary."""
        return asdict(self)


@dataclass
class EnvironmentalImpactRangeResult:
    """
    Structured result for range-based environmental impact calculations (best-case / worst-case).

    Attributes:
        virgin_emissions_avoided_min (float): Minimum avoided emissions (kg CO2 or kg CO2e).
        virgin_emissions_avoided_max (float): Maximum avoided emissions (kg CO2 or kg CO2e).
        processing_emissions_min (float): Minimum processing emissions (kg CO2 or kg CO2e).
        processing_emissions_max (float): Maximum processing emissions (kg CO2 or kg CO2e).
        transport_emissions_min (float): Minimum transport emissions (kg CO2 or kg CO2e).
        transport_emissions_max (float): Maximum transport emissions (kg CO2 or kg CO2e).
        net_co2e_benefit_min (float): Minimum net benefit (worst-case scenario).
        net_co2e_benefit_max (float): Maximum net benefit (best-case scenario).
        net_co2e_benefit_central (float, optional): Central net benefit if central values exist.
        emissions_gas_basis (str): Gas basis indicator ('CO2' or 'CO2e').
        is_estimated (bool): Always True.
        label (str): Classification label marking result as an estimate range.
        factor_sources (Dict[str, Dict[str, Any]]): Lineage metadata for all factors.
        assumptions (Dict[str, Any]): Calculation assumptions and methodology notes.
    """
    virgin_emissions_avoided_min: float
    virgin_emissions_avoided_max: float
    processing_emissions_min: float
    processing_emissions_max: float
    transport_emissions_min: float
    transport_emissions_max: float
    net_co2e_benefit_min: float
    net_co2e_benefit_max: float
    net_co2e_benefit_central: Optional[float] = None
    emissions_gas_basis: str = "CO2e"
    is_estimated: bool = True
    label: str = "ESTIMATED environmental impact range, not an official carbon credit"
    factor_sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    assumptions: Dict[str, Any] = field(default_factory=dict)
    data_classification: str = DataClassification.CALCULATED_OUTPUT.value
    is_synthetic: bool = False
    disclaimer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result dataclass instance to a standard Python dictionary."""
        return asdict(self)


class EnvironmentalImpactCalculator:
    """
    Calculator class for environmental benefit estimation using external emission factors.
    """

    @staticmethod
    def _extract_bounds(factor: EmissionFactor) -> Tuple[float, float, Optional[float]]:
        """Extract (min, max, central) numerical values for a factor."""
        if factor.value_type == "single_value":
            val = float(factor.value)
            return val, val, val
        elif factor.value_type == "range":
            min_v = float(factor.minimum_value)
            max_v = float(factor.maximum_value)
            c_v = float(factor.value) if factor.value is not None else None
            return min_v, max_v, c_v
        else:
            raise ValueError(f"Unknown value_type '{factor.value_type}' for factor '{factor.factor_name}'.")

    @staticmethod
    def calculate(
        quantity: Union[int, float],
        distance: Union[int, float],
        virgin_material_emission_factor: EmissionFactor,
        processing_emission_factor: EmissionFactor,
        transport_emission_factor: EmissionFactor,
        quantity_unit: str = "tonne",
        distance_unit: str = "km",
        custom_assumptions: Optional[Dict[str, Any]] = None,
        decimals: Optional[int] = 4,
    ) -> EnvironmentalImpactResult:
        """
        Calculate single-value net environmental benefit from externally supplied factors.

        Args:
            quantity (int | float): Material quantity. Must be >= 0.
            distance (int | float): Transport distance. Must be >= 0.
            virgin_material_emission_factor (EmissionFactor): External virgin material factor with metadata.
            processing_emission_factor (EmissionFactor): External processing factor with metadata.
            transport_emission_factor (EmissionFactor): External transport factor with metadata.
            quantity_unit (str): Mass unit of input quantity (default 'tonne').
            distance_unit (str): Distance unit of transport distance (default 'km').
            custom_assumptions (dict, optional): Additional contextual assumptions.
            decimals (int, optional): Precision for rounding output floats. Defaults to 4.

        Returns:
            EnvironmentalImpactResult: Structured calculation result with factor lineage and gas basis.

        Raises:
            ValueError: If inputs are negative, missing, have invalid units, mix gas bases, or pass an unverified/range factor without central value.
            TypeError: If input values or emission factor objects are of invalid types.
        """
        # 1. Validate numerical inputs
        for name, val in [("quantity", quantity), ("distance", distance)]:
            if val is None:
                raise ValueError(f"Missing required parameter: '{name}' cannot be None.")
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise TypeError(f"Invalid type for '{name}': expected int or float, got {type(val).__name__}.")
            if val < 0:
                raise ValueError(f"Invalid value for '{name}': value cannot be negative (got {val}).")

        # 2. Validate EmissionFactor instances & metadata
        factors = {
            "virgin_material_emission_factor": virgin_material_emission_factor,
            "processing_emission_factor": processing_emission_factor,
            "transport_emission_factor": transport_emission_factor,
        }

        for factor_key, factor_obj in factors.items():
            if not isinstance(factor_obj, EmissionFactor):
                raise TypeError(
                    f"Parameter '{factor_key}' must be an instance of EmissionFactor, got {type(factor_obj).__name__}."
                )
            factor_obj.validate()

            if factor_obj.verification_status == "NOT_VERIFIED":
                raise UnverifiedFactorError(factor_obj.factor_name)

            if factor_obj.value_type == "range" and factor_obj.value is None:
                raise ValueError(
                    f"Factor '{factor_obj.factor_name}' is a range-valued factor "
                    f"(min={factor_obj.minimum_value}, max={factor_obj.maximum_value}) without a central value. "
                    f"Standard single-value calculation mode requires a central value or range mode (calculate_range)."
                )

        # 3. Parse units and verify gas basis consistency
        _, qty_mass_to_kg = parse_mass_unit(quantity_unit)
        _, dist_to_km = parse_distance_unit(distance_unit)

        v_gas, _, v_emiss_to_kg, _, v_mass_to_kg = parse_material_factor_unit(
            virgin_material_emission_factor.unit
        )
        p_gas, _, p_emiss_to_kg, _, p_mass_to_kg = parse_material_factor_unit(
            processing_emission_factor.unit
        )
        t_gas, _, t_emiss_to_kg, _, t_mass_to_kg, _, t_dist_to_km = parse_transport_factor_unit(
            transport_emission_factor.unit
        )

        for f_name, f_obj, parsed_g in [
            ("virgin_material_emission_factor", virgin_material_emission_factor, v_gas),
            ("processing_emission_factor", processing_emission_factor, p_gas),
            ("transport_emission_factor", transport_emission_factor, t_gas),
        ]:
            if f_obj.gas_basis != parsed_g:
                raise ValueError(
                    f"Gas basis mismatch for '{f_name}': factor metadata specifies gas_basis='{f_obj.gas_basis}' "
                    f"but unit string specifies '{parsed_g}'."
                )

        if not (v_gas == p_gas == t_gas):
            raise ValueError(
                f"Mismatched gas basis across calculation inputs: virgin={v_gas}, processing={p_gas}, transport={t_gas}. "
                f"Cannot mix CO2 and CO2e factors without a verified conversion methodology."
            )

        calculation_gas_basis = v_gas
        emissions_output_unit = f"kg {calculation_gas_basis}"

        # 4. Perform calculations
        base_qty_kg = float(quantity) * qty_mass_to_kg
        base_dist_km = float(distance) * dist_to_km

        v_base_intensity = (virgin_material_emission_factor.value * v_emiss_to_kg) / v_mass_to_kg
        p_base_intensity = (processing_emission_factor.value * p_emiss_to_kg) / p_mass_to_kg
        t_base_intensity = (
            transport_emission_factor.value * t_emiss_to_kg
        ) / (t_mass_to_kg * t_dist_to_km)

        virgin_emissions_avoided = base_qty_kg * v_base_intensity
        processing_emissions = base_qty_kg * p_base_intensity
        transport_emissions = base_qty_kg * base_dist_km * t_base_intensity

        net_co2e_benefit = virgin_emissions_avoided - processing_emissions - transport_emissions

        if decimals is not None:
            virgin_emissions_avoided = round(virgin_emissions_avoided, decimals)
            processing_emissions = round(processing_emissions, decimals)
            transport_emissions = round(transport_emissions, decimals)
            net_co2e_benefit = round(net_co2e_benefit, decimals)

        factor_sources = {
            "virgin_material_factor": virgin_material_emission_factor.to_dict(),
            "processing_factor": processing_emission_factor.to_dict(),
            "transport_factor": transport_emission_factor.to_dict(),
        }

        assumptions = {
            "quantity_input": {"value": quantity, "unit": quantity_unit},
            "distance_input": {"value": distance, "unit": distance_unit},
            "output_emissions_unit": emissions_output_unit,
            "emissions_gas_basis": calculation_gas_basis,
            "disclaimer": (
                f"ESTIMATED environmental impact ({calculation_gas_basis}) calculated using externally provided emission factors. "
                f"Not an official carbon credit certification."
            ),
            "methodology": (
                "Calculated as (Quantity * Virgin Factor) - (Quantity * Processing Factor) - "
                "(Quantity * Distance * Transport Factor) after unit normalization."
            ),
            "data_policy": "All emission factors were supplied externally with traceable metadata. Gas basis mismatch and unverified conversions are prohibited.",
        }

        any_synthetic = any(
            f.is_synthetic or f.classification == "SYNTHETIC_DEMO" or f.verification_status == "SYNTHETIC_DEMO"
            for f in [virgin_material_emission_factor, processing_emission_factor, transport_emission_factor]
        )
        res_classification = (
            DataClassification.SYNTHETIC_DEMO_DATA.value
            if any_synthetic
            else DataClassification.CALCULATED_OUTPUT.value
        )
        res_disclaimer = SYNTHETIC_DATA_DISCLAIMER if any_synthetic else None
        res_label = (
            f"SYNTHETIC / DEMO environmental impact estimate ({calculation_gas_basis}) - FOR DEMONSTRATION ONLY"
            if any_synthetic
            else f"ESTIMATED environmental impact ({calculation_gas_basis}), not an official carbon credit"
        )

        if any_synthetic:
            assumptions["synthetic_data_notice"] = SYNTHETIC_DATA_DISCLAIMER

        if custom_assumptions:
            assumptions.update(custom_assumptions)

        return EnvironmentalImpactResult(
            virgin_emissions_avoided=virgin_emissions_avoided,
            processing_emissions=processing_emissions,
            transport_emissions=transport_emissions,
            net_co2e_benefit=net_co2e_benefit,
            emissions_gas_basis=calculation_gas_basis,
            is_estimated=True,
            label=res_label,
            factor_sources=factor_sources,
            assumptions=assumptions,
            data_classification=res_classification,
            is_synthetic=any_synthetic,
            disclaimer=res_disclaimer,
        )

    @staticmethod
    def calculate_range(
        quantity: Union[int, float],
        distance: Union[int, float],
        virgin_material_emission_factor: EmissionFactor,
        processing_emission_factor: EmissionFactor,
        transport_emission_factor: EmissionFactor,
        quantity_unit: str = "tonne",
        distance_unit: str = "km",
        custom_assumptions: Optional[Dict[str, Any]] = None,
        decimals: Optional[int] = 4,
    ) -> EnvironmentalImpactRangeResult:
        """
        Calculate range-based best-case / worst-case net environmental benefit.

        Args:
            quantity (int | float): Material quantity. Must be >= 0.
            distance (int | float): Transport distance. Must be >= 0.
            virgin_material_emission_factor (EmissionFactor): External virgin material factor.
            processing_emission_factor (EmissionFactor): External processing factor.
            transport_emission_factor (EmissionFactor): External transport factor.
            quantity_unit (str): Mass unit of input quantity.
            distance_unit (str): Distance unit of transport.
            custom_assumptions (dict, optional): Contextual assumptions.
            decimals (int, optional): Output precision rounding.

        Returns:
            EnvironmentalImpactRangeResult: Structured result containing min, max, and central benefit bounds.
        """
        for name, val in [("quantity", quantity), ("distance", distance)]:
            if val is None:
                raise ValueError(f"Missing required parameter: '{name}' cannot be None.")
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise TypeError(f"Invalid type for '{name}': expected int or float, got {type(val).__name__}.")
            if val < 0:
                raise ValueError(f"Invalid value for '{name}': value cannot be negative (got {val}).")

        factors = {
            "virgin_material_emission_factor": virgin_material_emission_factor,
            "processing_emission_factor": processing_emission_factor,
            "transport_emission_factor": transport_emission_factor,
        }

        for factor_key, factor_obj in factors.items():
            if not isinstance(factor_obj, EmissionFactor):
                raise TypeError(
                    f"Parameter '{factor_key}' must be an instance of EmissionFactor, got {type(factor_obj).__name__}."
                )
            factor_obj.validate()

            if factor_obj.verification_status == "NOT_VERIFIED":
                raise UnverifiedFactorError(factor_obj.factor_name)

        _, qty_mass_to_kg = parse_mass_unit(quantity_unit)
        _, dist_to_km = parse_distance_unit(distance_unit)

        v_gas, _, v_emiss_to_kg, _, v_mass_to_kg = parse_material_factor_unit(
            virgin_material_emission_factor.unit
        )
        p_gas, _, p_emiss_to_kg, _, p_mass_to_kg = parse_material_factor_unit(
            processing_emission_factor.unit
        )
        t_gas, _, t_emiss_to_kg, _, t_mass_to_kg, _, t_dist_to_km = parse_transport_factor_unit(
            transport_emission_factor.unit
        )

        for f_name, f_obj, parsed_g in [
            ("virgin_material_emission_factor", virgin_material_emission_factor, v_gas),
            ("processing_emission_factor", processing_emission_factor, p_gas),
            ("transport_emission_factor", transport_emission_factor, t_gas),
        ]:
            if f_obj.gas_basis != parsed_g:
                raise ValueError(
                    f"Gas basis mismatch for '{f_name}': factor metadata specifies gas_basis='{f_obj.gas_basis}' "
                    f"but unit string specifies '{parsed_g}'."
                )

        if not (v_gas == p_gas == t_gas):
            raise ValueError(
                f"Mismatched gas basis across calculation inputs: virgin={v_gas}, processing={p_gas}, transport={t_gas}. "
                f"Cannot mix CO2 and CO2e factors without a verified conversion methodology."
            )

        calculation_gas_basis = v_gas
        emissions_output_unit = f"kg {calculation_gas_basis}"

        base_qty_kg = float(quantity) * qty_mass_to_kg
        base_dist_km = float(distance) * dist_to_km

        v_min, v_max, v_central = EnvironmentalImpactCalculator._extract_bounds(virgin_material_emission_factor)
        p_min, p_max, p_central = EnvironmentalImpactCalculator._extract_bounds(processing_emission_factor)
        t_min, t_max, t_central = EnvironmentalImpactCalculator._extract_bounds(transport_emission_factor)

        v_min_int = (v_min * v_emiss_to_kg) / v_mass_to_kg
        v_max_int = (v_max * v_emiss_to_kg) / v_mass_to_kg

        p_min_int = (p_min * p_emiss_to_kg) / p_mass_to_kg
        p_max_int = (p_max * p_emiss_to_kg) / p_mass_to_kg

        t_min_int = (t_min * t_emiss_to_kg) / (t_mass_to_kg * t_dist_to_km)
        t_max_int = (t_max * t_emiss_to_kg) / (t_mass_to_kg * t_dist_to_km)

        v_avoided_min = base_qty_kg * v_min_int
        v_avoided_max = base_qty_kg * v_max_int

        p_emiss_min = base_qty_kg * p_min_int
        p_emiss_max = base_qty_kg * p_max_int

        t_emiss_min = base_qty_kg * base_dist_km * t_min_int
        t_emiss_max = base_qty_kg * base_dist_km * t_max_int

        net_min = v_avoided_min - p_emiss_max - t_emiss_max
        net_max = v_avoided_max - p_emiss_min - t_emiss_min

        net_central = None
        if v_central is not None and p_central is not None and t_central is not None:
            v_c_int = (v_central * v_emiss_to_kg) / v_mass_to_kg
            p_c_int = (p_central * p_emiss_to_kg) / p_mass_to_kg
            t_c_int = (t_central * t_emiss_to_kg) / (t_mass_to_kg * t_dist_to_km)

            v_avoided_c = base_qty_kg * v_c_int
            p_emiss_c = base_qty_kg * p_c_int
            t_emiss_c = base_qty_kg * base_dist_km * t_c_int

            net_central = v_avoided_c - p_emiss_c - t_emiss_c

        if decimals is not None:
            v_avoided_min = round(v_avoided_min, decimals)
            v_avoided_max = round(v_avoided_max, decimals)
            p_emiss_min = round(p_emiss_min, decimals)
            p_emiss_max = round(p_emiss_max, decimals)
            t_emiss_min = round(t_emiss_min, decimals)
            t_emiss_max = round(t_emiss_max, decimals)
            net_min = round(net_min, decimals)
            net_max = round(net_max, decimals)
            if net_central is not None:
                net_central = round(net_central, decimals)

        factor_sources = {
            "virgin_material_factor": virgin_material_emission_factor.to_dict(),
            "processing_factor": processing_emission_factor.to_dict(),
            "transport_factor": transport_emission_factor.to_dict(),
        }

        assumptions = {
            "quantity_input": {"value": quantity, "unit": quantity_unit},
            "distance_input": {"value": distance, "unit": distance_unit},
            "output_emissions_unit": emissions_output_unit,
            "emissions_gas_basis": calculation_gas_basis,
            "calculation_mode": "range",
            "disclaimer": (
                f"ESTIMATED environmental impact range ({calculation_gas_basis}) calculated using range-valued emission factors. "
                f"Not an official carbon credit certification."
            ),
            "methodology": (
                "Best case net benefit = virgin_max - processing_min - transport_min. "
                "Worst case net benefit = virgin_min - processing_max - transport_max."
            ),
        }

        any_synthetic = any(
            f.is_synthetic or f.classification == "SYNTHETIC_DEMO" or f.verification_status == "SYNTHETIC_DEMO"
            for f in [virgin_material_emission_factor, processing_emission_factor, transport_emission_factor]
        )
        res_classification = (
            DataClassification.SYNTHETIC_DEMO_DATA.value
            if any_synthetic
            else DataClassification.CALCULATED_OUTPUT.value
        )
        res_disclaimer = SYNTHETIC_DATA_DISCLAIMER if any_synthetic else None
        res_label = (
            f"SYNTHETIC / DEMO environmental impact range estimate ({calculation_gas_basis}) - FOR DEMONSTRATION ONLY"
            if any_synthetic
            else f"ESTIMATED environmental impact range ({calculation_gas_basis}), not an official carbon credit"
        )

        if any_synthetic:
            assumptions["synthetic_data_notice"] = SYNTHETIC_DATA_DISCLAIMER

        if custom_assumptions:
            assumptions.update(custom_assumptions)

        return EnvironmentalImpactRangeResult(
            virgin_emissions_avoided_min=v_avoided_min,
            virgin_emissions_avoided_max=v_avoided_max,
            processing_emissions_min=p_emiss_min,
            processing_emissions_max=p_emiss_max,
            transport_emissions_min=t_emiss_min,
            transport_emissions_max=t_emiss_max,
            net_co2e_benefit_min=net_min,
            net_co2e_benefit_max=net_max,
            net_co2e_benefit_central=net_central,
            emissions_gas_basis=calculation_gas_basis,
            is_estimated=True,
            label=res_label,
            factor_sources=factor_sources,
            assumptions=assumptions,
            data_classification=res_classification,
            is_synthetic=any_synthetic,
            disclaimer=res_disclaimer,
        )


def calculate_environmental_impact(
    quantity: Union[int, float],
    distance: Union[int, float],
    virgin_material_emission_factor: EmissionFactor,
    processing_emission_factor: EmissionFactor,
    transport_emission_factor: EmissionFactor,
    quantity_unit: str = "tonne",
    distance_unit: str = "km",
    custom_assumptions: Optional[Dict[str, Any]] = None,
    decimals: Optional[int] = 4,
) -> EnvironmentalImpactResult:
    """Convenience function for EnvironmentalImpactCalculator.calculate."""
    return EnvironmentalImpactCalculator.calculate(
        quantity=quantity,
        distance=distance,
        virgin_material_emission_factor=virgin_material_emission_factor,
        processing_emission_factor=processing_emission_factor,
        transport_emission_factor=transport_emission_factor,
        quantity_unit=quantity_unit,
        distance_unit=distance_unit,
        custom_assumptions=custom_assumptions,
        decimals=decimals,
    )


def calculate_environmental_impact_range(
    quantity: Union[int, float],
    distance: Union[int, float],
    virgin_material_emission_factor: EmissionFactor,
    processing_emission_factor: EmissionFactor,
    transport_emission_factor: EmissionFactor,
    quantity_unit: str = "tonne",
    distance_unit: str = "km",
    custom_assumptions: Optional[Dict[str, Any]] = None,
    decimals: Optional[int] = 4,
) -> EnvironmentalImpactRangeResult:
    """Convenience function for EnvironmentalImpactCalculator.calculate_range."""
    return EnvironmentalImpactCalculator.calculate_range(
        quantity=quantity,
        distance=distance,
        virgin_material_emission_factor=virgin_material_emission_factor,
        processing_emission_factor=processing_emission_factor,
        transport_emission_factor=transport_emission_factor,
        quantity_unit=quantity_unit,
        distance_unit=distance_unit,
        custom_assumptions=custom_assumptions,
        decimals=decimals,
    )
