# Theory — Carbon Capture Screening Tool v1.8.8

Every equation below is derived from and traceable to a named peer-reviewed or institutional source. Parameters read directly from Database V5 CSV files are shown with their source column name.

---

## 1. Feed characterisation

Converting volumetric flow to molar basis:

$$\dot{n}_{\text{total}} = \frac{\dot{V}_{\text{feed}}}{22.414} \quad \left[\frac{\text{kmol}}{\text{h}}\right] \qquad (0°\text{C}, 1\text{ atm reference})$$

CO₂ molar flow and captured flow:

$$\dot{n}_{\text{CO}_2} = \dot{n}_{\text{total}} \cdot \frac{y_{\text{CO}_2}}{100}$$

$$\dot{n}_{\text{cap}} = \dot{n}_{\text{CO}_2} \cdot \frac{\eta_{\text{cap}}}{100}$$

$$\dot{m}_{\text{cap}} = \dot{n}_{\text{cap}} \cdot \frac{44.01}{1000} \quad \left[\frac{\text{t}}{\text{h}}\right]$$

CO₂ partial pressure (used for physical solvent applicability check):

$$p_{\text{CO}_2} = P_{\text{feed}} \cdot \frac{y_{\text{CO}_2}}{100} \quad [\text{bar}]$$

---

## 2. Regime scoring

Each route template carries an `application_regime` string. The regime score $s_r \in [0, 1]$ modulates technical fit and confidence — it does not hard-exclude routes (the 0.2 floor in `evaluate_route()` does that).

| Regime | In-window condition | $s_r$ in-window | $s_r$ out |
|--------|--------------------|-----------------|-----------:|
| `low_pressure_flue_gas` | $P \leq 2$ bar AND $y_{\text{CO}_2} \leq 30\%$ | 1.0 | 0.60 |
| `high_pressure_precombustion_or_sweetening` | $P \geq 8$ bar AND $y_{\text{CO}_2} \geq 15\%$ | 1.0 | 0.45 |
| `moderate_pressure_dry_gas` | $P \geq 3$ bar, $y_{\text{H}_2\text{O}} \leq 3\%$, $8\% \leq y_{\text{CO}_2} \leq 50\%$ | 1.0 | 0.55 |
| `pressure_assisted_modular` | $P \geq 4$ bar AND $y_{\text{CO}_2} \geq 10\%$ | 1.0 | 0.50 |
| `niche_high_co2_high_pressure` | $P \geq 8$ bar AND $y_{\text{CO}_2} \geq 25\%$ | 1.0 | 0.20 |
| `clr_shifted_high_pressure` | $P \geq 10$ bar AND $y_{\text{H}_2} \geq 15\%$ | 1.0 | 0.35 |

**Literature basis:** Concawe 2025 (Report 25/11) defines post-combustion flue gas as 3–20 vol% CO₂ at near-atmospheric pressure and sets the minimum CO₂ partial pressure for physical solvent applicability at 300 kPa (3 bar). Meerman 2012 (IJGGC, DOI: 10.1016/j.ijggc.2012.02.018) anchors the high-pressure pre-combustion/sweetening regime at 18–40% CO₂ and 15–30 bar.

---

## 3. Absorption

### 3.1 Solvent database values

From `absorption_solvents.csv`:

| Solvent | Family | Q_min (GJ/t) | Q_max (GJ/t) | δ_load_min | δ_load_max | TRL |
|---------|--------|-------------|-------------|-----------|-----------|-----|
| MEA | chemical | 3.5 | 4.2 | 0.22 | 0.30 | 9 |
| MDEA | chemical | 2.2 | 3.0 | 0.25 | 0.35 | 9 |
| MDEA+PZ | chemical_blend | 2.4 | 3.0 | 0.28 | 0.36 | 8 |
| Selexol | physical | 0.8 | 1.5 | 0.50 | 0.90 | 9 |
| Rectisol | physical | 0.5 | 1.2 | 0.60 | 1.10 | 9 |

**Literature basis for MEA range (3.5–4.2 GJ/t):**  
Nwaoha et al. 2018 (IJGGC 78, 362–375) reports MEA regeneration energy at cement conditions. Kohl & Nielsen, *Gas Purification* 5th ed. (1997) remains the classical reference for amine regeneration energy components (reaction heat, latent heat of steam, sensible heat). Roussanaly et al. 2017 (GHGT-13 / Energy Procedia 114) confirms the 3.5–4.0 GJ/t range for MEA at cement post-combustion.

**Literature basis for Selexol range (0.8–1.5 GJ/t):**  
Meerman 2012 anchors physical absorption at SMR conditions. Concawe 2025 and the Emis-VITO Selexol TEA confirm that flash regeneration at high pCO₂ requires minimal heat. The 1.5 penalty factor applies when the solvent is used below its natural pressure window.

### 3.2 Regeneration energy

$$Q_{\text{regen}} = \frac{Q_{\min} + Q_{\max}}{2} \quad [\text{GJ/tCO}_2]$$

### 3.3 Physical solvent pressure correction

Physical solvents regenerate by pressure-swing; at low pCO₂ they require supplemental stripping energy:

$$Q_{\text{phys}} = Q_{\text{regen}} \times \begin{cases} 0.85 & P \geq 8\text{ bar and } y_{\text{CO}_2} \geq 15\% \\ 1.45 & \text{otherwise} \end{cases}$$

The 0.85 factor (15% saving vs mid-point) reflects flash regeneration efficiency at high pCO₂ (Meerman 2012: ADIP-X at 20 bar, 18% CO₂). The 1.45 factor (45% penalty) reflects the energy cost of supplemental stripping when feed pCO₂ < 3 bar, where physical solvents are outside their natural operating window (Concawe 2025 §3).

Chemical solvent minor adjustment at moderate conditions:

$$Q_{\text{chem,low-P}} = Q_{\text{regen}} \times 0.95 \quad \text{if } P < 2\text{ bar and } y_{\text{CO}_2} < 15\%$$

### 3.4 Steam, electricity, cooling demands

Annual steam duty:

$$\dot{Q}_{\text{steam}} = Q_{\text{regen}} \cdot \dot{m}_{\text{cap,annual}} \quad [\text{GJ/y}]$$

Electricity (pumps, blowers, instrumentation):

$$\dot{W}_{\text{elec}} = \dot{m}_{\text{cap,annual}} \cdot (0.08 + 0.01 \cdot \max(P, 1)) \quad [\text{MWh/y}]$$

The 0.08 MWh/t base covers solvent circulation pumps and instrumentation (IEAGHG 2014/03 range: 0.10–0.15 MWh/t; the lower value used because compression to export is added separately as a downstream item).

Cooling water:

$$\dot{V}_{\text{cool}} = \dot{m}_{\text{cap}} \cdot \begin{cases} 0.70 & \text{cooling dependency = high (MEA)} \\ 0.35 & \text{otherwise} \end{cases} \quad [\text{m}^3/\text{tCO}_2]$$

### 3.5 Performance factors for equipment sizing

Duty factor (proxy for heat exchanger and reboiler sizing):

$$f_{\text{duty}} = \max\!\left(0.3,\; \frac{\dot{Q}_{\text{steam}}}{\text{op\_hours} \times 5}\right)$$

Pressure factor (for absorber shell thickness — physical solvent only):

$$f_{\text{pressure}} = \max(0.8,\; P/5)$$

Area factor (for column sizing — proportional to volumetric gas flow):

$$f_{\text{area}} = \max(\dot{V}_{\text{feed}} / 10{,}000,\; 0.5)$$

---

## 4. Adsorption

### 4.1 Sorbent database values

From `adsorbents.csv`:

| Sorbent | q_min (mol/kg) | q_max (mol/kg) | Moisture sensitivity | TRL |
|---------|---------------|---------------|---------------------|-----|
| Zeolite 13X | 2.0 | 3.0 | high | 9 |
| Activated Carbon | 1.0 | 2.0 | medium | 9 |
| Amine Solid | 1.5 | 2.6 | high | 7 |

**Literature basis:** Riboldi & Bolland 2017 (Energy Procedia 114, 319 citations) provides the consolidated parameter ranges for PSA/VSA/TSA for CO₂ capture. Chisalita et al. 2024 (I&ECR, TNO) calibrates monolithic Zeolite 13X/Activated Carbon adsorber performance including moisture sensitivity effects.

### 4.2 Effective working capacity

$$q_{\text{mid}} = \frac{q_{\min} + q_{\max}}{2} \quad [\text{mol/kg}]$$

Moisture correction (Riboldi 2017 review — wet flue gas capacity reduction):

$$q_{\text{eff}} = q_{\text{mid}} \times \begin{cases} 0.55 & \text{sensitivity = high and } y_{\text{H}_2\text{O}} > 3\% \\ 0.75 & \text{sensitivity = medium and } y_{\text{H}_2\text{O}} > 5\% \\ 1.00 & \text{otherwise} \end{cases}$$

### 4.3 Adsorbent inventory

$$m_{\text{ads}} = \frac{\dot{n}_{\text{cap}} \cdot 1000 \cdot t_{\text{service}}}{q_{\text{eff}}} \quad [\text{kg}]$$

where $\dot{n}_{\text{cap}}$ is in kmol/h (hence ×1000 to mol/h) and service times are:

| Swing mode | $t_{\text{service}}$ (h) |
|------------|------------------------|
| PSA | 1.3 |
| TSA | 2.4 |

**Basis:** Commercial PSA cycles for CO₂ capture run 2–6 min per bed (Riboldi 2017); the 1.3 h value is an equivalent inventory factor across multiple beds. TSA thermal cycles are significantly slower (Chisalita 2024 reports column counts of 133 per train for a 800 MW reference).

### 4.4 Specific electricity — calibrated values

The electricity demand is set from literature calibration, not first-principles:

**PSA** — *Riboldi 2017 review; Chisalita 2024 TNO monolith study:*

$$W_{\text{PSA}} \in [0.35,\; 0.55] \text{ MWh/tCO}_2, \quad W_{\text{base}} = 0.42$$

Adjustments: +0.08 MWh/t if $P < 2$ bar (added feed compression); +0.04 MWh/t if $y_{\text{H}_2\text{O}} > 4\%$ (moisture handling overhead).

**TSA** — *Chisalita 2024 TNO; Displace 2025 concept study (Netherlands/EU):*

$$W_{\text{TSA,elec}} \in [0.45,\; 0.70] \text{ MWh/tCO}_2, \quad W_{\text{base}} = 0.55$$

$$Q_{\text{TSA,steam}} = 1.8 \cdot \dot{m}_{\text{cap,annual}} \quad [\text{GJ/y}]$$

**VSA/PVSA** — *Riboldi 2017 VSA section:*

$$W_{\text{VSA}} \in [0.50,\; 0.85] \text{ MWh/tCO}_2, \quad W_{\text{base}} = 0.62$$

**Literature anchor check:** Chisalita 2024 reports 5% LCOE reduction and 11% footprint reduction for monolithic vs packed-bed at 800 MW reference. The paper's electricity consumption range for post-combustion TSA is 0.5–0.7 MWh/t — directly matching our TSA range.

**Critical fix from v1.8.3:** Utility map electricity for adsorption is **excluded** in `route_utility_intensity()` to avoid double-counting with the performance model values above. This was the primary cause of adsorption winning 83% of stress-test cases in v1.8.3 (documented bug BUG-ADS-1).

### 4.5 Area factor for vessel sizing

$$f_{\text{area}} = \max\!\left(\frac{m_{\text{ads}}}{7{,}000},\; 0.55\right)$$

---

## 5. Membrane

### 5.1 Membrane database values

From `membranes.csv`:

| Membrane | Permeance (GPU) | Selectivity α | Stage cut θ | TRL |
|----------|----------------|--------------|------------|-----|
| Cellulose Acetate | 800–1500 | 20–35 | 0.35–0.45 | 9 |
| Polysulfone | 600–1000 | 20–30 | 0.30–0.40 | 9 |
| Polaris-type | 1500–2500 | 30–40 | 0.40–0.55 | 8 |
| Mixed Matrix | 1800–2800 | 35–50 | 0.40–0.55 | 6 |
| Pd-Ag H₂-selective | 50–200 | 30–100 | 0.10–0.30 | 6 |
| Ceramic CO₂-selective | 300–800 | 10–30 | 0.20–0.35 | 5 |

**Literature basis:** Wijmans & Baker 1995 (J. Membr. Sci. 107) establishes the solution-diffusion framework. Cellulose acetate data from Zhai & Rubin 2013 (ES&T, DOI: 10.1021/es3050604) and Concawe 2025 review. Polaris-type data from NETL membrane programme publications.

### 5.2 Permeate composition — solution-diffusion model

From Wijmans & Baker 1995, two-component pressure-normalised form:

$$y_{\text{perm}} = \frac{\alpha \cdot x_{\text{CO}_2}}{1 + (\alpha - 1)\cdot x_{\text{CO}_2}}$$

where $\alpha = P_{\text{CO}_2}/P_{\text{N}_2}$ (or $P_{\text{CO}_2}/P_{\text{CH}_4}$ for sweetening), $x_{\text{CO}_2}$ = feed mole fraction, and $\alpha$ and $\theta$ are mid-point values from the database.

### 5.3 Recovery and purity

$$r = \min\!\left(0.98,\; \theta_{\text{mid}} \cdot \frac{c_{\text{stage}}}{x_{\text{CO}_2}}\right), \quad c_{\text{stage}} = \begin{cases} 1.10 & \text{2-stage} \\ 0.75 & \text{1-stage} \end{cases}$$

$$p = \min(0.99,\; y_{\text{perm}} \cdot c_{\text{stage}})$$

`purity_shortfall = True` if $p \cdot 100 < \text{purity\_target}$ or $r \cdot 100 < \text{capture\_target}$. This flag triggers downstream polishing in the TEA.

**Concawe 2025 check:** Two-stage polymeric membranes achieve 80–85 vol% CO₂ product purity for post-combustion flue gas. With CA membrane ($\alpha \approx 27$, $x_{\text{CO}_2} = 0.13$): $y_{\text{perm}} = (27 \times 0.13)/(1 + 26 \times 0.13) = 3.51/4.38 = 0.80$, consistent with the 80–85% range.

### 5.4 Compression electricity

Driving force is the CO₂ partial pressure difference across the membrane. When feed is at low pressure (post-combustion), a blower/compressor creates the required pressure ratio:

$$W_{\text{elec}} = \dot{m}_{\text{cap,annual}} \cdot \left(0.25 + 0.12\ln\!\left(\max\!\left(1.1,\; \frac{8}{P_{\text{feed}}}\right)\right) + 0.12 \cdot \mathbf{1}_{\text{2-stage}}\right) \quad [\text{MWh/y}]$$

**Derivation of constants:** The 0.25 base is the minimum electrical energy for compression + instrumentation at the reference pressure ratio. The 0.12 × ln(8/P) term is the marginal electricity of gas-phase compression following polytropic work: $W \propto \ln(r_P)$, calibrated to IEAGHG post-combustion membrane review (0.4–0.7 MWh/t at 1.05 bar feed). The 0.12 per stage accounts for interstage compression in the two-stage configuration.

Sensitivity check: At $P = 1.05$ bar: $W = 0.25 + 0.12 \ln(7.62) = 0.25 + 0.25 = 0.50$ MWh/t (1-stage) — matches IEAGHG range midpoint.  
At $P = 50$ bar: $W = 0.25 + 0.12 \ln(1.1) = 0.25 + 0.01 = 0.26$ MWh/t — feed pressure provides driving force naturally.

Low-pressure penalty: when $P < 2$ bar, elec ×1.5 and regime_score ×0.75 (additional blower/fan duty).

### 5.5 Area factor for module sizing

$$f_{\text{area}} = \max\!\left(\frac{\dot{n}_{\text{cap}} \cdot 1000/3600}{\text{perm}_{\text{mid}} \cdot P_{\text{feed}} \cdot 0.02},\; 0.4\right)$$

where permeance is in GPU and the denominator approximates the effective transmembrane CO₂ partial pressure driving force.

---

## 6. Cryogenic

### 6.1 Configuration database values

From `cryogenic_configs.csv`:

| Config | CO₂ range (mol%) | Pressure regime | Dryness required | TRL |
|--------|-----------------|-----------------|------------------|-----|
| CRYO_NICHE_HIGHCO2 | 25–95 | high | mandatory | 8 |
| CRYO_POLISHING | 15–60 | high | mandatory | 7 |
| CRYO_MEM_HYBRID | 10–50 | medium–high | mandatory | 6 |

### 6.2 Specific electricity — three-tier model

Anchored to Varnier et al. 2025 (*Cleaner Engineering and Technology*): 90% capture of cement flue gas (24% CO₂, 1.1 bar) achieved with **1.19 MJ_el/kgCO₂ = 0.331 MWh/tCO₂**.

| Tier condition | $W_{\text{elec}}$ (MWh/tCO₂) | Literature anchor |
|----------------|-------------------------------|-------------------|
| $P \geq 12$ bar AND $y_{\text{CO}_2} \geq 40\%$ AND dry | **0.38** | Varnier 2025 extrapolated high-CO₂; IEAGHG 2008 oxyfuel CPU |
| $P \geq 8$ bar AND $y_{\text{CO}_2} \geq 25\%$ | **0.58** | CEMCAP MAL (Bouma 2017, GHGT-13); CEMCAP comparative |
| All other feasible ($P \geq 6$ bar) | **0.90** | Varnier 2025 atmospheric cement case with compression overhead |

Drying penalty: $+0.12$ MWh/tCO₂ when $y_{\text{H}_2\text{O}} > 1\%$ (feed dehydration energy for freeze-out prevention).

**Why 0.38 for the high-CO₂ tier:** At 40%+ CO₂ and 12+ bar, CO₂ liquefaction requires significantly less compression energy than dilute feed cases. IEAGHG 2008 cement oxyfuel study shows that ~80% CO₂ dry flue gas from an oxyfuel kiln is purified in a simple CPU at ~0.33–0.40 MWh/tCO₂.

**Why 0.90 for the outside-niche tier:** Varnier 2025 reports 0.331 MWh/t for the atmospheric cement case, but this already includes an optimised process design. Adding the compression burden to reach liquefaction pressure from atmospheric feed (approximately +0.55 MWh/t) gives ~0.88 MWh/t, rounded to 0.90.

### 6.3 Hard infeasibility gate

```python
if feed.pressure_bar < 6.0:
    return None  # route excluded — not evaluated
```

**Justification:** No published peer-reviewed study demonstrates cryogenic as the economic winner for CO₂ capture from atmospheric or near-atmospheric feed streams without a preceding pre-concentration step. Varnier 2025 notes that electricity price sensitivity means cryogenic only outperforms MEA at moderate electricity prices — at atmospheric pressure, the specific energy penalty is too large. The 6 bar threshold is conservative (below the 8 bar regime score threshold) to avoid excluding legitimate high-pressure cases.

### 6.4 Pressure factor for cold-box sizing

$$f_P^{\text{cryo}} = \min\!\left(2.5,\; \max\!\left(0.8,\; \frac{10}{P_{\text{feed}}}\right)\right)$$

**Fix from v1.8.3 (BUG-CRYO-1):** Without the 2.5 cap, at 1.1 bar the factor reached 9.1, inflating cold-box cost by 9×. The cap at 2.5 reflects the maximum CAPEX uplift for refrigeration-duty compression observed in CEMCAP comparative study — a physically reasonable upper bound for the compression and cold-box oversizing.

---

## 7. Impurity and pretreatment multipliers

The impurity effects database (`impurity_effects.csv`) defines per-impurity, per-family thresholds:

| Column | Meaning |
|--------|---------|
| `warning_threshold` | Value above which cost multipliers apply |
| `reject_threshold` | Value above which route is excluded (for sensitive families) |
| `capex_multiplier` | CAPEX scaling factor |
| `opex_multiplier` | OPEX scaling factor |
| `confidence_delta` | Points added/subtracted from confidence score |

All multipliers are read directly from the database — no model equations here. The compound effect is:

$$C_{\text{CAPEX,eff}} = C_{\text{CAPEX}} \cdot \prod_i f_{\text{imp},i} \cdot \prod_j f_{\text{pre},j} \cdot \prod_k f_{\text{ctx},k} \cdot \prod_l f_{\text{ds},l}$$

$$C_{\text{OPEX,eff}} = C_{\text{OPEX}} \cdot \prod_i g_{\text{imp},i} \cdot \prod_j g_{\text{pre},j} \cdot \prod_k g_{\text{ctx},k} \cdot \prod_l g_{\text{ds},l}$$

---

## 8. Equipment cost scaling

All equipment costs follow the six-tenths rule (Peters & Timmerhaus 2003):

$$C(Q) = C_{\text{ref}} \cdot \left(\frac{Q}{Q_{\text{ref}}}\right)^{0.65}$$

Reference costs from `route_equipment_map.csv` and `equipment_cost_anchors.csv`, calibrated to 2019–2022 European euros using CEMCAP (Voldsund 2019; Gardarsdottir 2019) and NETL 2023 cost bases.

Key equipment cost functions (EUR, $\dot{V}$ in Nm³/h, factors from performance model):

| Equipment | Formula |
|-----------|---------|
| Absorber | $8 \times 10^5 \cdot (\dot{V}/10{,}000)^{0.65} \cdot f_P$ |
| Stripper | $7 \times 10^5 \cdot (\dot{V}/10{,}000)^{0.65}$ |
| Reboiler | $5.5 \times 10^5 \cdot \max(f_{\text{duty}}, 0.2)^{0.70}$ |
| Adsorber vessel | $9.3 \times 10^5 \cdot \max(f_{\text{area}}, 0.3)^{0.65}$ |
| Vacuum system | $9.9 \times 10^5 \cdot (\dot{V}/10{,}000)^{0.60} \cdot f_P$ |
| Membrane modules | $1.5 \times 10^5 \cdot \max(f_{\text{area}}, 0.3)$ |
| Cold box | $1.3 \times 10^6 \cdot (\dot{V}/10{,}000)^{0.60} \cdot f_P^{\text{cryo}}$ |
| Refrigeration | $9.0 \times 10^5 \cdot \max(f_{\text{duty}}, 0.3)^{0.70}$ |
| CO₂ export compressor | $5.0 \times 10^5 \cdot \max(f_{\text{duty}}, 0.3)^{0.65}$ |

---

## 9. TEA — full LCOC calculation

### 9.1 Total installed CAPEX

$$C_{\text{CAPEX}} = \underbrace{\sum_i C_{\text{equip},i}}_{\text{equipment train}} \times \underbrace{f_{\text{imp}} \cdot f_{\text{pre}} \cdot f_{\text{ctx}} \cdot f_{\text{ds}}}_{\text{burden multipliers}} \times \underbrace{\left(1 + \frac{c_{\text{cont}}}{100}\right)}_{\text{contingency}}$$

Integration overhead is tracked separately: $C_{\text{integration}} = \max(C_{\text{CAPEX,pre}} - C_{\text{equipment}},\; 0)$

### 9.2 Annual OPEX

$$C_{\text{OPEX}} = \Big(\underbrace{W_{\text{elec}} \cdot p_e}_{\text{electricity}} + \underbrace{\dot{Q}_{\text{steam}} \cdot p_h}_{\text{heat}} + \underbrace{\dot{V}_{\text{cool}} \cdot p_c}_{\text{cooling}} + \underbrace{C_{\text{repl}}}_{\text{consumables}} + \underbrace{C_{\text{CAPEX}} \cdot m/100}_{\text{maintenance}} + \underbrace{C_{\text{labor}}}_{\text{labor}}\Big) \cdot g_{\text{imp}} \cdot g_{\text{pre}} \cdot g_{\text{ctx}} \cdot g_{\text{ds}}$$

where $m$ = maintenance rate (% of CAPEX/y), default 3%.

### 9.3 Capital recovery factor

$$\text{CRF}(d, n) = \frac{d(1+d)^n}{(1+d)^n - 1}, \quad d = d_{\%}/100$$

Default: $d = 8\%$, $n = 25$ years → CRF = 0.0937.

### 9.4 Levelised cost of capture

$$\text{LCOC} = \frac{\text{CRF} \cdot C_{\text{CAPEX}} + C_{\text{OPEX}}}{\dot{m}_{\text{cap,annual}}} \quad \left[\frac{\text{EUR}}{\text{tCO}_2}\right]$$

### 9.5 Specific energy demand

$$E_{\text{specific}} = \frac{W_{\text{elec}} \cdot 3.6 + \dot{Q}_{\text{steam}}}{\dot{m}_{\text{cap,annual}}} \quad \left[\frac{\text{GJ}}{\text{tCO}_2}\right]$$

### 9.6 Simple payback

$$t_{\text{payback}} = \frac{C_{\text{CAPEX}}}{C_{\text{gross}} - C_{\text{OPEX}}} \quad [\text{y}], \quad C_{\text{gross}} = \dot{m}_{\text{cap,annual}} \cdot p_{\text{carbon}}$$

Returns `None` when $C_{\text{gross}} \leq C_{\text{OPEX}}$.

---

## 10. Benchmark distance

Three-dimensional normalised distance from the nearest literature benchmark case in `benchmark_cases.csv`:

$$d_{\text{bench}} = \left|\frac{y_{\text{CO}_2} - y_{\text{CO}_2}^{\text{bm}}}{100}\right| + \left|\frac{P - P^{\text{bm}}}{\max(P, 1)}\right| + \left|\frac{\eta_{\text{cap}} - \eta_{\text{cap}}^{\text{bm}}}{100}\right|$$

The minimum distance over all benchmarks in the same family is used. Distance < 0.2 means the feed is well inside the benchmark envelope; > 0.6 means significant extrapolation.

---

## 11. Confidence scoring

$$C = \text{clip}\!\left(65 + \sum_i \Delta_i,\; 5,\; 95\right)$$

| Signal | Δ | Basis |
|--------|---|-------|
| Regime score ≥ 0.75 (in preferred window) | +8 | Feed clearly within route design space |
| Regime score < 0.75 | −6 | Route applied outside its natural operating regime |
| Benchmark distance < 0.2 | +8 | Very close to a literature-validated anchor point |
| Benchmark distance > 0.6 | −8 | Substantial extrapolation from any known benchmark |
| TRL ≥ 8 | +8 | Commercial or near-commercial deployment evidence |
| TRL = 7 | +4 | Pilot-scale demonstration |
| TRL ≤ 6 | −6 | Lab or concept stage only |
| Purity shortfall | −5 | Route cannot meet product specification without polishing |
| Regime score < 0.5 | −8 | Additional penalty for severely mis-matched regime |
| Impurity/context delta | from database | Read from `impurity_effects.csv`, `process_context_rules.csv` |

**Label thresholds:** High ≥ 75 · Moderate ≥ 55 · Low < 55.

**Maximum achievable:** $65 + 8 + 8 + 8 + 8 = 97$ → clipped to 95. "High" is reachable for a route that is in-window, TRL 9, near a benchmark, and without impurity/context penalties.

**Fix from v1.8.3 (BUG-CONF-1):** Baseline was 55. With maximum positive adjustments of +8 (in-window) + 8 (benchmark) = +16, ceiling was 71 — structurally below the 75 threshold for "High". Raising baseline to 65 and adding the TRL ≥ 8 bonus resolves this.

---

## 12. Balanced score

The overall ranking criterion — routes are not sorted by LCOC alone:

$$S = 0.32 \cdot S_{\text{cost}} + 0.15 \cdot S_{\text{energy}} + 0.24 \cdot S_{\text{fit}} + 0.12 \cdot S_{\text{TRL}} + 0.17 \cdot S_{\text{confidence}}$$

Sub-score transformations (all map to [0, 100]):

$$S_{\text{cost}} = \frac{100}{1 + \text{LCOC}/80}$$

$$S_{\text{energy}} = \frac{100}{1 + E_{\text{specific}}/3}$$

$$S_{\text{TRL}} = \frac{\text{TRL}}{9} \times 100$$

$$S_{\text{fit}} = \max\!\left(0,\; \min\!\left(100,\; 35 s_r + 25(1 - d_{\text{bench}}) + 20 \frac{\text{TRL}}{9} + 20 \cdot \mathbf{1}_{\text{no-purity-shortfall}}\right)\right)$$

**Weight rationale:**
- 32% cost — largest driver for commercial decisions, but not sole criterion
- 15% energy — captures electricity/heat price sensitivity
- 24% technical fit — regime compatibility, benchmark proximity, maturity, spec achievability
- 12% TRL maturity — prevents emerging-technology routes from winning purely on optimistic cost
- 17% confidence — penalises routes with poor benchmark support or poor data quality

---

*All equations implemented verbatim in `carbon_capture_app_v1_8_8.py`. All parameters read from `carbon_capture_master_data_pack_v5/engineering_backbone/`. All references listed in `references_master.csv`.*
