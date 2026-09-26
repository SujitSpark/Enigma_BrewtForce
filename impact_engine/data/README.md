# India-First Environmental Data Layer Specification

This directory contains the machine-readable dataset and governance specifications for the **India-First Environmental Impact Engine**.

---

## 1. Core Principles & Governance Rules

1. **No Invented Factors**: Every emission factor must be sourced from a verifiable, traceable primary or secondary publication. Guesses and arbitrary midpoints are strictly prohibited.
2. **India-First Policy**: Factors classified as `INDIA_PRIMARY` or `INDIA_SECONDARY` take priority for Indian calculations. International factors (`INTERNATIONAL_REFERENCE`) can **never** be used as default substitutes for Indian baseline calculations.
3. **Traceability**: Missing source metadata (organization, publication title) prevents any factor from being marked as verified.
4. **Gas Basis Preservation**: Direct $\text{CO2}$ and multi-gas $\text{CO2e}$ factors must retain their original published gas basis. Automatic or unverified conversions are rejected.
5. **Range Preservation**: If a primary source publishes a range (min/max), the range is preserved. Arbitrary midpoints are prohibited.
6. **Verification Enforcers**: Any factor marked as `NOT_VERIFIED` is automatically rejected by the calculation engine.

---

## 2. Required Schema Fields for Every Emission Factor

Every factor record in `emission_factors.json` must specify the following 21 fields:

| Field | Type | Description |
|---|---|---|
| `factor_id` | String | Unique machine-readable identifier (e.g., `IND_CEA_GRID_2024`). |
| `factor_name` | String | Human-readable factor title. |
| `value` | Float / Null | Single or central numerical value. Required for `single_value` factors. |
| `minimum_value` | Float / Null | Lower bound for range-valued factors. |
| `maximum_value` | Float / Null | Upper bound for range-valued factors. |
| `value_type` | String | `single_value` or `range`. |
| `unit` | String | Standardized unit string (e.g., `kg CO2 / kWh`, `kg CO2e / tonne`). |
| `gas_basis` | String | `CO2` or `CO2e`. |
| `applicable_material` | String | Target material (e.g., `Electricity / Grid Power`, `Steel`). |
| `applicable_process` | String | Target process (e.g., `Grid Generation`, `Blast Furnace`). |
| `geographic_scope` | String | Specific national/regional code (`India`, `UK`, `USA`). Vague scopes (`Global`) are prohibited. |
| `classification` | String | `INDIA_PRIMARY`, `INDIA_SECONDARY`, `INTERNATIONAL_REFERENCE`, or `NOT_SUITABLE`. |
| `source` | String | Source organization name (e.g., `Central Electricity Authority`). |
| `source_title` | String | Exact publication title. |
| `source_url` | String | Official URL or DOI link. |
| `year` | String / Int | Publication year or version indicator. |
| `methodology` | String | Brief description of calculation methodology. |
| `system_boundary` | String | Exact boundary (e.g., `Stack emissions`, `Cradle-to-gate`). |
| `original_value_text` | String | Verbatim published text from original source. |
| `limitations` | String | Applicability boundaries or exclusions. |
| `verification_status` | String | `VERIFIED_PRIMARY`, `VERIFIED_SECONDARY`, `INTERNATIONAL_REFERENCE`, or `NOT_VERIFIED`. |

---

## 3. Classification & Verification Status Definitions

### Allowed Classifications
- `INDIA_PRIMARY`: Official Government of India dataset (Ministry of Power, CPCB, MoEFCC).
- `INDIA_SECONDARY`: Verified Indian secondary / research institute dataset (CEEW, CSE India, BEE).
- `INTERNATIONAL_REFERENCE`: International benchmark (UK DEFRA, US EPA) kept for explicit reference only.
- `NOT_SUITABLE`: Disqualified or unverified data factor.

### Allowed Verification Statuses
- `VERIFIED_PRIMARY`: Verified against an official government publication.
- `VERIFIED_SECONDARY`: Verified against a peer-reviewed or authoritative research publication.
- `INTERNATIONAL_REFERENCE`: Verified international reference dataset.
- `NOT_VERIFIED`: Unverified or incomplete factor. **Strictly prohibited from calculation engine.**
