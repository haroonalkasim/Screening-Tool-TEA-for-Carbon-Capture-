# Architecture — Carbon Capture Screening Tool v1.8.8

This document walks through every functional layer of `carbon_capture_app_v1_8_8.py` in execution order. All function names, class names, and variable names correspond exactly to the code.

---

## Execution flow

```
app startup
    └── load_data()                          loads DataPack from 29 CSV files
            │
user fills sidebar → build_feed_case()
    └── returns FeedCase + Economics + run_clicked
            │
run_engine(db, feed, econ)
    ├── candidate_routes(db, feed)           → list of 27 candidate dicts
    │       ├── regime_score() per route
    │       └── expand by sub-technology
    │
    └── for each candidate → evaluate_route(db, feed, econ, cand)
            ├── evaluate_impurities()        → CAPEX/OPEX multipliers + reject flag
            ├── evaluate_pretreatment()      → pretreatment burden multipliers
            ├── apply_process_context()      → credits/penalties from site context
            ├── evaluate_absorption()        ┐
            ├── evaluate_adsorption()        ├─ family performance model
            ├── evaluate_membrane()          │
            ├── evaluate_cryogenic()         ┘
            ├── build_equipment_train_cost() → itemized equipment CAPEX
            ├── route_utility_intensity()    → steam/electricity/cooling
            ├── replacement_cost_factor()    → annual consumable costs
            ├── downstream_multiplier()      → CO₂ destination burden
            ├── compute CAPEX, OPEX, LCOC, energy, payback
            ├── benchmark_distance()         → proximity to literature anchors
            ├── confidence_score()           → High/Moderate/Low + numeric
            └── compute balanced_score
    │
results sorted by balanced_score (descending)
    │
Streamlit tabs render:
    Overview → render_overview()
    per-family → render_family_tab()
    Summary → render_summary_tab()
```

---

## Module 1 — Data loading

### `DataPack` class

Reads all 29 CSV files from `carbon_capture_master_data_pack_v5/engineering_backbone/` on startup. Stored as pandas DataFrame attributes — full list:

| Attribute | File | Purpose |
|-----------|------|---------|
| `feed_sources` | `feed_sources.csv` | Source archetype metadata |
| `rep_cases` | `feed_source_representative_cases.csv` | Default compositions per archetype |
| `solvents` | `absorption_solvents.csv` | Solvent properties: Q_regen, TRL, burden class |
| `adsorbents` | `adsorbents.csv` | Working capacity, moisture sensitivity, TRL |
| `swing_modes` | `swing_modes.csv` | PSA/TSA/VSA mode definitions |
| `adsorbent_swing` | `adsorbent_swing_compatibility.csv` | Which sorbents are compatible with which swing |
| `membranes` | `membranes.csv` | Permeance GPU, selectivity, stage cut, TRL |
| `cryogenic` | `cryogenic_configs.csv` | Config IDs, CO₂/pressure windows, TRL |
| `route_templates` | `route_templates.csv` | Routes by family and application regime |
| `route_equipment` | `route_equipment_map.csv` | Equipment items per route with trigger logic |
| `equipment_classes` | `equipment_classes.csv` | Equipment class definitions |
| `equipment_cost_anchors` | `equipment_cost_anchors.csv` | Reference cost and scaling basis |
| `equipment_scaling_rules` | `equipment_scaling_rules.csv` | Scaling exponents per class |
| `utility_mapping` | `utility_mapping.csv` | Steam/electricity/cooling intensity per route |
| `replacement_consumables` | `replacement_consumables.csv` | Annual replacement cost factors per family |
| `scope_boundaries` | `scope_boundary_definitions.csv` | TEA scope definitions |
| `tea_norm` | `tea_normalization_rules.csv` | Normalization rules for LCOC comparison |
| `study_scope_mapping` | `study_scope_mapping.csv` | Literature study → scope boundary mapping |
| `product_specs` | `product_spec_targets.csv` | Purity targets by destination |
| `downstream_rules` | `downstream_handling_rules.csv` | CO₂ destination → post-treatment multipliers |
| `benchmark_cases` | `benchmark_cases.csv` | Literature benchmark cases for distance scoring |
| `benchmark_case_tags` | `benchmark_case_tags.csv` | Tags linking benchmarks to sources |
| `validation_sets` | `validation_sets.csv` | Spot-check validation truth sets |
| `confidence_rules` | `confidence_rules.csv` | Confidence rule definitions |
| `impurity_effects` | `impurity_effects.csv` | Per-impurity × per-family thresholds and multipliers |
| `pretreatment_rules` | `pretreatment_rules.csv` | Feed-triggered pretreatment burden |
| `post_treatment_rules` | `post_treatment_rules.csv` | Post-treatment rules |
| `process_context_rules` | `process_context_rules.csv` | Context flag effects |
| `tea_cost_anchors` | `tea_cost_anchors.csv` | TEA sanity anchors per family |
| `tea_studies` | `tea_literature/tea_study_metadata.csv` | Literature study metadata (optional) |
| `tea_metrics` | `tea_literature/tea_extracted_metrics_long.csv` | Extracted TEA metric values (optional) |

### `locate_data_root()`

Searches in order:
1. `CC_DATA_PACK` environment variable
2. Same directory as the script file
3. Current working directory (`Path.cwd()`)
4. `/mnt/data/` (cloud deployment)

### `load_data()`

Decorated with `@st.cache_data` — DataPack is built once per session and cached.

---

## Module 2 — Input dataclasses

### `FeedCase`

All feed properties in one dataclass. Computed properties (not stored fields):

```python
flow_kmol_h         = flow_nm3_h / 22.414
co2_kmol_h          = flow_kmol_h × co2_mol_pct / 100
captured_co2_kmol_h = co2_kmol_h × capture_target_pct / 100
captured_co2_t_h    = captured_co2_kmol_h × 44.01 / 1000
```

### `Economics`

Stores all TEA parameters:
- `carbon_price_eur_t` — carbon price for payback calculation
- `electricity_eur_mwh` — electricity price
- `heat_eur_gj` — heat/steam price
- `cooling_eur_m3` — cooling water price
- `labor_eur_y` — annual labor cost
- `discount_rate_pct` — discount rate for CRF
- `life_years` — project life for CRF
- `maintenance_pct_capex` — maintenance as % of CAPEX/year
- `contingency_pct` — contingency as % of pre-contingency CAPEX
- `op_hours` — operating hours per year

### `build_feed_case(db)`

Renders the Streamlit sidebar. Returns `(FeedCase, Economics, run_button_clicked)`. The Run button is disabled when composition does not sum to 100 mol%.

---

## Module 3 — Route generation

### `regime_score(route_regime, feed)`

Returns float 0–1. Six regime identifiers defined; unknown regimes return 0.7 (moderate applicability assumed). Does **not** hard-exclude routes — the 0.2 floor in `evaluate_route()` does that.

### `candidate_routes(db, feed)`

Iterates over all rows in `route_templates`. For each route, expands into individual options by cross-joining with the relevant technology sub-library:

| Route ID | Cross-join table | Filter |
|----------|-----------------|--------|
| `ROUTE_ABS_MEA` | `db.solvents` | `solvent_family == "chemical"` |
| `ROUTE_ABS_PHYS` | `db.solvents` | `solvent_family == "physical"` |
| `ROUTE_CLR_PHYS` | `db.solvents` | `solvent_family == "physical"` |
| `ROUTE_ADS_PSA` | `db.adsorbents` ∩ `db.adsorbent_swing[swing_mode=="PSA"]` | merge on "adsorbent" |
| `ROUTE_ADS_TSA` | `db.adsorbents` ∩ `db.adsorbent_swing[swing_mode=="TSA"]` | merge on "adsorbent" |
| `ROUTE_MEM_1STAGE` | `db.membranes` | all (stages=1) |
| `ROUTE_MEM_2STAGE` | `db.membranes` | all (stages=2) |
| `ROUTE_CRYO_NICHE` | `db.cryogenic` | all configs |

Total candidates per run: 5 solvents (2 routes × 2 families) + 6 adsorbent-swing pairs + 12 membrane options (6 × 2 stages) + 3 cryo configs = **27 candidates**.

Each candidate dict carries: `route_id`, `family`, `subtechnology_group`, `route_description`, `route_regime_score`, plus family-specific keys (`option_name`, `adsorbent`/`swing_mode`/`membrane`/`stages`/`config_id`).

---

## Module 4 — Feasibility and burden evaluation

### `evaluate_impurities(db, feed, family)`

Reads `db.impurity_effects` filtered to the current family. For each impurity:

```
if val ≥ warning_threshold:
    capex_mult  *= row.capex_multiplier
    opex_mult   *= row.opex_multiplier
    conf_delta  += row.confidence_delta
    pretreat_list.append(row.pretreatment_needed)
if val ≥ reject_threshold:
    reject = True
```

Returns: `(capex_mult, opex_mult, pretreat_list, warnings, reject, conf_delta)`

Impurities checked: H₂O, CO, O₂, H₂S, SOx, NOx, HCl, NH₃, Particulates, HeavyHC — drawn from both `feed.impurities` dict and `feed.co_mol_pct`.

### `evaluate_pretreatment(db, feed, family)`

Reads `db.pretreatment_rules` and evaluates trigger conditions:

| Trigger variable | Feed property |
|-----------------|--------------|
| `temperature_c` | `feed.temperature_c` |
| `H2O_mol_pct` | `feed.h2o_mol_pct` |
| `Particulates_mg_Nm3` | `feed.impurities["Particulates"]` |
| `SOx_or_HCl_present` | `max(SOx, HCl)` |
| `heavy_hc_proxy` | `feed.impurities["HeavyHC"]` |

Comparators supported: `>` and `==`. Returns `(capex_mult, opex_mult, item_list)`.

### `apply_process_context(db, feed, family)`

Reads `db.process_context_rules`. Each row checks a context flag against a trigger value. Unknown values (user left at "unknown") subtract 2 confidence points — explicitly representing incomplete information.

Returns `(capex_mult, opex_mult, conf_delta, notes)`.

### `downstream_multiplier(db, feed, family, purity_shortfall)`

Reads `db.downstream_rules`. Filters on `co2_destination` (storage/utilization/high_purity). The `polishing_for_purity` item is only included when `purity_shortfall=True`.

Returns `(capex_mult, opex_mult, item_list)`.

---

## Module 5 — Family performance models

### `evaluate_absorption(db, feed, econ, cand)`

1. Reads solvent row from `db.solvents` by option_name
2. Computes mid-point regeneration energy
3. Applies physical solvent pressure correction
4. Computes steam_gj_y = regen × captured_tpy
5. Computes elec_mwh_y = captured_tpy × (0.08 + 0.01 × max(P, 1))
6. Sets duty_factor, pressure_factor, area_factor
7. Returns performance dict

### `evaluate_adsorption(db, feed, econ, cand)`

1. Reads adsorbent from `db.adsorbents`
2. Computes q_eff with moisture correction
3. Computes adsorbent mass inventory
4. Sets spec electricity from calibrated per-swing ranges (PSA/TSA/VSA)
5. **Utility map electricity is excluded here** (handled in performance model only, not in `route_utility_intensity()` for adsorption — this prevents the double-counting bug BUG-ADS-1)
6. Computes steam for TSA only
7. Returns performance dict with vacuum_needed, swing_mode, purity_shortfall flags

### `evaluate_membrane(db, feed, econ, cand)`

1. Reads membrane from `db.membranes`
2. Computes permeate purity `y_perm` via solution-diffusion equation
3. Computes recovery and purity with 1- or 2-stage correction
4. Sets `purity_shortfall` and `recovered_shortfall` flags
5. Computes compression electricity as function of pressure ratio
6. Applies 1.5× electricity penalty and 0.75× regime_score at P < 2 bar
7. Returns performance dict

### `evaluate_cryogenic(db, feed, econ, cand)`

1. Reads cryogenic config from `db.cryogenic`
2. **Returns None immediately if P < 6 bar** (hard infeasibility gate)
3. Selects tier (high-CO₂/moderate/outside) for specific electricity
4. Applies +0.12 MWh/t drying penalty if H₂O > 1%
5. Sets pressure_factor = min(2.5, max(0.8, 10/P)) — note cap at 2.5 (BUG-CRYO-1 fix)
6. Returns performance dict

---

## Module 6 — Equipment cost

### `cost_equipment_item(eq_id, feed, duty_factor, pressure_factor, area_factor)`

Maps equipment class ID to a cost formula. Reference values in 2019–2022 EUR using six-tenths rule from Peters & Timmerhaus 2003:

```python
flow_factor = max(feed.flow_nm3_h / 10_000, 0.1)

"EQ_ABSORBER"         → 800_000 × flow_factor^0.65 × pressure_factor
"EQ_STRIPPER"         → 700_000 × flow_factor^0.65
"EQ_REBOILER"         → 550_000 × max(duty_factor, 0.2)^0.70
"EQ_HEX"              → 280_000 × max(duty_factor, 0.2)^0.65
"EQ_ADS_VESSEL"       → 930_000 × max(area_factor, 0.3)^0.65
"EQ_SWITCHING_VALVES" → 350_000 × flow_factor^0.50
"EQ_VACUUM"           → 990_000 × flow_factor^0.60 × pressure_factor
"EQ_MEM_MODULES"      → 150_000 × max(area_factor, 0.3)
"EQ_COLD_BOX"         → 1_300_000 × flow_factor^0.60 × pressure_factor
"EQ_REFRIGERATION"    → 900_000 × max(duty_factor, 0.3)^0.70
"EQ_CO2_EXPORT_COMP"  → 500_000 × max(duty_factor, 0.3)^0.65
# ... (full list in code)
```

Unknown equipment IDs fall back to: `100_000 × flow_factor^0.5`

### `build_equipment_train_cost(db, route_id, feed, perf)`

Reads `db.route_equipment` filtered to the current route_id, sorted by `sequence_no`. For each row, evaluates `trigger_logic`:

| Trigger | Condition |
|---------|-----------|
| `hot_or_wet_flue_gas` | `T > 40°C or H₂O > 3%` |
| `particulates_or_mist_present` | `impurities["Particulates"] > 0` |
| `when_high_water_or_water_sensitive` | `H₂O > 1%` |
| `only_when_reclaiming_needed` | `perf["reclaiming_needed"] == True` |
| `only_for_tsa_variants` | `perf["swing_mode"] == "TSA"` |
| `only_for_vacuum_routes` | `perf["vacuum_needed"] == True` |
| `only_when_2nd_stage_or_recycle` | `perf["stages"] >= 2` |
| `when_polishing_needed` | `perf["purity_shortfall"] == True` |
| `always_if_cryogenic_selected` | always True |
| `always_for_export_scope` | `co2_destination == "storage"` |
| `only_for_clr_shifted_high_pressure` | `source_id == "SRC_CLR" or (P ≥ 10 and H₂ ≥ 15%)` |

Returns `(total_cost, cost_dict)` where `cost_dict` maps equipment_class_id → cost EUR.

---

## Module 7 — Utilities and replacement

### `route_utility_intensity(db, route_id, base_tpy)`

Reads `db.utility_mapping` for the route. Significance class → multiplier:

```
"high"   → 1.00
"medium" → 0.55
"low"    → 0.25
```

Utility intensities per significance level:

| Type | Formula |
|------|---------|
| steam | `base_tpy × 2.2 × sig` |
| electricity | `base_tpy × 0.18 × sig` (**excluded for adsorption**) |
| cooling_water | `base_tpy × 0.60 × sig` |
| refrigeration_power | `base_tpy × 0.28 × sig` (**excluded for adsorption**) |

**Critical:** For adsorption routes, electricity contributions from the utility map are NOT applied — the performance model handles electricity directly (BUG-ADS-1 fix). Adsorption cooling is still taken from the utility map.

### `replacement_cost_factor(db, family, subtech, base_capex)`

Reads `db.replacement_consumables` filtered to family. For each row:

```
factor += 0.005 + 0.01 × classify_significance(sig_class)
```

Returns `factor × base_capex` EUR/year.

---

## Module 8 — TEA assembly in `evaluate_route()`

Full sequence for one candidate:

```
1. Feasibility check: route_regime_score < 0.2 → return None
2. evaluate_impurities()    → (ic, io, ip, iw, ir, iconf)
3. if ir and family in [cryogenic, membrane] → return None
4. evaluate_pretreatment()  → (pc, po, pt)
5. apply_process_context()  → (cc, co, cconf, cnotes)
6. performance model        → perf dict
7. regime_score adjustments:
      membrane at P < 2:     elec × 1.5; rrs × 0.75
      adsorption at P < 2.5 and H₂O > 3%: rrs × 0.8
      cryogenic at P < 6:    return None
      cryogenic at CO₂ < 20%: rrs × 0.6
      cryogenic at CO₂ ≥ 40, P ≥ 12, dry: rrs × 1.1
8. downstream_multiplier()  → (dc, do, downstream_items)
9. build_equipment_train_cost() → (eq_capex, eq_items)
10. CAPEX = eq_capex × (ic×pc×cc×dc) × (1 + cont/100)
11. Utility mapping          → (steam_u, elec_u, cool_u)
12. Merge utilities with performance model (adsorption: use perf only for elec/steam)
13. OPEX = (elec×pe + steam×ph + cool×pc + repl + maint + labor) × (io×po×co×do)
14. captured_tpy = feed.captured_co2_t_h × op_hours
15. annualized_capex = CAPEX × CRF(discount, life)
16. LCOC = (annualized_capex + OPEX) / captured_tpy
17. energy_gj_t = (elec×3.6 + steam) / captured_tpy
18. benchmark_distance()
19. confidence_score()
20. technical_fit = 35×rrs + 25×(1-min(bdist,1)) + 20×(TRL/9) + 20×(no-purity-shortfall)
21. return full result dict (30+ keys)
```

### `run_engine(db, feed, econ)`

Calls `evaluate_route()` for all 27 candidates. Filters `None` results. Computes `balanced_score` for each. Returns list sorted descending by `balanced_score`.

---

## Module 9 — Balanced score

$$S = 0.32 \cdot \frac{100}{1+\text{LCOC}/80} + 0.15 \cdot \frac{100}{1+E/3} + 0.24 \cdot T_{\text{fit}} + 0.12 \cdot \frac{\text{TRL}}{9}\cdot100 + 0.17 \cdot C$$

Weights deliberate — see THEORY.md §12 for rationale.

---

## Module 10 — Rendering

### Overview tab — `render_overview()`

- Banner with top route name, LCOC, energy, confidence
- 4 metrics (balanced score, LCOC, energy, confidence)
- Case summary table + metric explanation table
- Family comparison table from `family_best()`
- Cost ranking chart and energy ranking chart (horizontal bar, Plotly)
- Screening disclaimer

### Family tabs — `render_family_tab(results, family, db)`

- 6 metrics (route, score, LCOC, energy, confidence, payback)
- Benchmark consistency card (distance label + nearest IDs)
- "Why this route" expander with `why_selected` bullets
- Technical summary table (fit, energy, capture, OPEX, CAPEX ann., payback, TRL + perf dict values)
- Candidate table (top 8 options in family, sorted by balanced_score)
- Pretreatment/impurity expander
- Post-treatment/context expander
- CAPEX donut chart (core equipment / integration / contingency)
- Equipment CAPEX drivers chart (top 8 items, horizontal bar)
- OPEX breakdown expander (donut + table)
- Nearest benchmarks expander (from `db.benchmark_cases`)
- Literature anchors expander (from `db.tea_studies`)
- Assumptions expander

### Summary tab — `render_summary_tab()`

- Explains the tab purpose
- Calls `build_summary_sections()` → deterministic executive + technical text
- AI rewriting toggle (optional, requires OPENAI_API_KEY in environment)
- Executive summary card + technical summary card
- Family best table
- Conceptual PFD (`render_conceptual_pfd()`)
- Report text area (full 15-section Markdown report via `build_detailed_report_markdown()`)
- Download buttons (.md and .txt)
- Reference and benchmark note expander

### `render_conceptual_pfd(result)`

Auto-generates a horizontal block diagram from the equipment train. Pretreatment items shown as labelled steps before the main equipment; post-treatment items after. No user interaction — purely display.

### `build_detailed_report_markdown()`

Builds a 15-section Markdown report:
1. Executive summary
2. Technical summary
3. Input case (all feed parameters)
4. Selected route snapshot
5. Best route by family table
6. Candidate routes within family
7. Conceptual process flow (numbered steps)
8. Triggered pretreatment
9. Triggered post-treatment
10. CAPEX component view
11. Equipment CAPEX drivers
12. Annual OPEX breakdown
13. Nearest benchmark cases
14. Relevant literature anchors
15. Notes and scope caveats

All numbers come directly from the result dict — no language model required for the default path.

---

## Module 11 — Helper utilities

| Function | Purpose |
|----------|---------|
| `payback_label(years)` | Format payback year string including `>100 y` and `None` cases |
| `money(x)` | Format EUR value as `€1.2M`, `€450k`, `€12,000` |
| `crf(rate_pct, years)` | Capital recovery factor |
| `classify_significance(sig)` | "high" → 1.0, "medium" → 0.55, else 0.25 |
| `html_table(df, index, max_rows)` | Render DataFrame as styled HTML table |
| `label_source_name(db, source_id)` | Look up human-readable source name |
| `render_string_list_table(items, col_name)` | Render a list as a one-column HTML table |
| `generic_assumptions(best, family)` | Return list of scope limitation notes per family |
| `benchmark_rows(db, ids)` | Retrieve benchmark case rows by ID list |
| `literature_rows(db, family)` | Retrieve TEA study rows for a given family |
| `family_best(results)` | Return DataFrame of best route per family |
| `conceptual_equipment_train(result)` | Build ordered equipment step list for PFD |
| `_df_to_markdown(df, max_rows)` | Convert DataFrame to Markdown table string |

---

*For equation derivations: see [THEORY.md](THEORY.md)*  
*For database schema: see [DATABASE.md](DATABASE.md)*  
*For validation results: see [VALIDATION.md](VALIDATION.md)*
