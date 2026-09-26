"""
Economic Benefit Calculator Module.

Calculates the net financial benefit of industrial symbiosis material substitution:

Net Economic Benefit =
    Virgin Material Cost Avoided
  + Waste Disposal Cost Saved
  - Processing Cost
  - Transport Cost

All unit prices and distance values are explicit input parameters (e.g. from GIS routing),
never hardcoded assumptions.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

from .units import parse_mass_unit, parse_distance_unit
from .data_classification import DataClassification, SYNTHETIC_DATA_DISCLAIMER


@dataclass(frozen=True)
class EconomicBenefitResult:
    """
    Structured result returned by the Economic Benefit Calculator.

    Attributes:
        virgin_material_cost_avoided (float): Financial savings from avoided virgin material purchase.
        waste_disposal_cost_saved (float): Financial savings from avoided landfill/tipping disposal fees.
        processing_cost (float): Total processing cost incurred for byproduct preparation/beneficiation.
        transport_cost (float): Total transportation cost incurred based on distance.
        net_economic_benefit (float): Total net economic benefit (savings minus costs).
        currency (str): Currency code (e.g. 'INR').
        assumptions (dict): Audit log of input unit rates, quantity, distance, and unit conversions.
        data_classification (str): Data traceability tag (e.g. 'CALCULATED_OUTPUT' or 'SYNTHETIC_DEMO_DATA').
        is_synthetic (bool): Flag indicating if calculation is based on synthetic/demo data.
        disclaimer (str, optional): Explicit legal / data policy disclaimer.
    """
    virgin_material_cost_avoided: float
    waste_disposal_cost_saved: float
    processing_cost: float
    transport_cost: float
    net_economic_benefit: float
    currency: str = "INR"
    assumptions: Dict[str, Any] = field(default_factory=dict)
    data_classification: str = DataClassification.CALCULATED_OUTPUT.value
    is_synthetic: bool = False
    disclaimer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation preserving provenance."""
        return asdict(self)


class EconomicBenefitCalculator:
    """
    Calculator engine for evaluating the economic benefit of industrial symbiosis material reuse.
    """

    def calculate(
        self,
        quantity: float,
        distance: float,
        virgin_material_price: float,
        disposal_cost: float = 0.0,
        processing_cost: float = 0.0,
        transport_cost_per_km: float = 0.0,
        quantity_unit: str = "tonne",
        distance_unit: str = "km",
        currency: str = "INR",
        data_classification: str = DataClassification.USER_PROVIDED_DATA.value,
        is_synthetic: bool = False,
    ) -> EconomicBenefitResult:
        """
        Calculate economic benefit from material substitution.

        Args:
            quantity (float): Material quantity.
            distance (float): Transport distance (accepted as input, e.g. from GIS module).
            virgin_material_price (float): Virgin material purchase price per quantity_unit.
            disposal_cost (float): Avoided waste disposal/tipping fee per quantity_unit.
            processing_cost (float): Byproduct processing/beneficiation cost per quantity_unit.
            transport_cost_per_km (float): Freight cost per quantity_unit per distance_unit.
            quantity_unit (str): Unit of quantity (default 'tonne').
            distance_unit (str): Unit of distance (default 'km').
            currency (str): Currency identifier (default 'INR').
            data_classification (str): Data classification tag.
            is_synthetic (bool): Explicit synthetic flag.

        Returns:
            EconomicBenefitResult: Financial breakdown of savings and costs with explicit data classification.

        Raises:
            ValueError: If negative quantities, distances, or prices are supplied.
            TypeError: If numerical inputs are non-numeric.
        """
        # Type & Numeric Validation
        for name, val in [
            ("quantity", quantity),
            ("distance", distance),
            ("virgin_material_price", virgin_material_price),
            ("disposal_cost", disposal_cost),
            ("processing_cost", processing_cost),
            ("transport_cost_per_km", transport_cost_per_km),
        ]:
            if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
                raise TypeError(f"Economic benefit input '{name}' must be numeric (got {val}).")
            if val < 0:
                raise ValueError(f"Economic benefit input '{name}' cannot be negative (got {val}).")

        # Normalize units to tonnes and km
        _, mass_to_kg = parse_mass_unit(quantity_unit)
        qty_tonnes = (quantity * mass_to_kg) / 1000.0

        _, dist_to_km = parse_distance_unit(distance_unit)
        dist_km = distance * dist_to_km

        # Financial Calculations
        material_cost_avoided = qty_tonnes * virgin_material_price
        disposal_saved = qty_tonnes * disposal_cost
        proc_cost = qty_tonnes * processing_cost
        trans_cost = qty_tonnes * dist_km * transport_cost_per_km

        net_benefit = material_cost_avoided + disposal_saved - proc_cost - trans_cost

        # Determine Synthetic Status & Provenance
        synth_flag = (
            is_synthetic
            or data_classification in {DataClassification.SYNTHETIC_DEMO_DATA.value, "SYNTHETIC_DEMO"}
        )
        res_classification = (
            DataClassification.SYNTHETIC_DEMO_DATA.value
            if synth_flag
            else DataClassification.CALCULATED_OUTPUT.value
        )
        res_disclaimer = SYNTHETIC_DATA_DISCLAIMER if synth_flag else None

        assumptions = {
            "input_quantity": quantity,
            "quantity_unit": quantity_unit,
            "normalized_quantity_tonnes": qty_tonnes,
            "input_distance": distance,
            "distance_unit": distance_unit,
            "normalized_distance_km": dist_km,
            "virgin_material_price_per_unit": virgin_material_price,
            "disposal_cost_per_unit": disposal_cost,
            "processing_cost_per_unit": processing_cost,
            "transport_cost_per_unit_km": transport_cost_per_km,
            "input_data_classification": data_classification,
        }
        if synth_flag:
            assumptions["disclaimer"] = SYNTHETIC_DATA_DISCLAIMER

        return EconomicBenefitResult(
            virgin_material_cost_avoided=round(material_cost_avoided, 2),
            waste_disposal_cost_saved=round(disposal_saved, 2),
            processing_cost=round(proc_cost, 2),
            transport_cost=round(trans_cost, 2),
            net_economic_benefit=round(net_benefit, 2),
            currency=currency,
            assumptions=assumptions,
            data_classification=res_classification,
            is_synthetic=synth_flag,
            disclaimer=res_disclaimer,
        )


def calculate_economic_benefit(
    quantity: float,
    distance: float,
    virgin_material_price: float,
    disposal_cost: float = 0.0,
    processing_cost: float = 0.0,
    transport_cost_per_km: float = 0.0,
    quantity_unit: str = "tonne",
    distance_unit: str = "km",
    currency: str = "INR",
    data_classification: str = DataClassification.USER_PROVIDED_DATA.value,
    is_synthetic: bool = False,
) -> EconomicBenefitResult:
    """Helper function to execute economic benefit calculation."""
    calculator = EconomicBenefitCalculator()
    return calculator.calculate(
        quantity=quantity,
        distance=distance,
        virgin_material_price=virgin_material_price,
        disposal_cost=disposal_cost,
        processing_cost=processing_cost,
        transport_cost_per_km=transport_cost_per_km,
        quantity_unit=quantity_unit,
        distance_unit=distance_unit,
        currency=currency,
        data_classification=data_classification,
        is_synthetic=is_synthetic,
    )
