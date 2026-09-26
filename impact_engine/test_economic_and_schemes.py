"""
Unit tests for Economic Benefit Engine, Scheme Matching Architecture,
Data Safety Audit, and Synthetic Data Isolation rules.
"""

import unittest
from impact_engine import (
    EconomicBenefitCalculator,
    EconomicBenefitResult,
    calculate_economic_benefit,
    SchemeMatcher,
    ApplicabilityStatus,
    DataClassification,
    EmissionFactor,
    EmissionFactorRegistry,
    load_emission_factors,
    load_synthetic_emission_factors,
    calculate_environmental_impact,
)


class TestEconomicBenefitCalculator(unittest.TestCase):
    """Test suite for Economic Benefit Engine."""

    def test_economic_benefit_calculation_accuracy(self):
        """Test economic formula: Avoided Material Cost + Saved Disposal Cost - Processing Cost - Transport Cost."""
        res = calculate_economic_benefit(
            quantity=10.0,                 # 10 tonnes
            distance=50.0,                 # 50 km (GIS input)
            virgin_material_price=3000.0,  # 3,000 INR/tonne avoided
            disposal_cost=500.0,           # 500 INR/tonne saved
            processing_cost=200.0,         # 200 INR/tonne processing
            transport_cost_per_km=2.0,     # 2 INR/tonne-km transport
            currency="INR",
        )

        self.assertIsInstance(res, EconomicBenefitResult)
        self.assertEqual(res.virgin_material_cost_avoided, 30000.0)
        self.assertEqual(res.waste_disposal_cost_saved, 5000.0)
        self.assertEqual(res.processing_cost, 2000.0)
        self.assertEqual(res.transport_cost, 1000.0)
        self.assertEqual(res.net_economic_benefit, 32000.0)
        self.assertEqual(res.currency, "INR")
        self.assertEqual(res.data_classification, DataClassification.CALCULATED_OUTPUT.value)

    def test_unit_conversion_handling(self):
        """Test unit normalization (kg to tonnes, m to km)."""
        calc = EconomicBenefitCalculator()
        res = calc.calculate(
            quantity=5000.0,               # 5,000 kg = 5 tonnes
            distance=10000.0,              # 10,000 m = 10 km
            virgin_material_price=4000.0,  # INR/tonne
            disposal_cost=1000.0,
            processing_cost=500.0,
            transport_cost_per_km=3.0,
            quantity_unit="kg",
            distance_unit="meter",
        )

        self.assertEqual(res.virgin_material_cost_avoided, 20000.0)
        self.assertEqual(res.waste_disposal_cost_saved, 5000.0)
        self.assertEqual(res.processing_cost, 2500.0)
        self.assertEqual(res.transport_cost, 150.0)
        self.assertEqual(res.net_economic_benefit, 22350.0)

    def test_negative_input_rejection(self):
        """Test that negative quantities, distances, or prices raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_economic_benefit(quantity=-10.0, distance=50.0, virgin_material_price=100.0)

        with self.assertRaises(ValueError):
            calculate_economic_benefit(quantity=10.0, distance=-50.0, virgin_material_price=100.0)

        with self.assertRaises(ValueError):
            calculate_economic_benefit(quantity=10.0, distance=50.0, virgin_material_price=-100.0)


class TestDataSafetyAndSyntheticIsolationAudit(unittest.TestCase):
    """Audit tests verifying data safety, synthetic isolation, and output provenance leakage protection."""

    def test_1_normal_production_loader_does_not_load_synthetic_factors(self):
        """TEST 1: Verify production load_emission_factors() loads strictly verified factors and NO synthetic records."""
        prod_registry = load_emission_factors()
        factors = prod_registry.list_factors()
        self.assertGreater(len(factors), 0)
        for f in factors:
            self.assertFalse(f.is_synthetic, f"Synthetic factor '{f.factor_name}' leaked into production loader.")
            self.assertNotEqual(f.classification, "SYNTHETIC_DEMO")
            self.assertNotEqual(f.verification_status, "SYNTHETIC_DEMO")

    def test_2_synthetic_loader_loads_synthetic_factors(self):
        """TEST 2: Verify synthetic loader loads demo factors and preserves synthetic metadata."""
        synth_registry = load_synthetic_emission_factors()
        factors = synth_registry.list_factors()
        self.assertGreaterEqual(len(factors), 5)

        for f in factors:
            self.assertTrue(f.is_synthetic, f"Factor '{f.factor_name}' in synthetic dataset missing is_synthetic=True.")
            self.assertEqual(f.classification, "SYNTHETIC_DEMO")
            self.assertEqual(f.verification_status, "SYNTHETIC_DEMO")

    def test_3_default_registry_query_excludes_synthetic_factors(self):
        """TEST 3: Verify default registry queries exclude synthetic factors."""
        reg = EmissionFactorRegistry()
        synth_f = EmissionFactor(
            factor_id="SYNTH_SLAG_01",
            factor_name="SYNTHETIC / DEMO Slag",
            unit="kg CO2e / tonne",
            source="Demo Lab",
            geographic_scope="India",
            classification="SYNTHETIC_DEMO",
            verification_status="SYNTHETIC_DEMO",
            applicable_material="Blast Furnace Slag",
            value=1.5,
        )
        reg.register(synth_f)

        results = reg.query(geography="India", applicable_material="Blast Furnace Slag")
        self.assertEqual(len(results), 0, "Synthetic factor returned in standard query without include_synthetic=True.")

    def test_4_synthetic_factor_cannot_claim_verified_status(self):
        """TEST 4: Verify synthetic factors cannot claim VERIFIED_PRIMARY or VERIFIED_SECONDARY status."""
        with self.assertRaises(ValueError) as ctx1:
            f1 = EmissionFactor(
                factor_id="SYNTH_BAD_01",
                factor_name="Bad Synthetic Primary Factor",
                unit="kg CO2e / tonne",
                source="Demo Source",
                geographic_scope="India",
                classification="SYNTHETIC_DEMO",
                verification_status="VERIFIED_PRIMARY",
                value=1.0,
            )
            f1.validate()
        self.assertIn("synthetic factors CANNOT be marked as verified status", str(ctx1.exception))

        with self.assertRaises(ValueError) as ctx2:
            f2 = EmissionFactor(
                factor_id="SYNTH_BAD_02",
                factor_name="Bad Synthetic Secondary Factor",
                unit="kg CO2e / tonne",
                source="Demo Source",
                geographic_scope="India",
                classification="SYNTHETIC_DEMO",
                verification_status="VERIFIED_SECONDARY",
                value=1.0,
            )
            f2.validate()
        self.assertIn("synthetic factors CANNOT be marked as verified status", str(ctx2.exception))

    def test_5_synthetic_factor_cannot_claim_official_government_status(self):
        """TEST 5: Verify synthetic factors cannot claim official government dataset status."""
        with self.assertRaises(ValueError) as ctx:
            f = EmissionFactor(
                factor_id="SYNTH_GOV_BAD",
                factor_name="Fake Official Synthetic Factor",
                unit="kg CO2e / tonne",
                source="Demo Source",
                geographic_scope="India",
                classification="SYNTHETIC_DEMO",
                verification_status="SYNTHETIC_DEMO",
                is_official_government=True,
                value=1.0,
            )
            f.validate()
        self.assertIn("synthetic factors CANNOT be claimed as official government data", str(ctx.exception))

    def test_6_economic_calculation_using_synthetic_inputs_preserves_classification(self):
        """TEST 6: Verify economic calculations using synthetic inputs preserve SYNTHETIC_DEMO_DATA classification."""
        calc = EconomicBenefitCalculator()
        res = calc.calculate(
            quantity=10.0,
            distance=50.0,
            virgin_material_price=3000.0,
            disposal_cost=500.0,
            data_classification=DataClassification.SYNTHETIC_DEMO_DATA.value,
        )

        self.assertEqual(res.data_classification, DataClassification.SYNTHETIC_DEMO_DATA.value)
        self.assertTrue(res.is_synthetic)

    def test_7_economic_calculation_output_contains_demo_disclaimer(self):
        """TEST 7: Verify economic calculation output contains explicit synthetic disclaimer when data is synthetic."""
        res = calculate_economic_benefit(
            quantity=10.0,
            distance=50.0,
            virgin_material_price=3000.0,
            data_classification=DataClassification.SYNTHETIC_DEMO_DATA.value,
        )

        self.assertIsNotNone(res.disclaimer)
        self.assertIn("SYNTHETIC / DEMO DATA", res.disclaimer)
        self.assertIn("disclaimer", res.assumptions)

    def test_8_synthetic_scheme_match_remains_classified_as_synthetic_demo(self):
        """TEST 8: Verify synthetic scheme match results remain classified as SYNTHETIC_DEMO_DATA."""
        matcher = SchemeMatcher()
        results = matcher.match_project(material="Blast Furnace Slag", process="Granulation", quantity_tonnes=100.0)
        self.assertGreater(len(results), 0)

        for match in results:
            self.assertEqual(match.data_classification, DataClassification.SYNTHETIC_DEMO_DATA.value)
            self.assertTrue(match.is_synthetic)

    def test_9_synthetic_scheme_output_does_not_lose_source_disclaimer_classification(self):
        """TEST 9: Verify synthetic scheme output preserves source organization, disclaimer, and classification."""
        matcher = SchemeMatcher()
        results = matcher.match_project(material="Blast Furnace Slag")
        match = results[0]

        self.assertIsNotNone(match.source)
        self.assertGreater(len(match.source), 0)
        self.assertIsNotNone(match.disclaimer)
        self.assertIn("SYNTHETIC / DEMO", match.disclaimer)
        self.assertEqual(match.data_classification, DataClassification.SYNTHETIC_DEMO_DATA.value)

    def test_10_serialization_dictionary_output_preserves_data_classification(self):
        """TEST 10: Verify serialization / dictionary conversion preserves data_classification and disclaimers."""
        # Economic result dict test
        econ_res = calculate_economic_benefit(
            quantity=10.0,
            distance=50.0,
            virgin_material_price=3000.0,
            data_classification=DataClassification.SYNTHETIC_DEMO_DATA.value,
        )
        econ_dict = econ_res.to_dict()
        self.assertEqual(econ_dict["data_classification"], DataClassification.SYNTHETIC_DEMO_DATA.value)
        self.assertTrue(econ_dict["is_synthetic"])
        self.assertIn("SYNTHETIC / DEMO DATA", econ_dict["disclaimer"])

        # Environmental impact result dict test
        synth_f = EmissionFactor(
            factor_id="SYNTH_FACTOR_SER",
            factor_name="SYNTHETIC / DEMO Factor",
            unit="kg CO2e / tonne",
            source="Demo Lab",
            geographic_scope="India",
            classification="SYNTHETIC_DEMO",
            verification_status="SYNTHETIC_DEMO",
            value=1.0,
        )
        env_res = calculate_environmental_impact(
            quantity=10,
            distance=50,
            virgin_material_emission_factor=synth_f,
            processing_emission_factor=synth_f,
            transport_emission_factor=synth_f,
        )
        env_dict = env_res.to_dict()
        self.assertEqual(env_dict["data_classification"], DataClassification.SYNTHETIC_DEMO_DATA.value)
        self.assertTrue(env_dict["is_synthetic"])
        self.assertIn("SYNTHETIC", env_dict["label"])
        self.assertIsNotNone(env_dict["disclaimer"])


class TestGovernmentSchemeMatcher(unittest.TestCase):
    """Test suite for Government Scheme Matching architecture."""

    def test_scheme_matching_potentially_applicable(self):
        """Test project profile satisfying all scheme conditions."""
        matcher = SchemeMatcher()
        results = matcher.match_project(
            material="Blast Furnace Slag",
            process="Granulation",
            quantity_tonnes=100.0,
            distance_km=150.0,
            geography="India",
        )

        self.assertGreaterEqual(len(results), 1)
        pat_match = [r for r in results if "PAT" in r.scheme_name][0]
        self.assertEqual(pat_match.applicability_status, ApplicabilityStatus.POTENTIALLY_APPLICABLE)
        self.assertGreater(len(pat_match.matched_conditions), 0)
        self.assertEqual(len(pat_match.unmet_conditions), 0)
        self.assertIn("SYNTHETIC", pat_match.disclaimer)

    def test_scheme_matching_ineligible(self):
        """Test project profile violating scheme minimum quantity condition."""
        matcher = SchemeMatcher()
        results = matcher.match_project(
            material="Blast Furnace Slag",
            process="Granulation",
            quantity_tonnes=10.0,
            distance_km=150.0,
            geography="India",
        )

        pat_match = [r for r in results if "PAT" in r.scheme_name][0]
        self.assertEqual(pat_match.applicability_status, ApplicabilityStatus.INELIGIBLE)
        self.assertGreater(len(pat_match.unmet_conditions), 0)

    def test_scheme_matching_needs_more_data(self):
        """Test project profile with missing process or distance information."""
        matcher = SchemeMatcher()
        results = matcher.match_project(
            material="Blast Furnace Slag",
            quantity_tonnes=100.0,
        )

        pat_match = [r for r in results if "PAT" in r.scheme_name][0]
        self.assertEqual(pat_match.applicability_status, ApplicabilityStatus.NEEDS_MORE_DATA)
        self.assertGreater(len(pat_match.missing_information), 0)


if __name__ == "__main__":
    unittest.main()
