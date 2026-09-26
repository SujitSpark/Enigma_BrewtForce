"""
Unit tests for Environmental Impact Calculator, Data Architecture, Dataset Loader,
India-First Policy, Gas Basis Verification (CO2 vs CO2e), and Range-Valued Factors.

Tests unit consistency, external factors, source metadata validation,
calculation correctness, invalid units, missing metadata, negative values,
gas basis matching, range representation, best/worst case range calculation,
emission factor registry management, JSON data loader, and strict India-First selection policy.
"""

import unittest
from impact_engine import (
    EmissionFactor,
    EmissionFactorRegistry,
    EnvironmentalImpactCalculator,
    EnvironmentalImpactResult,
    EnvironmentalImpactRangeResult,
    NoIndiaFactorAvailableError,
    calculate_environmental_impact,
    calculate_environmental_impact_range,
    load_emission_factors,
)


class TestEnvironmentalImpactCalculator(unittest.TestCase):
    """Test suite for Environmental Impact Engine."""

    def setUp(self):
        """Set up standard externally supplied emission factors for testing."""
        self.virgin_factor = EmissionFactor(
            factor_name="Virgin Steel Factor",
            value=2.5,
            unit="kg CO2e / tonne",
            gas_basis="CO2e",
            source="World Steel Association 2022 Report",
            source_url="https://worldsteel.org/data/co2-intensity",
            geographic_scope="UK",
            classification="INTERNATIONAL_REFERENCE",
            applicable_material="Steel",
            year=2022,
        )

        self.processing_factor = EmissionFactor(
            factor_name="Recycled Steel Scrap Processing Factor",
            value=0.5,
            unit="kg CO2e / tonne",
            gas_basis="CO2e",
            source="Ecoinvent v3.9 Database",
            source_url="https://ecoinvent.org",
            geographic_scope="UK",
            classification="INTERNATIONAL_REFERENCE",
            applicable_material="Steel",
            year=2023,
        )

        self.transport_factor = EmissionFactor(
            factor_name="HGV Diesel Freight Transport Factor",
            value=0.01,
            unit="kg CO2e / tonne-km",
            gas_basis="CO2e",
            source="UK DEFRA 2023 Greenhouse Gas Conversion Factors",
            source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023",
            geographic_scope="UK",
            classification="INTERNATIONAL_REFERENCE",
            applicable_material="Freight Transport",
            year=2023,
            is_official_government=True,
        )

    def test_calculation_correctness_external_factors(self):
        """Test calculation accuracy using traceable external emission factors."""
        result = calculate_environmental_impact(
            quantity=10,
            distance=100,
            virgin_material_emission_factor=self.virgin_factor,
            processing_emission_factor=self.processing_factor,
            transport_emission_factor=self.transport_factor,
            quantity_unit="tonne",
            distance_unit="km",
        )

        self.assertIsInstance(result, EnvironmentalImpactResult)
        self.assertEqual(result.virgin_emissions_avoided, 25.0)
        self.assertEqual(result.processing_emissions, 5.0)
        self.assertEqual(result.transport_emissions, 10.0)
        self.assertEqual(result.net_co2e_benefit, 10.0)
        self.assertEqual(result.emissions_gas_basis, "CO2e")
        self.assertTrue(result.is_estimated)
        self.assertIn("CO2e", result.label)

    def test_co2_vs_co2e_mismatch_rejection(self):
        """Test that mixing CO2 and CO2e factors raises ValueError."""
        co2_virgin_factor = EmissionFactor(
            factor_name="CO2 Virgin Factor",
            value=2.0,
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            source="Test Source",
            geographic_scope="India",
        )

        with self.assertRaises(ValueError) as ctx:
            calculate_environmental_impact(
                quantity=10,
                distance=100,
                virgin_material_emission_factor=co2_virgin_factor,
                processing_emission_factor=self.processing_factor,  # CO2e
                transport_emission_factor=self.transport_factor,   # CO2e
            )
        self.assertIn("Mismatched gas basis", str(ctx.exception))

    def test_valid_co2_calculation(self):
        """Test that pure CO2 factor calculations work correctly and report gas_basis='CO2'."""
        f_virgin_co2 = EmissionFactor(
            factor_name="VF CO2", value=2.0, unit="kg CO2 / tonne", gas_basis="CO2", source="Src A", geographic_scope="India"
        )
        f_proc_co2 = EmissionFactor(
            factor_name="PF CO2", value=0.5, unit="kg CO2 / tonne", gas_basis="CO2", source="Src B", geographic_scope="India"
        )
        f_trans_co2 = EmissionFactor(
            factor_name="TF CO2", value=0.01, unit="kg CO2 / tonne-km", gas_basis="CO2", source="Src C", geographic_scope="India"
        )

        result = calculate_environmental_impact(
            quantity=10,
            distance=100,
            virgin_material_emission_factor=f_virgin_co2,
            processing_emission_factor=f_proc_co2,
            transport_emission_factor=f_trans_co2,
        )

        self.assertEqual(result.virgin_emissions_avoided, 20.0)
        self.assertEqual(result.processing_emissions, 5.0)
        self.assertEqual(result.transport_emissions, 10.0)
        self.assertEqual(result.net_co2e_benefit, 5.0)
        self.assertEqual(result.emissions_gas_basis, "CO2")

    def test_rejection_of_unsupported_gas_conversion(self):
        """Test that declaring gas_basis='CO2e' while unit specifies 'kg CO2 / tonne' raises ValueError."""
        mismatched_unit_factor = EmissionFactor(
            factor_name="Bad Gas Label Factor",
            value=1.5,
            unit="kg CO2 / tonne",
            gas_basis="CO2e",
            source="Test Source",
            geographic_scope="India",
        )

        with self.assertRaises(ValueError) as ctx:
            mismatched_unit_factor.validate()
        self.assertIn("conflicts with unit", str(ctx.exception))

    def test_range_valued_factors_handling(self):
        """Test schema validation for range-valued factors and rejection when central value is missing in single mode."""
        range_factor = EmissionFactor(
            factor_name="Coal DRI Steel Range Factor",
            minimum_value=2700.0,
            maximum_value=3100.0,
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            value_type="range",
            original_value_text="2.70 - 3.10 t CO2 / tcs",
            source="CEEW Study 2024",
            geographic_scope="India",
        )
        range_factor.validate()
        self.assertEqual(range_factor.value_type, "range")
        self.assertEqual(range_factor.minimum_value, 2700.0)
        self.assertEqual(range_factor.maximum_value, 3100.0)

        with self.assertRaises(ValueError) as ctx:
            calculate_environmental_impact(
                quantity=10,
                distance=100,
                virgin_material_emission_factor=range_factor,
                processing_emission_factor=range_factor,
                transport_emission_factor=range_factor,
            )
        self.assertIn("range-valued factor", str(ctx.exception))

    def test_calculate_range_mode(self):
        """Test Range-Based Calculation Mode for best-case and worst-case net benefit bounds."""
        rf_virgin = EmissionFactor(
            factor_name="RF Virgin",
            minimum_value=2000.0,
            maximum_value=3000.0,
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            value_type="range",
            source="Src A",
            geographic_scope="India",
        )
        rf_proc = EmissionFactor(
            factor_name="RF Processing",
            minimum_value=400.0,
            maximum_value=600.0,
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            value_type="range",
            source="Src B",
            geographic_scope="India",
        )
        rf_trans = EmissionFactor(
            factor_name="RF Transport",
            minimum_value=0.01,
            maximum_value=0.02,
            unit="kg CO2 / tonne-km",
            gas_basis="CO2",
            value_type="range",
            source="Src C",
            geographic_scope="India",
        )

        res_range = calculate_environmental_impact_range(
            quantity=10,
            distance=100,
            virgin_material_emission_factor=rf_virgin,
            processing_emission_factor=rf_proc,
            transport_emission_factor=rf_trans,
        )

        self.assertIsInstance(res_range, EnvironmentalImpactRangeResult)
        # avoided: min = 10 * 2000 = 20000, max = 10 * 3000 = 30000
        self.assertEqual(res_range.virgin_emissions_avoided_min, 20000.0)
        self.assertEqual(res_range.virgin_emissions_avoided_max, 30000.0)

        # proc: min = 10 * 400 = 4000, max = 10 * 600 = 6000
        self.assertEqual(res_range.processing_emissions_min, 4000.0)
        self.assertEqual(res_range.processing_emissions_max, 6000.0)

        # trans: min = 10 * 100 * 0.01 = 10, max = 10 * 100 * 0.02 = 20
        self.assertEqual(res_range.transport_emissions_min, 10.0)
        self.assertEqual(res_range.transport_emissions_max, 20.0)

        # Worst-case net benefit = 20000 - 6000 - 20 = 13980.0
        self.assertEqual(res_range.net_co2e_benefit_min, 13980.0)

        # Best-case net benefit = 30000 - 4000 - 10 = 25990.0
        self.assertEqual(res_range.net_co2e_benefit_max, 25990.0)
        self.assertEqual(res_range.emissions_gas_basis, "CO2")

    def test_national_average_factor_metadata(self):
        """Test metadata preservation of Ministry of Power CEA national average grid factor."""
        registry = load_emission_factors()
        cea_factor = registry.get("CEA_India_Grid_Electricity_Weighted_Average_2024")

        self.assertEqual(cea_factor.value, 0.710)
        self.assertEqual(cea_factor.unit, "kg CO2 / kWh")
        self.assertEqual(cea_factor.gas_basis, "CO2")
        self.assertEqual(cea_factor.value_type, "single_value")
        self.assertEqual(cea_factor.original_value_text, "0.710 tCO2/MWh")
        self.assertEqual(cea_factor.classification, "INDIA_PRIMARY")
        self.assertTrue(cea_factor.is_official_government)

    def test_data_loader_loads_verified_json_dataset(self):
        """Test that data loader parses emission_factors.json with full schema metadata."""
        registry = load_emission_factors()
        factors = registry.list_factors()
        self.assertGreaterEqual(len(factors), 6)

        defra_steel = registry.get("UK_DEFRA_Virgin_Steel_Production_2023")
        self.assertEqual(defra_steel.gas_basis, "CO2e")
        self.assertEqual(defra_steel.value_type, "single_value")
        self.assertEqual(defra_steel.geographic_scope, "UK")

    def test_missing_source_validation(self):
        """Test that missing source or source_title for verified status raises ValueError."""
        # Missing source organization
        f1 = EmissionFactor(
            factor_id="TEST_01",
            factor_name="Test No Source",
            unit="kg CO2e / tonne",
            source="",
            geographic_scope="India",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx1:
            f1.validate()
        self.assertIn("missing mandatory 'source'", str(ctx1.exception))

        # Verified status missing source_title
        f2 = EmissionFactor(
            factor_id="TEST_02",
            factor_name="Test No Title",
            unit="kg CO2 / kWh",
            source="Ministry of Power",
            source_title="",
            geographic_scope="India",
            classification="INDIA_PRIMARY",
            verification_status="VERIFIED_PRIMARY",
            value=0.71,
            gas_basis="CO2",
        )
        with self.assertRaises(ValueError) as ctx2:
            f2.validate()
        self.assertIn("require a non-empty 'source_title'", str(ctx2.exception))

    def test_missing_geography_validation(self):
        """Test that missing or generic/disallowed geography raises ValueError."""
        # Missing geography
        f1 = EmissionFactor(
            factor_id="TEST_03",
            factor_name="Test No Geography",
            unit="kg CO2e / tonne",
            source="Test Org",
            geographic_scope="",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx1:
            f1.validate()
        self.assertIn("missing mandatory 'geographic_scope'", str(ctx1.exception))

        # Generic disallowed geography
        f2 = EmissionFactor(
            factor_id="TEST_04",
            factor_name="Test Global Geography",
            unit="kg CO2e / tonne",
            source="Test Org",
            geographic_scope="Global",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx2:
            f2.validate()
        self.assertIn("Generic scopes like 'Global'", str(ctx2.exception))

    def test_invalid_classification_validation(self):
        """Test that invalid classification string or classification-geography mismatch raises ValueError."""
        # Invalid classification string
        f1 = EmissionFactor(
            factor_id="TEST_05",
            factor_name="Test Bad Class",
            unit="kg CO2e / tonne",
            source="Test Org",
            geographic_scope="India",
            classification="INVALID_CLASS",
            verification_status="VERIFIED_PRIMARY",
            source_title="Title",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx1:
            f1.validate()
        self.assertIn("invalid classification", str(ctx1.exception))

        # INDIA_PRIMARY but geography is UK
        f2 = EmissionFactor(
            factor_id="TEST_06",
            factor_name="Test Mismatched Class",
            unit="kg CO2e / tonne",
            source="Test Org",
            geographic_scope="UK",
            classification="INDIA_PRIMARY",
            verification_status="VERIFIED_PRIMARY",
            source_title="Title",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx2:
            f2.validate()
        self.assertIn("geographic_scope is 'UK'", str(ctx2.exception))

    def test_invalid_verification_status_validation(self):
        """Test that invalid verification_status string raises ValueError."""
        f = EmissionFactor(
            factor_id="TEST_07",
            factor_name="Test Bad Status",
            unit="kg CO2e / tonne",
            source="Test Org",
            geographic_scope="India",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="SUPER_VERIFIED",
            value=1.0,
        )
        with self.assertRaises(ValueError) as ctx:
            f.validate()
        self.assertIn("invalid verification_status", str(ctx.exception))

    def test_unverified_factor_cannot_be_used(self):
        """Test that factors marked NOT_VERIFIED cannot be registered or used for calculations."""
        unverified_f = EmissionFactor(
            factor_id="TEST_08",
            factor_name="Unverified Factor",
            unit="kg CO2e / tonne",
            source="Unverified Source",
            geographic_scope="India",
            classification="NOT_SUITABLE",
            verification_status="NOT_VERIFIED",
            value=1.5,
        )
        # Cannot be registered in registry
        reg = EmissionFactorRegistry()
        from impact_engine.emission_factor import UnverifiedFactorError
        with self.assertRaises(UnverifiedFactorError):
            reg.register(unverified_f)

        # Cannot be passed to impact calculator
        with self.assertRaises(UnverifiedFactorError):
            calculate_environmental_impact(
                quantity=10,
                distance=100,
                virgin_material_emission_factor=unverified_f,
                processing_emission_factor=self.processing_factor,
                transport_emission_factor=self.transport_factor,
            )

    def test_international_factor_cannot_become_india_default(self):
        """Test that international factors are never selected by default when India geography is requested."""
        registry = load_emission_factors()

        # Querying for India steel when only UK steel exists must raise NoIndiaFactorAvailableError
        with self.assertRaises(NoIndiaFactorAvailableError):
            registry.find_factor(applicable_material="Steel", geography="India", allow_international_fallback=False)

    def test_co2_co2e_metadata_consistency(self):
        """Test that gas_basis metadata strictly matches unit text and cannot be silently mixed."""
        # gas_basis CO2e vs unit kg CO2 / kWh
        f_bad_gas = EmissionFactor(
            factor_id="TEST_09",
            factor_name="Mismatched Unit Gas",
            unit="kg CO2 / kWh",
            gas_basis="CO2e",
            source="Test Org",
            geographic_scope="India",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
            value=0.5,
        )
        with self.assertRaises(ValueError) as ctx:
            f_bad_gas.validate()
        self.assertIn("conflicts with unit", str(ctx.exception))

    def test_range_metadata_consistency(self):
        """Test that range metadata validation requires minimum_value <= maximum_value and non-negative bounds."""
        # Min > Max
        f_bad_range = EmissionFactor(
            factor_id="TEST_10",
            factor_name="Inverted Range Factor",
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            value_type="range",
            minimum_value=3000.0,
            maximum_value=2000.0,
            source="Test Org",
            geographic_scope="India",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
        )
        with self.assertRaises(ValueError) as ctx1:
            f_bad_range.validate()
        self.assertIn("cannot exceed maximum_value", str(ctx1.exception))

        # Missing min/max
        f_missing_bounds = EmissionFactor(
            factor_id="TEST_11",
            factor_name="Missing Bounds Range Factor",
            unit="kg CO2 / tonne",
            gas_basis="CO2",
            value_type="range",
            source="Test Org",
            geographic_scope="India",
            classification="INTERNATIONAL_REFERENCE",
            verification_status="INTERNATIONAL_REFERENCE",
        )
        with self.assertRaises(ValueError) as ctx2:
            f_missing_bounds.validate()
        self.assertIn("must specify both minimum_value and maximum_value", str(ctx2.exception))


if __name__ == "__main__":
    unittest.main()

