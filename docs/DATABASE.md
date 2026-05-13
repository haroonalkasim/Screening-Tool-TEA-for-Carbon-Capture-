# Database V5 — Schema and Column Definitions

`carbon_capture_master_data_pack_v5/engineering_backbone/` contains 29 CSV files. Every parameter that drives model behaviour is stored here. All values trace to `references_master.csv`.

---

## Feed sources

### `feed_sources.csv`

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | string | Unique identifier (e.g. `SRC_CEMENT`) |
| `source_name` | string | Human-readable name (e.g. `cement_flue_gas`) |
| `sector` | string | Industrial sector |
| `likely_impurities` | string | Comma-separated impurities typical of this source |
| `notes` | string | Free-text notes |

### `feed_source_representative_cases.csv`

Default feed compositions displayed when user selects a source archetype.

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | string | Foreign key → `feed_sources.source_id` |
| `flow_nm3_h` | float | Reference volumetric gas flow (Nm³/h) |
| `pressure_bar` | float | Feed pressure (bar abs) |
| `temperature_c` | float | Feed temperature (°C) |
| `co2_mol_pct` | float | CO₂ mole fraction (mol%) |
| `h2_mol_pct` | float | H₂ mole fraction (mol%) |
| `n2_mol_pct` | float | N₂ mole fraction (mol%) |
| `ch4_mol_pct` | float | CH₄ mole fraction (mol%) |
| `co_mol_pct` | float | CO mole fraction (mol%) |
| `h2o_mol_pct` | float | H₂O mole fraction (mol%) |

---

## Technology libraries

### `absorption_solvents.csv`

One row per solvent. Drives `evaluate_absorption()`.

| Column | Type | Description |
|--------|------|-------------|
| `solvent` | string | Solvent name (`MEA`, `Selexol`, etc.) |
| `solvent_family` | string | `chemical` or `physical` |
| `best_pressure_regime` | string | Natural operating pressure window |
| `steam_dependency` | string | `high` / `medium` / `low` |
| `regen_gj_t_min` | float | Minimum regeneration energy (GJ/tCO₂) |
| `regen_gj_t_max` | float | Maximum regeneration energy (GJ/tCO₂) |
| `delta_loading_min` | float | Minimum cyclic loading capacity (mol CO₂/mol amine) |
| `delta_loading_max` | float | Maximum cyclic loading capacity |
| `degradation_burden` | string | `high` / `medium` / `low` |
| `reclaiming_burden` | string | `high` / `medium` / `low` — triggers `EQ_SOLVENT_RECLAIMER` |
| `complexity_class` | string | Process complexity |
| `cooling_dependency` | string | `high` → 0.70 m³/t cooling factor; else 0.35 |
| `trl` | int | Technology Readiness Level (1–9) |
| `notes` | string | Key literature references |

**Value sources:**  
MEA range (3.5–4.2 GJ/t): Nwaoha 2018 IJGGC; Roussanaly 2017 GHGT-13; Kohl & Nielsen 1997.  
Selexol range (0.8–1.5 GJ/t): Meerman 2012 IJGGC; Emis-VITO Selexol TEA.  
Rectisol range (0.5–1.2 GJ/t): Kohl & Nielsen 1997.

### `adsorbents.csv`

One row per sorbent material. Drives `evaluate_adsorption()`.

| Column | Type | Description |
|--------|------|-------------|
| `adsorbent` | string | Sorbent name |
| `class` | string | `zeolite` / `carbon` / `amine_functionalized` |
| `effective_working_capacity_min_mol_per_kg` | float | Minimum usable CO₂ capacity (mol/kg) |
| `effective_working_capacity_max_mol_per_kg` | float | Maximum usable CO₂ capacity (mol/kg) |
| `pressure_sensitivity` | string | Sensitivity of capacity to pressure |
| `moisture_sensitivity` | string | `high` / `medium` / `low` — drives capacity penalty |
| `regen_heat_class` | string | Thermal regeneration burden class |
| `cost_class` | string | Relative material cost |
| `lifetime_years` | float | Expected sorbent lifetime (years) |
| `trl` | int | Technology Readiness Level |
| `notes` | string | |

**Value sources:** Riboldi & Bolland 2017 (Energy Procedia, 319 citations); Chisalita et al. 2024 (I&ECR, TNO); Samanta et al. 2012 (I&ECR review, DOI: 10.1021/ie200686q).

### `adsorbent_swing_compatibility.csv`

| Column | Type | Description |
|--------|------|-------------|
| `adsorbent` | string | Foreign key → `adsorbents.adsorbent` |
| `swing_mode` | string | `PSA`, `TSA`, `VSA`, `PVSA` |
| `notes` | string | Compatibility rationale |

### `swing_modes.csv`

| Column | Type | Description |
|--------|------|-------------|
| `swing_mode` | string | Mode identifier |
| `mode_class` | string | `pressure` / `thermal` / `vacuum` |
| `heat_required` | bool | Whether thermal energy is needed for regeneration |
| `vacuum_required` | bool | Whether vacuum is needed |
| `notes` | string | |

### `membranes.csv`

One row per membrane material. Drives `evaluate_membrane()`.

| Column | Type | Description |
|--------|------|-------------|
| `membrane` | string | Membrane name |
| `class` | string | `polymeric` / `mixed_matrix` / `metal_H2_selective` / `ceramic` |
| `permeance_gpu_min` | float | Minimum CO₂ permeance (GPU) |
| `permeance_gpu_max` | float | Maximum CO₂ permeance (GPU) |
| `selectivity_min` | float | Minimum CO₂/N₂ or CO₂/CH₄ ideal selectivity α |
| `selectivity_max` | float | Maximum selectivity |
| `max_stage_cut_min` | float | Minimum stage cut θ (fraction) |
| `max_stage_cut_max` | float | Maximum stage cut |
| `best_pressure_regime` | string | Natural pressure operating window |
| `replacement_years` | float | Module replacement interval (years) |
| `trl` | int | Technology Readiness Level |
| `notes` | string | |

**Value sources:** Wijmans & Baker 1995; Zhai & Rubin 2013 (ES&T); Concawe 2025; NETL membrane programme publications.

### `cryogenic_configs.csv`

One row per cryogenic configuration. Drives `evaluate_cryogenic()`.

| Column | Type | Description |
|--------|------|-------------|
| `config_id` | string | Configuration identifier |
| `class` | string | `cryogenic_standalone` / `cryogenic_polishing` / `hybrid_membrane_cryogenic` |
| `best_co2_regime` | string | CO₂ concentration window |
| `best_pressure_regime` | string | Pressure window |
| `co2_mol_pct_min` | float | Minimum applicable CO₂ concentration (mol%) |
| `co2_mol_pct_max` | float | Maximum applicable CO₂ concentration (mol%) |
| `dryness_requirement` | string | `mandatory` for all cryogenic configs |
| `complexity_class` | int | Complexity score |
| `trl` | int | Technology Readiness Level |
| `notes` | string | |

**Value sources:** Varnier et al. 2025 (CET); Voldsund et al. 2019 (Energies); Bouma et al. 2017 (GHGT-13).

---

## Route structure

### `route_templates.csv`

One row per route. Defines which technology family and regime a route belongs to.

| Column | Type | Description |
|--------|------|-------------|
| `route_id` | string | Unique route identifier (e.g. `ROUTE_ABS_MEA`) |
| `family` | string | `absorption` / `adsorption` / `membrane` / `cryogenic` |
| `subtechnology` | string | Sub-technology group |
| `application_regime` | string | Regime identifier used in `regime_score()` |
| `description` | string | Human-readable route description |
| `complexity_class` | string | Process complexity |
| `downstream_note` | string | Key downstream conditioning requirement |
| `ref_ids` | string | Semicolon-separated reference IDs |

Available routes in V5:

| route_id | family | regime |
|----------|--------|--------|
| `ROUTE_ABS_MEA` | absorption | `low_pressure_flue_gas` |
| `ROUTE_ABS_PHYS` | absorption | `high_pressure_precombustion_or_sweetening` |
| `ROUTE_ADS_PSA` | adsorption | `high_pressure_dry_gas` |
| `ROUTE_ADS_TSA` | adsorption | `low_to_medium_pressure_dry_gas` |
| `ROUTE_MEM_1STAGE` | membrane | `medium_to_high_pressure_moderate_purity` |
| `ROUTE_MEM_2STAGE` | membrane | `medium_to_high_pressure_higher_recovery` |
| `ROUTE_CRYO_NICHE` | cryogenic | `high_co2_high_pressure_dry_feed` |
| `ROUTE_CLR_PHYS` | absorption | `high_pressure_CLR_shifted_gas` |

### `route_equipment_map.csv`

Defines which equipment items belong to each route, and when they are included.

| Column | Type | Description |
|--------|------|-------------|
| `route_id` | string | Foreign key → `route_templates.route_id` |
| `sequence_no` | int | Processing order within the route |
| `equipment_class_id` | string | Foreign key → `equipment_classes.equipment_class_id` |
| `inclusion_type` | string | `mandatory` or `conditional` |
| `trigger_logic` | string | Condition identifier (see `build_equipment_train_cost()` for all values) |
| `cost_importance` | string | Relative cost significance |
| `energy_importance` | string | Relative energy significance |
| `notes` | string | |

---

## Equipment

### `equipment_classes.csv`

Defines the complete vocabulary of equipment class IDs.

| Column | Type | Description |
|--------|------|-------------|
| `equipment_class_id` | string | Unique ID (e.g. `EQ_ABSORBER`) |
| `class_name` | string | Human-readable name |
| `category` | string | `core` / `pretreatment` / `post_treatment` / `utility` |
| `notes` | string | |

### `equipment_cost_anchors.csv`

Reference costs and scaling parameters for each equipment class.

| Column | Type | Description |
|--------|------|-------------|
| `anchor_id` | string | Equipment anchor identifier |
| `anchor_type` | string | `equipment_capex_anchor` / `pretreatment_anchor` / `post_treatment_anchor` / `energy_anchor_gj_t` |
| `scope` | string | Equipment scope description |
| `relative_anchor` | float | Relative cost multiplier (1.0 = reference) |
| `scaling_basis` | string | Scaling variable description |
| `notes` | string | |
| `ref_ids` | string | Semicolon-separated reference IDs |

### `equipment_scaling_rules.csv`

Scaling exponents and reference capacities.

| Column | Type | Description |
|--------|------|-------------|
| `equipment_class_id` | string | Foreign key → `equipment_classes` |
| `scaling_exponent` | float | Power-law exponent (typically 0.5–0.7) |
| `reference_flow_nm3_h` | float | Reference capacity for normalization |
| `notes` | string | |

---

## Utilities and consumables

### `utility_mapping.csv`

Utility intensity per route, used in `route_utility_intensity()`.

| Column | Type | Description |
|--------|------|-------------|
| `route_id` | string | Foreign key → `route_templates` |
| `utility_type` | string | `steam` / `electricity` / `cooling_water` / `refrigeration_power` / `heat` |
| `significance_class` | string | `very_high` (not standard) / `high` / `medium` / `low` → mapped to 1.0/0.55/0.25 |
| `notes` | string | |
| `ref_ids` | string | Reference IDs |

**Important:** Electricity utility entries for adsorption routes (`ROUTE_ADS_PSA`, `ROUTE_ADS_TSA`) are **not applied** in the code to avoid double-counting with the performance model.

### `replacement_consumables.csv`

Annual replacement and consumable costs per family.

| Column | Type | Description |
|--------|------|-------------|
| `family` | string | Technology family |
| `subtechnology_group` | string | Sub-technology group |
| `consumable_or_replacement` | string | Item description (e.g. `solvent_makeup`, `membrane_modules`) |
| `significance_class` | string | `high` / `medium` / `low` → 0.015 / 0.0105 / 0.006 per year of CAPEX |
| `ref_ids` | string | |

---

## Feasibility logic

### `impurity_effects.csv`

Per-impurity, per-family effects on cost and feasibility.

| Column | Type | Description |
|--------|------|-------------|
| `impurity` | string | Impurity name (`H2O`, `SOx`, `H2S`, `Particulates`, etc.) |
| `family` | string | Affected technology family |
| `trigger_units` | string | Units of the trigger value |
| `warning_threshold` | float | Value above which multipliers apply |
| `reject_threshold` | float | Value above which route is rejected |
| `mechanism` | string | Description of the degradation mechanism |
| `capex_multiplier` | float | CAPEX scaling factor when triggered (>1 = penalty) |
| `opex_multiplier` | float | OPEX scaling factor when triggered |
| `pretreatment_needed` | string | Required pretreatment step |
| `confidence_delta` | int | Points added to confidence score (typically negative) |

### `pretreatment_rules.csv`

Feed-condition-triggered pretreatment burden.

| Column | Type | Description |
|--------|------|-------------|
| `rule_id` | string | Rule identifier |
| `trigger_variable` | string | Feed property to check (`temperature_c`, `H2O_mol_pct`, `SOx_ppm`, etc.) |
| `comparator` | string | `>` or `==` |
| `trigger_value` | float/string | Threshold value |
| `affected_families` | string | Semicolon-separated families (or `all`) |
| `pretreatment` | string | Pretreatment item triggered |
| `capex_multiplier` | float | CAPEX scaling factor |
| `opex_multiplier` | float | OPEX scaling factor |

### `post_treatment_rules.csv`

Post-treatment triggered by feed quality or product spec requirements.

### `process_context_rules.csv`

Site-context flag effects.

| Column | Type | Description |
|--------|------|-------------|
| `rule_id` | string | Rule identifier |
| `context_variable` | string | Context key (e.g. `steam_available`) |
| `value_type` | string | Data type |
| `trigger_value` | string | Value that triggers the rule (e.g. `yes`, `no`) |
| `affected_families` | string | Semicolon-separated families (or `all`) |
| `capex_multiplier` | float | CAPEX adjustment |
| `opex_multiplier` | float | OPEX adjustment |
| `confidence_delta` | int | Confidence adjustment |
| `effect_logic` | string | Human-readable explanation |

### `downstream_handling_rules.csv`

Post-capture conditioning based on CO₂ destination.

| Column | Type | Description |
|--------|------|-------------|
| `rule_id` | string | |
| `co2_destination` | string | `storage` / `utilization_standard` / `high_purity` / `any` |
| `affected_families` | string | |
| `downstream_unit` | string | Equipment item triggered (e.g. `co2_dehydration`, `polishing_for_purity`) |
| `requirement_level` | string | `mandatory` / `conditional` |
| `capex_multiplier` | float | |
| `opex_multiplier` | float | |

---

## TEA anchors

### `tea_cost_anchors.csv`

TEA sanity bands and reference anchors used for confidence scoring and literature validation.

| Column | Type | Description |
|--------|------|-------------|
| `anchor_id` | string | Anchor identifier |
| `anchor_type` | string | `equipment_capex_anchor` / `energy_anchor_gj_t` / `benchmark_anchor` |
| `scope` | string | Technology or equipment scope |
| `relative_anchor` | float | Relative scaling anchor (1.0 = reference) |
| `scaling_basis` | string | What the anchor scales against |
| `notes` | string | |
| `ref_ids` | string | Reference IDs |

Energy sanity anchors in the database:

| Family | Anchor GJ/t | Stated range |
|--------|------------|-------------|
| absorption | 3.0 | 2–5 |
| adsorption | 1.5 | 1–3 |
| membrane | 2.0 | 1–4 |
| cryogenic | 2.5 | 1.5–5.5 |

### `tea_normalization_rules.csv`

Rules for normalising LCOC values across studies with different scope boundaries.

### `scope_boundary_definitions.csv`

Defines what is included/excluded in each TEA scope.

### `study_scope_mapping.csv`

Maps literature studies to their scope boundary definitions.

---

## Benchmarks and validation

### `benchmark_cases.csv`

Known literature cases used for benchmark distance scoring.

| Column | Type | Description |
|--------|------|-------------|
| `benchmark_id` | string | Unique identifier |
| `source_id` | string | Feed source archetype |
| `flow_nm3_h` | float | Reference flow |
| `pressure_bar` | float | Feed pressure |
| `temperature_c` | float | Feed temperature |
| `co2_mol_pct` | float | CO₂ concentration |
| `h2_mol_pct` | float | H₂ concentration |
| `n2_mol_pct` | float | N₂ concentration |
| `ch4_mol_pct` | float | CH₄ concentration |
| `co_mol_pct` | float | CO concentration |
| `h2o_mol_pct` | float | H₂O concentration |
| `capture_target_pct` | float | Capture target (%) |
| `product_purity_pct` | float | Product purity target (%) |
| `expected_family` | string | Expected winning technology family |
| `expected_subtechnology` | string | Expected sub-technology |
| `confidence` | string | Confidence level of benchmark |
| `notes` | string | Key literature source and conditions |
| `ref_ids` | string | Semicolon-separated reference IDs |

Available benchmark cases (V5):

| ID | Conditions | Expected winner |
|----|-----------|----------------|
| `BM_CEMENT_ME` | 24% CO₂, 1.1 bar, 90% capture | absorption/MEA |
| `BM_CCGT_MEA` | 8% CO₂, 1.05 bar, 90% capture | absorption/MEA |
| `BM_COAL_MEA` | 13% CO₂, 1.05 bar, 90% capture | absorption/MEA |
| `BM_BIOGAS_MEM` | 40% CO₂, 4 bar, 90% capture | membrane/2-stage |
| `BM_NGS_PHYS` | 5% CO₂, 50 bar, 90% capture | absorption/Selexol |
| `BM_PRECOMB_PHYS` | 35% CO₂, 30 bar, 90% capture | absorption/physical |
| `BM_PRECOMB_MEM` | 35% CO₂, 30 bar, H₂-selective | membrane/Pd-Ag |
| `BM_BFG_STEP` | 24% CO₂, 1.5 bar, 85% capture | adsorption/SEWGS |
| `BM_ADS_DILUTE` | 6% CO₂, 1.2 bar, 80% capture | adsorption/TSA |
| `BM_CRYO_NICHE` | 45% CO₂, 25 bar, 90% capture | cryogenic |
| `BM_CLR_PHYS` | 45% CO₂, 15 bar, CLR proxy | absorption/physical |

### `benchmark_case_tags.csv`

Tags linking benchmark cases to specific literature studies.

### `validation_sets.csv`

Spot-check validation truth sets used for credibility testing.

### `confidence_rules.csv`

Explicit rules defining confidence score adjustments.

---

## Product specifications

### `product_spec_targets.csv`

| Column | Type | Description |
|--------|------|-------------|
| `destination` | string | `storage` / `utilization_standard` / `high_purity` |
| `co2_min_pct` | float | Minimum required CO₂ purity (%) |
| `h2o_max_ppm` | float | Maximum H₂O (ppm) |
| `notes` | string | Reference specification |

### `species_properties.csv`

Physical properties of key species used in unit conversions.

---

## TEA literature (tea_literature/)

### `tea_study_metadata.csv`

One row per published TEA study in the literature backbone.

| Column | Type | Description |
|--------|------|-------------|
| `study_id` | string | Unique study identifier |
| `country_scope` | string | Country/region of the study |
| `source_type` | string | `peer-reviewed journal` / `institutional report` / etc. |
| `peer_reviewed` | string | `yes` / `no` |
| `title` | string | Full study title |
| `authors_org` | string | Authors and institution |
| `year` | int | Publication year |
| `journal_or_report` | string | Journal or report name |
| `approx_citations` | float | Approximate citation count |
| `technology_family` | string | Primary technology family |
| `sub_technology` | string | Sub-technology covered |
| `application_sector` | string | Industrial sector |
| `primary_region` | string | Applicable region |
| `key_value_scope` | string | What the study quantifies |
| `credibility_tier` | string | `A` (peer-reviewed) / `B` (institutional) |
| `eligibility_note` | string | Why this study is included |
| `source_locator` | string | URL or DOI |
| `locator_confidence` | string | `Exact URL` / `Exact DOI` / `Needs DOI verification` |

### `tea_extracted_metrics_long.csv`

Extracted numerical values from each study in long format.

| Column | Type | Description |
|--------|------|-------------|
| `study_id` | string | Foreign key → `tea_study_metadata` |
| `parameter_name` | string | Parameter identifier (e.g. `co2_avoided_cost`) |
| `value_num` | float | Numerical value |
| `value_text` | string | Textual value (for non-numeric parameters) |
| `units` | string | Units of the parameter |
| `scenario_basis` | string | Which scenario the value applies to |
| `notes` | string | Extraction notes |
| `extraction_confidence` | string | `High` / `Medium` / `Low` |

---

## `references_master.csv`

Top-level reference index — every `ref_id` used anywhere in the database must appear here.

| Column | Type | Description |
|--------|------|-------------|
| `reference_id` | string | Unique identifier used throughout CSV files |
| `title` | string | Full reference title |
| `year` | float | Publication year |
| `region` | string | Geographic scope |
| `source_type` | string | `peer-reviewed journal` / `institutional report` / `EU project report` / etc. |
| `source_locator` | string | URL or DOI |
| `locator_confidence` | string | `Exact URL` / `Exact DOI` / `Needs DOI verification` |

Key references in V5:

| ID | Title (abbreviated) | Year | Type |
|----|---------------------|------|------|
| `EU_CONCAWE_2025_REVIEW` | Review of CC technologies | 2025 | Institutional |
| `NLD_MEERMAN_2012_SMR_DOI` | TEA CO₂ capture at SMR | 2012 | Peer-reviewed |
| `ITA_EU_ROUSSANALY_2017_CEMENT_MEA` | TEA cement MEA GHGT-13 | 2017 | Peer-reviewed |
| `CAN_NWAOHA_2018_CEMENT` | TEA AMP-PZ-MEA vs MEA cement | 2018 | Peer-reviewed |
| `EU_CEMCAP_2019_COMPARATIVE` | CEMCAP comparative synthesis | 2019 | EU project |
| `ITA_VARSIER_2025_CRYO_CEMENT` | Cryogenic CO₂ cement | 2025 | Peer-reviewed |
| `NLD_TNO_CHISALITA_2024_ADS` | Monolithic adsorption TEA | 2024 | Peer-reviewed |
| `ITA_RIBOLDI_2017_PSA_REVIEW` | PSA/VSA/TSA review | 2017 | Peer-reviewed |
| `NLD_ITALY_SEWGS_2013_NGCC` | SEWGS economic assessment | 2013 | Peer-reviewed |
| `ITA_DELENA_2019_CALCIUM_LOOPING` | Calcium looping cement | 2019 | Peer-reviewed |
| `NLD_BOUNA_2017_MEM_CRYO` | Membrane-cryo hybrid cement | 2017 | Peer-reviewed |
| `USA_NETL_2023_INDUSTRIAL_COST` | NETL industrial CC cost | 2023 | Institutional |
| `EU_GARDARSDOTTIR_2019_CEMENT_COST` | CEMCAP Part 2 cost analysis | 2019 | Peer-reviewed |
