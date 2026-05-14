

def _legend_labels_with_pct(names, values):
    total = sum(values) if values else 0
    out = []
    for n, v in zip(names, values):
        pct = (100.0 * v / total) if total else 0.0
        out.append(f"{n}: {pct:.0f}%")
    return out

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import os
import json
from datetime import datetime

# ── Twin model imports (v2.1) ─────────────────────────────────────────────
try:
    from twin_router import enrich_result_with_twin, enrich_all_results
    TWIN_AVAILABLE = True
except ImportError:
    TWIN_AVAILABLE = False

NM3_TO_KMOL = 1.0 / 22.414
DEFAULT_DATA_DIRNAME = "carbon_capture_master_data_pack_v5"
FAMILY_COLORS = {
    "absorption": "#1f77b4",
    "adsorption": "#2ca02c",
    "membrane": "#ff7f0e",
    "cryogenic": "#9467bd",
}


def apply_styles():
    st.markdown(
        """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {background:#f6f8fb;color:#111827;}
        .block-container {padding-top:4.2rem;padding-bottom:2rem;max-width:1380px;}
        header[data-testid="stHeader"] {
            background: linear-gradient(180deg, rgba(248,250,252,0.96) 0%, rgba(248,250,252,0.86) 100%) !important;
            border-bottom: 1px solid rgba(148,163,184,0.16) !important;
            box-shadow: 0 4px 14px rgba(15,23,42,0.05);
        }
        div[data-testid="stToolbar"] {top:0.55rem !important;}
        section[data-testid="stSidebar"] > div {padding-top:4.9rem !important;}
        button[kind="header"] {top:5.0rem !important;}
        h1,h2,h3,h4,h5,h6,p,label,span,div,li {color:#111827;}
        [data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] *, [data-testid="stMetricDelta"] * {color:#111827 !important;}
        [data-testid="stSidebar"] {background:#ffffff;border-right:1px solid #e5e7eb;}
        [data-testid="stSidebar"] * {color:#111827 !important;}
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {background:#ffffff !important;color:#111827 !important;border-color:#cbd5e1 !important;}
        [data-testid="stSidebar"] button {background:#ffffff !important;color:#111827 !important;border:1px solid #d1d5db !important;}
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {background:#2563eb !important;color:#ffffff !important;border:1px solid #2563eb !important;}
        div[data-baseweb="popover"], div[data-baseweb="popover"] * {color:#111827 !important;}
        div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, div[role="listbox"], div[role="option"] {background:#ffffff !important;color:#111827 !important;}
        div[role="option"]:hover {background:#eff6ff !important;}
        [data-baseweb="tab-list"] {gap:0.8rem;padding-bottom:0.25rem;border-bottom:1px solid #e5e7eb;margin-bottom:0.8rem;}
        [data-baseweb="tab"] {color:#475569 !important;font-weight:600;font-size:0.96rem;padding:0.5rem 0.1rem 0.6rem 0.1rem;}
        [data-baseweb="tab"][aria-selected="true"] {color:#dc2626 !important;border-bottom:2px solid #dc2626 !important;}
        div[data-testid="stExpander"] {background:#ffffff !important;border:1px solid #e5e7eb !important;border-radius:14px !important;overflow:hidden;margin-bottom:0.75rem;}
        div[data-testid="stExpander"] details, div[data-testid="stExpander"] summary, div[data-testid="stExpander"] summary * {background:#ffffff !important;color:#111827 !important;}
        .cc-card {background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:0.95rem 1rem;margin-bottom:0.8rem;box-shadow:0 1px 2px rgba(15,23,42,0.03);}
        .cc-card-tight {background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:0.75rem 0.9rem;margin-bottom:0.8rem;box-shadow:0 1px 2px rgba(15,23,42,0.03);}
        .cc-banner {background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;border-radius:14px;padding:0.85rem 1rem;margin:0.2rem 0 0.9rem 0;font-weight:600;}
        .cc-warning {background:#fffbeb;color:#92400e;border:1px solid #fde68a;border-radius:14px;padding:0.8rem 1rem;margin:0.3rem 0 0.9rem 0;}
        .cc-muted {color:#4b5563;font-size:0.94rem;}
        .cc-section-title {font-size:1rem;font-weight:700;margin-bottom:0.55rem;color:#111827;}
        .cc-table table {width:100%;border-collapse:collapse;background:white;font-size:0.92rem;}
        .cc-table th {text-align:left;background:#f8fafc;padding:0.55rem;border-bottom:1px solid #d1d5db;color:#111827 !important;}
        .cc-table td {padding:0.48rem 0.55rem;border-bottom:1px solid #e5e7eb;vertical-align:top;color:#111827 !important;background:#ffffff;}
        .cc-small {font-size:0.9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )



def html_table(df: pd.DataFrame, index: bool = False, max_rows: int = 50) -> str:
    sub = df.head(max_rows).copy()
    html = sub.to_html(index=index, classes="cc-table cc-small", escape=False)
    return f'<div class="cc-table">{html}</div>'


def label_source_name(db: DataPack, source_id: str) -> str:
    rows = db.feed_sources.loc[db.feed_sources["source_id"] == source_id]
    if rows.empty:
        return source_id
    return str(rows.iloc[0]["source_name"]).replace("_", " ")


def render_string_list_table(items, col_name):
    if not items:
        st.write("No major triggered items for this section.")
        return
    df = pd.DataFrame({col_name: list(items)})
    st.markdown(html_table(df, index=False), unsafe_allow_html=True)


def generic_assumptions(best: Dict[str, Any], family: str) -> list[str]:
    notes = [
        "Screening-level route comparison only. Do not use as final project TEA or equipment sizing.",
        "Results depend on current Database V4 route templates, benchmark anchors, and simplified scaling rules.",
        "Scope aims to include triggered pretreatment and post-treatment burdens, but still remains simplified versus full FEED/Aspen work.",
    ]
    if family == "membrane":
        notes.append("Membrane routes may require polishing or downstream treatment if purity/recovery targets are not naturally met.")
    elif family == "adsorption":
        notes.append("Adsorption performance is sensitive to moisture, swing selection, and usable working capacity assumptions.")
    elif family == "cryogenic":
        notes.append("Cryogenic routes are treated as niche high-CO2/high-pressure options and remain especially sensitive to feed dryness and scope assumptions.")
    else:
        notes.append("Absorption routes remain sensitive to utility assumptions, reclaiming burden, and solvent/process-context fit.")
    if best.get("benchmark_distance", 1.0) > 0.6:
        notes.append("Benchmark distance is relatively large, so confidence should be treated cautiously.")
    return notes


def benchmark_rows(db: DataPack, ids: List[str]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame()
    rows = db.benchmark_cases[db.benchmark_cases["benchmark_id"].isin(ids)].copy()
    cols = [c for c in ["benchmark_id","expected_family","expected_subtechnology","co2_mol_pct","pressure_bar","capture_target_pct","confidence","notes"] if c in rows.columns]
    return rows[cols] if not rows.empty else pd.DataFrame()


def literature_rows(db: DataPack, family: str) -> pd.DataFrame:
    if db.tea_studies.empty or "technology_family" not in db.tea_studies.columns:
        return pd.DataFrame()
    rows = db.tea_studies[db.tea_studies["technology_family"].astype(str).str.lower() == family].copy()
    if rows.empty:
        return pd.DataFrame()
    cols = [c for c in ["study_id","primary_region","sub_technology","year","peer_reviewed","credibility_tier","title"] if c in rows.columns]
    return rows[cols].head(8)


@dataclass
class FeedCase:
    source_id: str
    source_name: str
    flow_nm3_h: float
    pressure_bar: float
    temperature_c: float
    co2_mol_pct: float
    h2_mol_pct: float
    n2_mol_pct: float
    ch4_mol_pct: float
    co_mol_pct: float
    h2o_mol_pct: float
    capture_target_pct: float
    product_purity_pct: float
    impurities: Dict[str, float]
    process_context: Dict[str, Any]

    @property
    def flow_kmol_h(self) -> float:
        return self.flow_nm3_h * NM3_TO_KMOL

    @property
    def co2_kmol_h(self) -> float:
        return self.flow_kmol_h * self.co2_mol_pct / 100.0

    @property
    def captured_co2_kmol_h(self) -> float:
        return self.co2_kmol_h * self.capture_target_pct / 100.0

    @property
    def captured_co2_t_h(self) -> float:
        return self.captured_co2_kmol_h * 44.01 / 1000.0


@dataclass
class Economics:
    carbon_price_eur_t: float
    electricity_eur_mwh: float
    heat_eur_gj: float
    cooling_eur_m3: float
    labor_eur_y: float
    discount_rate_pct: float
    life_years: float
    maintenance_pct_capex: float
    contingency_pct: float
    op_hours: float


class DataPack:
    def __init__(self, root: Path):
        eb = root / "engineering_backbone"
        tl = root / "tea_literature"
        self.root = root
        self.feed_sources = pd.read_csv(eb / "feed_sources.csv")
        self.rep_cases = pd.read_csv(eb / "feed_source_representative_cases.csv")
        self.process_context_rules = pd.read_csv(eb / "process_context_rules.csv")
        self.impurity_effects = pd.read_csv(eb / "impurity_effects.csv")
        self.pretreatment_rules = pd.read_csv(eb / "pretreatment_rules.csv")
        self.post_treatment_rules = pd.read_csv(eb / "post_treatment_rules.csv")
        self.solvents = pd.read_csv(eb / "absorption_solvents.csv")
        self.adsorbents = pd.read_csv(eb / "adsorbents.csv")
        self.swing_modes = pd.read_csv(eb / "swing_modes.csv")
        self.adsorbent_swing = pd.read_csv(eb / "adsorbent_swing_compatibility.csv")
        self.membranes = pd.read_csv(eb / "membranes.csv")
        self.cryogenic = pd.read_csv(eb / "cryogenic_configs.csv")
        self.route_templates = pd.read_csv(eb / "route_templates.csv")
        self.route_equipment = pd.read_csv(eb / "route_equipment_map.csv")
        self.equipment_classes = pd.read_csv(eb / "equipment_classes.csv")
        self.equipment_cost_anchors = pd.read_csv(eb / "equipment_cost_anchors.csv")
        self.equipment_scaling_rules = pd.read_csv(eb / "equipment_scaling_rules.csv")
        self.utility_mapping = pd.read_csv(eb / "utility_mapping.csv")
        self.replacement_consumables = pd.read_csv(eb / "replacement_consumables.csv")
        self.scope_boundaries = pd.read_csv(eb / "scope_boundary_definitions.csv")
        self.tea_norm = pd.read_csv(eb / "tea_normalization_rules.csv")
        self.study_scope_mapping = pd.read_csv(eb / "study_scope_mapping.csv")
        self.product_specs = pd.read_csv(eb / "product_spec_targets.csv")
        self.downstream_rules = pd.read_csv(eb / "downstream_handling_rules.csv")
        self.benchmark_cases = pd.read_csv(eb / "benchmark_cases.csv")
        self.benchmark_case_tags = pd.read_csv(eb / "benchmark_case_tags.csv")
        self.validation_sets = pd.read_csv(eb / "validation_sets.csv")
        self.confidence_rules = pd.read_csv(eb / "confidence_rules.csv")
        self.tea_cost_anchors = pd.read_csv(eb / "tea_cost_anchors.csv")
        self.tea_studies = pd.read_csv(tl / "tea_study_metadata.csv") if (tl / "tea_study_metadata.csv").exists() else pd.DataFrame()
        self.tea_metrics = pd.read_csv(tl / "tea_extracted_metrics_long.csv") if (tl / "tea_extracted_metrics_long.csv").exists() else pd.DataFrame()


def locate_data_root() -> Path:
    env = os.getenv("CC_DATA_PACK")
    candidates = []
    if env:
        candidates.append(Path(env))
    app_dir = Path(__file__).resolve().parent
    candidates.extend([
        app_dir / DEFAULT_DATA_DIRNAME,
        Path.cwd() / DEFAULT_DATA_DIRNAME,
        Path("/mnt/data") / DEFAULT_DATA_DIRNAME,
    ])
    for p in candidates:
        if p.exists() and (p / "engineering_backbone").exists():
            return p
    raise FileNotFoundError(
        f"Could not locate {DEFAULT_DATA_DIRNAME}. Put it next to the app file or set CC_DATA_PACK."
    )


@st.cache_data(show_spinner=False)
def load_data() -> DataPack:
    return DataPack(locate_data_root())



def payback_label(years: float | None) -> str:
    if years is None:
        return "No positive payback"
    if years >= 100:
        return ">100 y"
    return f"{years:.1f} y"

def money(x: float) -> str:
    if abs(x) >= 1e6:
        return f"€{x/1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"€{x/1e3:,.1f}k"
    return f"€{x:,.0f}"


def crf(rate_pct: float, years: float) -> float:
    r = rate_pct / 100.0
    if r == 0:
        return 1.0 / years
    return r * (1 + r) ** years / ((1 + r) ** years - 1)


def get_source_defaults(db: DataPack, source_id: str) -> Dict[str, Any]:
    row = db.rep_cases[db.rep_cases["source_id"] == source_id].iloc[0]
    source = db.feed_sources[db.feed_sources["source_id"] == source_id].iloc[0]
    return {
        "source_name": source["source_name"],
        "flow_nm3_h": float(row["flow_nm3_h"]),
        "pressure_bar": float(row["pressure_bar"]),
        "temperature_c": float(row["temperature_c"]),
        "co2_mol_pct": float(row["co2_mol_pct"]),
        "h2_mol_pct": float(row["h2_mol_pct"]),
        "n2_mol_pct": float(row["n2_mol_pct"]),
        "ch4_mol_pct": float(row["ch4_mol_pct"]),
        "co_mol_pct": float(row["co_mol_pct"]),
        "h2o_mol_pct": float(row["h2o_mol_pct"]),
        "likely_impurities": str(source["likely_impurities"]) if pd.notna(source["likely_impurities"]) else "",
    }


def build_feed_case(db: DataPack) -> Tuple[FeedCase, Economics, bool]:
    with st.sidebar:
        st.header("Inputs")
        mode = st.radio("Input mode", ["Source archetype", "Custom"], horizontal=True)
        source_names = dict(zip(db.feed_sources["source_name"], db.feed_sources["source_id"]))
        if mode == "Source archetype":
            source_name = st.selectbox("Source", list(source_names.keys()), index=list(source_names.keys()).index("cement_flue_gas") if "cement_flue_gas" in source_names else 0)
            source_id = source_names[source_name]
            d = get_source_defaults(db, source_id)
        else:
            source_id = "SRC_CUSTOM"
            d = {
                "source_name": "custom_case",
                "flow_nm3_h": 10000.0,
                "pressure_bar": 5.0,
                "temperature_c": 40.0,
                "co2_mol_pct": 20.0,
                "h2_mol_pct": 0.0,
                "n2_mol_pct": 70.0,
                "ch4_mol_pct": 5.0,
                "co_mol_pct": 0.0,
                "h2o_mol_pct": 5.0,
                "likely_impurities": "",
            }
        st.subheader("Feed")
        flow_nm3_h = st.number_input("Gas flow (Nm³/h)", min_value=100.0, value=float(d["flow_nm3_h"]), step=100.0)
        pressure_bar = st.number_input("Pressure (bar abs)", min_value=0.5, value=float(d["pressure_bar"]), step=0.1)
        temperature_c = st.number_input("Temperature (°C)", value=float(d["temperature_c"]), step=1.0)
        st.subheader("Major composition (mol%)")
        co2 = st.number_input("CO2", min_value=0.0, max_value=100.0, value=float(d["co2_mol_pct"]))
        h2 = st.number_input("H2", min_value=0.0, max_value=100.0, value=float(d["h2_mol_pct"]))
        n2 = st.number_input("N2", min_value=0.0, max_value=100.0, value=float(d["n2_mol_pct"]))
        ch4 = st.number_input("CH4", min_value=0.0, max_value=100.0, value=float(d["ch4_mol_pct"]))
        co = st.number_input("CO", min_value=0.0, max_value=100.0, value=float(d["co_mol_pct"]))
        h2o = st.number_input("H2O", min_value=0.0, max_value=100.0, value=float(d["h2o_mol_pct"]))
        total = co2 + h2 + n2 + ch4 + co + h2o
        if abs(total - 100.0) > 0.5:
            st.warning(f"Composition sum = {total:.1f} mol%. Adjust to 100.")
        st.subheader("Targets")
        capture_target = st.slider("CO2 capture target (%)", 50, 99, 90)
        purity_target = st.slider("CO2 product purity target (%)", 70, 99, 95)
        destination = st.selectbox("CO2 destination", ["storage", "utilization_standard", "high_purity"], index=0)
        with st.expander("Advanced feed quality / impurities"):
            impurities = {
                "O2": st.number_input("O2 (mol% if known)", min_value=0.0, value=0.0),
                "H2S": st.number_input("H2S (mol% if known)", min_value=0.0, value=0.0),
                "SOx": st.number_input("SOx / SO2 (ppm or mg/Nm3 proxy)", min_value=0.0, value=0.0),
                "NOx": st.number_input("NOx (ppm or mg/Nm3 proxy)", min_value=0.0, value=0.0),
                "HCl": st.number_input("HCl (ppm or mg/Nm3 proxy)", min_value=0.0, value=0.0),
                "NH3": st.number_input("NH3 (ppm or mg/Nm3 proxy)", min_value=0.0, value=0.0),
                "Particulates": st.number_input("Particulates (mg/Nm3)", min_value=0.0, value=0.0),
                "HeavyHC": st.number_input("Heavy hydrocarbons / condensables (proxy)", min_value=0.0, value=0.0),
            }
        with st.expander("Process context"):
            process_context = {
                "steam_available": st.selectbox("Steam available?", ["unknown", "yes", "no"], index=0),
                "waste_heat_available": st.selectbox("Waste heat available?", ["unknown", "yes", "no"], index=0),
                "cooling_limited": st.selectbox("Cooling limited?", ["unknown", "no", "yes"], index=0),
                "compression_available": st.selectbox("Compression already available?", ["unknown", "no", "yes"], index=0),
                "compact_footprint_preferred": st.selectbox("Compact footprint preferred?", ["unknown", "no", "yes"], index=0),
                "low_complexity_preferred": st.selectbox("Low complexity preferred?", ["unknown", "no", "yes"], index=0),
                "co2_destination": destination,
            }
        st.subheader("Economics")
        carbon_price = st.number_input("Carbon price (€/tCO₂)", value=85.0)
        electricity = st.number_input("Electricity (€/MWh)", value=85.0)
        heat = st.number_input("Heat / steam (€/GJ)", value=15.0)
        cooling = st.number_input("Cooling water (€/m³)", value=0.05)
        labor = st.number_input("Labor (€/y)", value=180000.0)
        discount = st.number_input("Discount rate (%)", value=8.0)
        life = st.number_input("Project life (y)", value=25.0)
        maint = st.number_input("Maintenance (% of CAPEX/y)", value=3.0)
        contingency = st.number_input("Contingency (% of CAPEX)", value=15.0)
        op_hours = st.number_input("Operating hours per year", value=8000.0)
        run = st.button("Run screening", type="primary", disabled=abs(total - 100.0) > 0.5)

    feed = FeedCase(
        source_id=source_id,
        source_name=d["source_name"],
        flow_nm3_h=float(flow_nm3_h),
        pressure_bar=float(pressure_bar),
        temperature_c=float(temperature_c),
        co2_mol_pct=float(co2),
        h2_mol_pct=float(h2),
        n2_mol_pct=float(n2),
        ch4_mol_pct=float(ch4),
        co_mol_pct=float(co),
        h2o_mol_pct=float(h2o),
        capture_target_pct=float(capture_target),
        product_purity_pct=float(purity_target),
        impurities=impurities,
        process_context=process_context,
    )
    econ = Economics(
        carbon_price_eur_t=float(carbon_price),
        electricity_eur_mwh=float(electricity),
        heat_eur_gj=float(heat),
        cooling_eur_m3=float(cooling),
        labor_eur_y=float(labor),
        discount_rate_pct=float(discount),
        life_years=float(life),
        maintenance_pct_capex=float(maint),
        contingency_pct=float(contingency),
        op_hours=float(op_hours),
    )
    return feed, econ, run


def regime_score(route_regime: str, feed: FeedCase) -> float:
    pressure = feed.pressure_bar
    co2 = feed.co2_mol_pct
    if route_regime == "low_pressure_flue_gas":
        score = 1.0 if pressure <= 2 and co2 <= 30 else 0.6
    elif route_regime == "high_pressure_precombustion_or_sweetening":
        score = 1.0 if pressure >= 8 and co2 >= 15 else 0.45
    elif route_regime == "moderate_pressure_dry_gas":
        score = 1.0 if pressure >= 3 and feed.h2o_mol_pct <= 3 and 8 <= co2 <= 50 else 0.55
    elif route_regime == "pressure_assisted_modular":
        score = 1.0 if pressure >= 4 and co2 >= 10 else 0.5
    elif route_regime == "niche_high_co2_high_pressure":
        score = 1.0 if pressure >= 8 and co2 >= 25 else 0.2
    elif route_regime == "clr_shifted_high_pressure":
        score = 1.0 if pressure >= 10 and feed.h2_mol_pct >= 15 else 0.35
    else:
        score = 0.7
    return score


def candidate_routes(db: DataPack, feed: FeedCase) -> List[Dict[str, Any]]:
    cands: List[Dict[str, Any]] = []
    for _, rt in db.route_templates.iterrows():
        rid = rt["route_id"]
        fam = rt["family"]
        base = {
            "route_id": rid,
            "family": fam,
            "subtechnology_group": rt["subtechnology"],
            "route_description": rt["description"],
            "route_regime_score": regime_score(rt["application_regime"], feed),
        }
        if rid == "ROUTE_ABS_MEA":
            for _, s in db.solvents[db.solvents["solvent_family"] == "chemical"].iterrows():
                d = dict(base)
                d["option_name"] = s["solvent"]
                d["route_mode"] = "absorption"
                cands.append(d)
        elif rid in ["ROUTE_ABS_PHYS", "ROUTE_CLR_PHYS"]:
            for _, s in db.solvents[db.solvents["solvent_family"] == "physical"].iterrows():
                d = dict(base)
                d["option_name"] = s["solvent"]
                d["route_mode"] = "absorption"
                cands.append(d)
        elif rid == "ROUTE_ADS_PSA":
            compat = db.adsorbent_swing[db.adsorbent_swing["swing_mode"] == "PSA"]
            ads_ok = db.adsorbents.merge(compat, on="adsorbent")
            for _, a in ads_ok.iterrows():
                d = dict(base)
                d["option_name"] = f"{a['adsorbent']} + PSA"
                d["adsorbent"] = a["adsorbent"]
                d["swing_mode"] = "PSA"
                d["route_mode"] = "adsorption"
                cands.append(d)
        elif rid == "ROUTE_ADS_TSA":
            compat = db.adsorbent_swing[db.adsorbent_swing["swing_mode"] == "TSA"]
            ads_ok = db.adsorbents.merge(compat, on="adsorbent")
            for _, a in ads_ok.iterrows():
                d = dict(base)
                d["option_name"] = f"{a['adsorbent']} + TSA"
                d["adsorbent"] = a["adsorbent"]
                d["swing_mode"] = "TSA"
                d["route_mode"] = "adsorption"
                cands.append(d)
        elif rid in ["ROUTE_MEM_1STAGE", "ROUTE_MEM_2STAGE"]:
            stages = 1 if "1STAGE" in rid else 2
            for _, m in db.membranes.iterrows():
                d = dict(base)
                d["option_name"] = f"{m['membrane']} ({stages}-stage)"
                d["membrane"] = m["membrane"]
                d["stages"] = stages
                d["route_mode"] = "membrane"
                cands.append(d)
        elif rid == "ROUTE_CRYO_NICHE":
            for _, c in db.cryogenic.iterrows():
                d = dict(base)
                d["option_name"] = c["config_id"]
                d["config_id"] = c["config_id"]
                d["route_mode"] = "cryogenic"
                cands.append(d)
    return cands


def evaluate_impurities(db: DataPack, feed: FeedCase, family: str) -> Tuple[float, float, List[str], List[str], bool, int]:
    cap_mult = 1.0
    op_mult = 1.0
    pretreat = []
    warnings = []
    reject = False
    conf_delta = 0
    fam_map = {"absorption": "absorption", "adsorption": "adsorption", "membrane": "membrane", "cryogenic": "cryogenic"}
    fam_key = fam_map[family]
    for imp, val in {"H2O": feed.h2o_mol_pct, **feed.impurities, "CO": feed.co_mol_pct}.items():
        rows = db.impurity_effects[(db.impurity_effects["family"] == fam_key) & (db.impurity_effects["impurity"] == imp)]
        if rows.empty:
            continue
        row = rows.iloc[0]
        if float(val) >= float(row["warning_threshold"]):
            warnings.append(f"{imp}: {row['mechanism']}")
            pretreat.append(str(row["pretreatment_needed"]))
            cap_mult *= float(row["capex_multiplier"])
            op_mult *= float(row["opex_multiplier"])
            conf_delta += int(row["confidence_delta"])
        if float(val) >= float(row["reject_threshold"]):
            reject = True
    return cap_mult, op_mult, sorted(set(pretreat)), warnings, reject, conf_delta


def evaluate_pretreatment(db: DataPack, feed: FeedCase, family: str) -> Tuple[float, float, List[str]]:
    cap = 1.0
    op = 1.0
    items = []
    fam_alias = "all" if family == "all" else family
    for _, r in db.pretreatment_rules.iterrows():
        fams = str(r["affected_families"]).split(";")
        if "all" not in fams and family not in fams:
            continue
        var = r["trigger_variable"]
        val = None
        if var == "temperature_c":
            val = feed.temperature_c
        elif var == "H2O_mol_pct":
            val = feed.h2o_mol_pct
        elif var == "Particulates_mg_Nm3":
            val = feed.impurities.get("Particulates", 0.0)
        elif var == "SOx_or_HCl_present":
            val = max(feed.impurities.get("SOx", 0.0), feed.impurities.get("HCl", 0.0))
        elif var == "heavy_hc_proxy":
            val = feed.impurities.get("HeavyHC", 0.0)
        if val is None:
            continue
        comp = r["comparator"]
        trig = r["trigger_value"]
        fire = False
        if comp == ">" and val > float(trig):
            fire = True
        elif comp == "==" and str(val) == str(trig):
            fire = True
        if fire:
            items.append(str(r["pretreatment"]))
            cap *= float(r["capex_multiplier"])
            op *= float(r["opex_multiplier"])
    return cap, op, sorted(set(items))


def apply_process_context(db: DataPack, feed: FeedCase, family: str) -> Tuple[float, float, int, List[str]]:
    cap = 1.0
    op = 1.0
    conf = 0
    notes = []
    for _, r in db.process_context_rules.iterrows():
        fams = str(r["affected_families"]).split(";")
        if "all" not in fams and family not in fams:
            continue
        key = r["context_variable"]
        user_val = str(feed.process_context.get(key, "unknown"))
        if user_val == str(r["trigger_value"]):
            cap *= float(r["capex_multiplier"])
            op *= float(r["opex_multiplier"])
            conf += int(r["confidence_delta"])
            notes.append(str(r["effect_logic"]))
        elif user_val == "unknown":
            conf -= 2
    return cap, op, conf, notes


def downstream_multiplier(db: DataPack, feed: FeedCase, family: str, purity_shortfall: bool) -> Tuple[float, float, List[str]]:
    cap = 1.0
    op = 1.0
    items = []
    dest = feed.process_context.get("co2_destination", "storage")
    for _, r in db.downstream_rules.iterrows():
        if r["co2_destination"] not in [dest, "any"]:
            continue
        fams = str(r["affected_families"]).split(";")
        if "all" not in fams and family not in fams:
            continue
        if r["downstream_unit"] == "polishing_for_purity" and not purity_shortfall:
            continue
        cap *= float(r["capex_multiplier"])
        op *= float(r["opex_multiplier"])
        items.append(str(r["downstream_unit"]))
    return cap, op, items


def cost_equipment_item(eq_id: str, feed: FeedCase, duty_factor: float, pressure_factor: float, area_factor: float) -> float:
    flow_factor = max(feed.flow_nm3_h / 10000.0, 0.1)
    if eq_id == "EQ_ABSORBER":
        return 800000 * (flow_factor ** 0.65) * pressure_factor
    if eq_id == "EQ_STRIPPER":
        return 700000 * (flow_factor ** 0.65)
    if eq_id == "EQ_REBOILER":
        return 550000 * (max(duty_factor, 0.2) ** 0.7)
    if eq_id == "EQ_HEX":
        return 280000 * (max(duty_factor, 0.2) ** 0.65)
    if eq_id == "EQ_PUMP":
        return 100000 * (flow_factor ** 0.55)
    if eq_id == "EQ_SOLVENT_RECLAIMER":
        return 250000 * (flow_factor ** 0.5)
    if eq_id == "EQ_ADS_VESSEL":
        return 930000 * (max(area_factor, 0.3) ** 0.65)
    if eq_id == "EQ_SWITCHING_VALVES":
        return 350000 * (flow_factor ** 0.5)
    if eq_id == "EQ_HEATER":
        return 200000 * (max(duty_factor, 0.2) ** 0.6)
    if eq_id == "EQ_BLOWER":
        return 260000 * (flow_factor ** 0.6)
    if eq_id == "EQ_VACUUM":
        return 990000 * (flow_factor ** 0.6) * pressure_factor
    if eq_id == "EQ_MEM_MODULES":
        return 150000 * max(area_factor, 0.3)
    if eq_id == "EQ_COMPRESSOR":
        return 420000 * (max(duty_factor, 0.2) ** 0.65) * pressure_factor
    if eq_id == "EQ_RECYCLE_LOOP":
        return 220000 * (flow_factor ** 0.55)
    if eq_id == "EQ_POLISHING":
        return 250000 * (flow_factor ** 0.55)
    if eq_id == "EQ_DRYER":
        return 220000 * (flow_factor ** 0.55)
    if eq_id == "EQ_FILTER":
        return 70000 * (flow_factor ** 0.45)
    if eq_id == "EQ_PRE_COOLER":
        return 140000 * (flow_factor ** 0.55)
    if eq_id == "EQ_COLD_BOX":
        return 1300000 * (flow_factor ** 0.6) * pressure_factor
    if eq_id == "EQ_REFRIGERATION":
        return 900000 * (max(duty_factor, 0.3) ** 0.7)
    if eq_id == "EQ_SEPARATOR":
        return 180000 * (flow_factor ** 0.55)
    if eq_id == "EQ_DEHY":
        return 180000 * (flow_factor ** 0.5)
    if eq_id == "EQ_EXPORT_COMP":
        return 500000 * (max(duty_factor, 0.3) ** 0.65)
    return 100000 * (flow_factor ** 0.5)


def build_equipment_train_cost(db: DataPack, route_id: str, feed: FeedCase, perf: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    rows = db.route_equipment[db.route_equipment["route_id"] == route_id].sort_values("sequence_no")
    costs: Dict[str, float] = {}
    for _, r in rows.iterrows():
        include = True
        trig = str(r["trigger_logic"])
        if trig == "hot_or_wet_flue_gas":
            include = feed.temperature_c > 40 or feed.h2o_mol_pct > 3
        elif trig == "particulates_or_mist_present":
            include = feed.impurities.get("Particulates", 0.0) > 0
        elif trig == "when_high_water_or_water_sensitive":
            include = feed.h2o_mol_pct > 1
        elif trig == "only_when_reclaiming_needed":
            include = perf.get("reclaiming_needed", False)
        elif trig == "only_for_tsa_variants":
            include = perf.get("swing_mode") == "TSA"
        elif trig == "only_for_vacuum_routes":
            include = perf.get("vacuum_needed", False)
        elif trig == "only_when_2nd_stage_or_recycle":
            include = perf.get("stages", 1) >= 2
        elif trig == "when_polishing_needed":
            include = perf.get("purity_shortfall", False)
        elif trig == "always_if_cryogenic_selected":
            include = True
        elif trig == "always_for_export_scope":
            include = feed.process_context.get("co2_destination", "storage") == "storage"
        elif trig == "only_for_clr_shifted_high_pressure":
            include = feed.source_id == "SRC_CLR" or (feed.pressure_bar >= 10 and feed.h2_mol_pct >= 15)
        if not include:
            continue
        eq_id = r["equipment_class_id"]
        cost = cost_equipment_item(
            eq_id,
            feed,
            duty_factor=perf.get("duty_factor", 1.0),
            pressure_factor=perf.get("pressure_factor", 1.0),
            area_factor=perf.get("area_factor", 1.0),
        )
        costs[eq_id] = cost
    return sum(costs.values()), costs


def classify_significance(sig: str) -> float:
    sig = str(sig)
    if "high" in sig:
        return 1.0
    if "medium" in sig:
        return 0.55
    return 0.25


def route_utility_intensity(db: DataPack, route_id: str, base_tpy: float) -> Tuple[float, float, float]:
    rows = db.utility_mapping[db.utility_mapping["route_id"] == route_id]
    steam_gj_y = 0.0
    elec_mwh_y = 0.0
    cooling_m3_y = 0.0
    for _, r in rows.iterrows():
        s = classify_significance(r["significance_class"])
        if r["utility_type"] == "steam":
            steam_gj_y += base_tpy * (2.2 * s)
        elif r["utility_type"] == "electricity":
            elec_mwh_y += base_tpy * (0.18 * s)
        elif r["utility_type"] == "cooling_water":
            cooling_m3_y += base_tpy * (0.6 * s)
        elif r["utility_type"] == "refrigeration_power":
            elec_mwh_y += base_tpy * (0.28 * s)
    return steam_gj_y, elec_mwh_y, cooling_m3_y


def replacement_cost_factor(db: DataPack, family: str, subtech: str, base_capex: float) -> float:
    rows = db.replacement_consumables[db.replacement_consumables["family"] == family]
    if rows.empty:
        return 0.0
    factor = 0.0
    for _, r in rows.iterrows():
        sig = classify_significance(r["significance_class"])
        factor += 0.005 + 0.01 * sig
    return factor * base_capex


def benchmark_distance(db: DataPack, feed: FeedCase, family: str) -> Tuple[float, List[str]]:
    fam_map = {"absorption": ["absorption"], "adsorption": ["adsorption"], "membrane": ["membrane"], "cryogenic": ["cryogenic"]}
    fam_bms = db.benchmark_cases[db.benchmark_cases["expected_family"].str.lower().str.contains(family[:4], na=False)]
    if fam_bms.empty:
        return 1.0, []
    dists = []
    for _, b in fam_bms.iterrows():
        dist = 0.0
        dist += abs(b["co2_mol_pct"] - feed.co2_mol_pct) / 100.0
        dist += abs(b["pressure_bar"] - feed.pressure_bar) / max(feed.pressure_bar, 1.0)
        dist += abs(b["capture_target_pct"] - feed.capture_target_pct) / 100.0
        dists.append((dist, b["benchmark_id"]))
    dists.sort(key=lambda x: x[0])
    return dists[0][0], [x[1] for x in dists[:3]]


def confidence_score(db: DataPack, metrics: Dict[str, Any]) -> Tuple[float, str]:
    score = 65.0
    if metrics.get("in_window", False):
        score += 8
    else:
        score -= 6
    score += metrics.get("conf_delta", 0)
    if metrics.get("benchmark_distance", 1.0) < 0.2:
        score += 8
    elif metrics.get("benchmark_distance", 1.0) > 0.6:
        score -= 8
    trl = metrics.get("trl", 8)
    if trl >= 8:
        score += 8
    elif trl == 7:
        score += 4
    elif trl <= 6:
        score -= 6
    if metrics.get("purity_shortfall", False):
        score -= 5
    if metrics.get("route_regime_score", 0.0) < 0.5:
        score -= 8
    score = max(5, min(95, score))
    label = "High" if score >= 75 else "Moderate" if score >= 55 else "Low"
    return score, label


def evaluate_absorption(db: DataPack, feed: FeedCase, econ: Economics, cand: Dict[str, Any]) -> Dict[str, Any]:
    s = db.solvents[db.solvents["solvent"] == cand["option_name"]].iloc[0]
    low, high = float(s["regen_gj_t_min"]), float(s["regen_gj_t_max"])
    regen = 0.5 * (low + high)
    if s["solvent_family"] == "physical":
        if feed.pressure_bar < 8 or feed.co2_mol_pct < 15:
            regen *= 1.45
        else:
            regen *= 0.85
    else:
        if feed.pressure_bar < 2 and feed.co2_mol_pct < 15:
            regen *= 0.95
    captured_tpy = feed.captured_co2_t_h * econ.op_hours
    steam_gj_y = regen * captured_tpy
    elec_mwh_y = captured_tpy * (0.08 + 0.01 * max(feed.pressure_bar, 1.0))
    cooling_m3_y = captured_tpy * (0.7 if s["cooling_dependency"] == "high" else 0.35)
    purity_shortfall = False
    delta_loading = 0.5 * (float(s["delta_loading_min"]) + float(s["delta_loading_max"]))
    duty_factor = max(0.3, steam_gj_y / max(econ.op_hours * 5, 1))
    pressure_factor = max(0.8, feed.pressure_bar / 5.0) if s["solvent_family"] == "physical" else 1.0
    perf = {
        "regen_gj_t": regen,
        "steam_gj_y": steam_gj_y,
        "elec_mwh_y": elec_mwh_y,
        "cooling_m3_y": cooling_m3_y,
        "duty_factor": duty_factor,
        "pressure_factor": pressure_factor,
        "area_factor": max(feed.flow_nm3_h / 10000.0, 0.5),
        "reclaiming_needed": s["reclaiming_burden"] in ["medium", "high"],
        "purity_shortfall": purity_shortfall,
        "trl": int(s["trl"]),
    }
    return perf


def evaluate_adsorption(db: DataPack, feed: FeedCase, econ: Economics, cand: Dict[str, Any]) -> Dict[str, Any]:
    a = db.adsorbents[db.adsorbents["adsorbent"] == cand["adsorbent"]].iloc[0]
    cap = 0.5 * (float(a["effective_working_capacity_min_mol_per_kg"]) + float(a["effective_working_capacity_max_mol_per_kg"]))
    if a["moisture_sensitivity"] == "high" and feed.h2o_mol_pct > 3:
        cap *= 0.55
    elif a["moisture_sensitivity"] == "medium" and feed.h2o_mol_pct > 5:
        cap *= 0.75
    captured_mol_h = feed.captured_co2_kmol_h * 1000.0
    swing_mode = cand["swing_mode"]
    service_h = 1.3 if swing_mode == "PSA" else 2.4
    ads_mass = captured_mol_h * service_h / max(cap, 0.2)
    vacuum_needed = swing_mode in ["VSA", "PVSA"]
    heat_needed = swing_mode in ["TSA", "PTSA"]
    captured_tpy = feed.captured_co2_t_h * econ.op_hours

    if swing_mode == "PSA":
        spec_elec = 0.42
        if feed.pressure_bar < 2:
            spec_elec += 0.08
        if feed.h2o_mol_pct > 4:
            spec_elec += 0.04
        spec_elec = min(max(spec_elec, 0.35), 0.55)
        steam_gj_y = 0.0
    elif swing_mode == "TSA":
        spec_elec = 0.50
        if feed.pressure_bar < 2:
            spec_elec += 0.05
        if feed.h2o_mol_pct > 4:
            spec_elec += 0.05
        spec_elec = min(max(spec_elec, 0.45), 0.70)
        steam_gj_y = captured_tpy * 1.8
    elif vacuum_needed:
        spec_elec = 0.62
        if feed.pressure_bar < 2:
            spec_elec += 0.08
        spec_elec = min(max(spec_elec, 0.50), 0.85)
        steam_gj_y = 0.0
    else:
        spec_elec = 0.48
        steam_gj_y = captured_tpy * (1.2 if heat_needed else 0.0)

    elec_mwh_y = captured_tpy * spec_elec

    perf = {
        "usable_capacity": cap,
        "adsorbent_inventory_kg": ads_mass,
        "steam_gj_y": steam_gj_y,
        "elec_mwh_y": elec_mwh_y,
        "cooling_m3_y": captured_tpy * 0.2,
        "duty_factor": max(0.3, (steam_gj_y + elec_mwh_y * 3.6) / max(captured_tpy, 1)),
        "pressure_factor": min(2.5, max(1.0, 4.5 / max(feed.pressure_bar, 1.0))) if vacuum_needed else 1.15,
        "area_factor": max(ads_mass / 7000.0, 0.55),
        "vacuum_needed": vacuum_needed,
        "swing_mode": swing_mode,
        "purity_shortfall": feed.product_purity_pct > 96 and swing_mode == "PSA" and feed.co2_mol_pct < 15,
        "trl": int(a["trl"]),
    }
    return perf


def evaluate_membrane(db: DataPack, feed: FeedCase, econ: Economics, cand: Dict[str, Any]) -> Dict[str, Any]:
    m = db.membranes[db.membranes["membrane"] == cand["membrane"]].iloc[0]
    perm = 0.5 * (float(m["permeance_gpu_min"]) + float(m["permeance_gpu_max"]))
    sel = 0.5 * (float(m["selectivity_min"]) + float(m["selectivity_max"]))
    stage_cut = 0.5 * (float(m["max_stage_cut_min"]) + float(m["max_stage_cut_max"]))
    stages = int(cand["stages"])
    x = feed.co2_mol_pct / 100.0
    y_perm = (sel * x) / (1 + (sel - 1) * x)
    recovery = min(0.98, stage_cut * (1.1 if stages == 2 else 0.75) / max(x, 1e-3))
    purity = min(0.99, y_perm * (1.1 if stages == 2 else 1.0))
    purity_shortfall = purity * 100 < feed.product_purity_pct
    recovered_shortfall = recovery * 100 < feed.capture_target_pct
    pressure_ratio = max(1.1, 8.0 / max(feed.pressure_bar, 1.0))
    captured_tpy = feed.captured_co2_t_h * econ.op_hours
    area_factor = max((feed.captured_co2_kmol_h * 1000 / 3600) / max(perm * max(feed.pressure_bar, 1.0) * 0.02, 1e-6), 0.4)
    elec_mwh_y = captured_tpy * (0.25 + 0.12 * math.log(pressure_ratio) + (0.12 if stages == 2 else 0.0))
    if purity_shortfall:
        elec_mwh_y *= 1.1
    perf = {
        "purity_pct_est": purity * 100,
        "recovery_pct_est": recovery * 100,
        "steam_gj_y": 0.0,
        "elec_mwh_y": elec_mwh_y,
        "cooling_m3_y": captured_tpy * 0.12,
        "duty_factor": max(0.2, elec_mwh_y / max(captured_tpy, 1)),
        "pressure_factor": max(1.0, pressure_ratio / 2),
        "area_factor": area_factor,
        "stages": stages,
        "purity_shortfall": purity_shortfall or recovered_shortfall,
        "trl": int(m["trl"]),
    }
    return perf


def evaluate_cryogenic(db: DataPack, feed: FeedCase, econ: Economics, cand: Dict[str, Any]) -> Dict[str, Any]:
    c = db.cryogenic[db.cryogenic["config_id"] == cand["config_id"]].iloc[0]
    captured_tpy = feed.captured_co2_t_h * econ.op_hours
    purity_shortfall = feed.product_purity_pct > 99 and cand["config_id"] == "CRYO_BULK" if "CRYO_BULK" in db.cryogenic["config_id"].values else False
    dry_good = feed.h2o_mol_pct <= 1.0
    if feed.pressure_bar >= 12 and feed.co2_mol_pct >= 40 and dry_good:
        spec_elec = 0.38
    elif feed.pressure_bar >= 8 and feed.co2_mol_pct >= 25:
        spec_elec = 0.58
    else:
        spec_elec = 0.90
    if not dry_good:
        spec_elec += 0.12
    elec_mwh_y = captured_tpy * spec_elec
    perf = {
        "steam_gj_y": 0.0,
        "elec_mwh_y": elec_mwh_y,
        "cooling_m3_y": captured_tpy * 0.08,
        "duty_factor": max(0.3, elec_mwh_y / max(captured_tpy, 1)),
        "pressure_factor": min(2.5, max(0.8, 10.0 / max(feed.pressure_bar, 1.0))),
        "area_factor": max(feed.flow_nm3_h / 15000.0, 0.5),
        "purity_shortfall": purity_shortfall,
        "trl": int(c["trl"]),
    }
    return perf


def evaluate_route(db: DataPack, feed: FeedCase, econ: Economics, cand: Dict[str, Any]) -> Dict[str, Any] | None:
    family = cand["family"]
    route_regime_score = cand["route_regime_score"]
    if route_regime_score < 0.2:
        return None
    imp_cap, imp_op, imp_pretreat, imp_warn, imp_reject, imp_conf = evaluate_impurities(db, feed, family)
    if imp_reject and family in ["cryogenic", "membrane"]:
        return None
    pre_cap, pre_op, pretreat_items = evaluate_pretreatment(db, feed, family)
    ctx_cap, ctx_op, ctx_conf, ctx_notes = apply_process_context(db, feed, family)

    if family == "absorption":
        perf = evaluate_absorption(db, feed, econ, cand)
    elif family == "adsorption":
        perf = evaluate_adsorption(db, feed, econ, cand)
    elif family == "membrane":
        perf = evaluate_membrane(db, feed, econ, cand)
    else:
        perf = evaluate_cryogenic(db, feed, econ, cand)

    if family == "membrane" and feed.pressure_bar < 2.0:
        perf["elec_mwh_y"] *= 1.5
        route_regime_score *= 0.75
    if family == "adsorption" and feed.pressure_bar < 2.5 and feed.h2o_mol_pct > 3.0:
        route_regime_score *= 0.8
    if family == "cryogenic":
        if feed.pressure_bar < 6.0:
            return None
        if feed.co2_mol_pct < 20:
            route_regime_score *= 0.6
        elif feed.co2_mol_pct >= 40 and feed.pressure_bar >= 12 and feed.h2o_mol_pct <= 1.5:
            route_regime_score *= 1.1

    down_cap, down_op, downstream_items = downstream_multiplier(db, feed, family, perf.get("purity_shortfall", False))

    eq_capex, eq_items = build_equipment_train_cost(db, cand["route_id"], feed, perf)
    non_contingency_mult = imp_cap * pre_cap * ctx_cap * down_cap
    capex_pre_contingency = eq_capex * non_contingency_mult
    contingency_amount = capex_pre_contingency * (econ.contingency_pct / 100.0)
    integration_amount = max(capex_pre_contingency - eq_capex, 0.0)
    capex = capex_pre_contingency + contingency_amount

    steam_gj_y, elec_map_y, cooling_map_y = route_utility_intensity(db, cand["route_id"], feed.captured_co2_t_h * econ.op_hours)
    if family == "adsorption":
        steam_gj_y = perf.get("steam_gj_y", 0.0)
        elec_mwh_y = perf.get("elec_mwh_y", 0.0)
        cooling_m3_y = perf.get("cooling_m3_y", 0.0) + cooling_map_y
    elif family == "cryogenic":
        steam_gj_y = perf.get("steam_gj_y", 0.0)
        elec_mwh_y = perf.get("elec_mwh_y", 0.0)
        cooling_m3_y = perf.get("cooling_m3_y", 0.0) + cooling_map_y
    else:
        steam_gj_y += perf.get("steam_gj_y", 0.0)
        elec_mwh_y = perf.get("elec_mwh_y", 0.0) + elec_map_y
        cooling_m3_y = perf.get("cooling_m3_y", 0.0) + cooling_map_y

    opex_elec = elec_mwh_y * econ.electricity_eur_mwh
    opex_heat = steam_gj_y * econ.heat_eur_gj
    opex_cooling = cooling_m3_y * econ.cooling_eur_m3
    opex_repl = replacement_cost_factor(db, family, cand.get("subtechnology_group", "all"), capex)
    opex_maint = capex * econ.maintenance_pct_capex / 100.0
    opex = (opex_elec + opex_heat + opex_cooling + opex_repl + opex_maint + econ.labor_eur_y)
    opex *= imp_op * pre_op * ctx_op * down_op

    captured_tpy = max(feed.captured_co2_t_h * econ.op_hours, 1e-6)
    annualized_capex = capex * crf(econ.discount_rate_pct, econ.life_years)
    annual_cost = annualized_capex + opex
    lcoc = annual_cost / captured_tpy
    energy_gj_t = (elec_mwh_y * 3.6 + steam_gj_y) / captured_tpy

    annual_gross_value = captured_tpy * econ.carbon_price_eur_t
    annual_net_benefit = annual_gross_value - opex
    simple_payback_y = None
    if annual_net_benefit > 0:
        simple_payback_y = capex / annual_net_benefit

    bdist, nearest = benchmark_distance(db, feed, family)
    conf_delta = imp_conf + ctx_conf
    in_window = route_regime_score >= 0.75
    conf_score, conf_label = confidence_score(db, {
        "in_window": in_window,
        "conf_delta": conf_delta,
        "benchmark_distance": bdist,
        "trl": perf.get("trl", 8),
        "purity_shortfall": perf.get("purity_shortfall", False),
        "route_regime_score": route_regime_score,
    })

    technical_fit = max(0.0, min(100.0, 35 * route_regime_score + 25 * (1.0 - min(bdist, 1.0)) + 20 * (perf.get("trl", 8) / 9.0) + 20 * (0 if perf.get("purity_shortfall", False) else 1)))

    why = []
    if family == "absorption":
        why.append("Favored for dilute or low-pressure capture service." if cand["route_id"] == "ROUTE_ABS_MEA" else "Favored for elevated CO2 partial pressure and higher-pressure service.")
    elif family == "adsorption":
        why.append("Favored only when gas is sufficiently dry and the swing-duty burden remains justified for the pressure regime.")
    elif family == "membrane":
        why.append("Favored when pressure support exists and route train remains manageable.")
    else:
        why.append("Favored only in dry, high-CO2, higher-pressure niche conditions.")
    if imp_pretreat:
        why.append(f"Impurity/conditioning triggered: {', '.join(sorted(set(imp_pretreat)))}")
    if perf.get("purity_shortfall", False):
        why.append("Requires downstream polishing or suffers off-spec penalty.")

    return {
        "route_id": cand["route_id"],
        "family": family,
        "option_name": cand["option_name"],
        "route_description": cand["route_description"],
        "capex_eur": capex,
        "opex_eur_y": opex,
        "annualized_capex_eur_y": annualized_capex,
        "annual_cost_eur_y": annual_cost,
        "lcoc_eur_t": lcoc,
        "energy_gj_t": energy_gj_t,
        "captured_tpy": captured_tpy,
        "simple_payback_y": simple_payback_y,
        "annual_gross_value_eur_y": annual_gross_value,
        "annual_net_benefit_eur_y": annual_net_benefit,
        "steam_gj_y": steam_gj_y,
        "elec_mwh_y": elec_mwh_y,
        "cooling_m3_y": cooling_m3_y,
        "replacement_eur_y": opex_repl,
        "technical_fit": technical_fit,
        "confidence_score": conf_score,
        "confidence_label": conf_label,
        "benchmark_distance": bdist,
        "nearest_benchmarks": nearest,
        "pretreatment": sorted(set(pretreat_items + imp_pretreat)),
        "post_treatment": downstream_items,
        "equipment_costs": eq_items,
        "capex_core_equipment_eur": eq_capex,
        "capex_integration_eur": integration_amount,
        "capex_installation_contingency_eur": contingency_amount,
        "impurity_warnings": imp_warn,
        "process_context_notes": ctx_notes,
        "why_selected": why,
        "in_window": in_window,
        "trl": perf.get("trl", 8),
        "perf": perf,
        "opex_breakdown_eur_y": {
            "Heat": opex_heat,
            "Electricity": opex_elec,
            "Cooling / misc.": opex_cooling,
            "Chemicals / replacement": opex_repl,
            "Maintenance": opex_maint,
            "Labor": econ.labor_eur_y,
        },
    }


def run_engine(db: DataPack, feed: FeedCase, econ: Economics) -> List[Dict[str, Any]]:
    routes = candidate_routes(db, feed)
    results = []
    for cand in routes:
        out = evaluate_route(db, feed, econ, cand)
        if out is not None:
            results.append(out)
    for r in results:
        # Balanced score: not just cheapest.
        cost_score = 100.0 / (1.0 + r["lcoc_eur_t"] / 80.0)
        energy_score = 100.0 / (1.0 + r["energy_gj_t"] / 3.0)
        maturity_score = (r["trl"] / 9.0) * 100.0
        confidence_score = r["confidence_score"]
        r["balanced_score"] = 0.32 * cost_score + 0.15 * energy_score + 0.24 * r["technical_fit"] + 0.12 * maturity_score + 0.17 * confidence_score
    return sorted(results, key=lambda x: x["balanced_score"], reverse=True)


def family_best(results: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for fam in ["absorption", "adsorption", "membrane", "cryogenic"]:
        fam_routes = [r for r in results if r["family"] == fam]
        if not fam_routes:
            continue
        best = max(fam_routes, key=lambda x: x["balanced_score"])
        rows.append({
            "Family": fam.capitalize(),
            "Best route": best["option_name"],
            "Balanced score": best["balanced_score"],
            "LCOC (€/tCO2)": best["lcoc_eur_t"],
            "Energy (GJ/tCO2)": best["energy_gj_t"],
            "Payback": payback_label(best.get("simple_payback_y")),
            "Confidence": best["confidence_label"],
        })
    return pd.DataFrame(rows).sort_values("Balanced score", ascending=False)


def render_line_ranking(df: pd.DataFrame, x: str, y: str, ylabel: str):
    if df.empty:
        st.info("No ranking data available.")
        return
    dff = df[[x, y]].copy().sort_values(y, ascending=True)
    dff["color"] = [FAMILY_COLORS.get(str(v).lower(), "#64748b") for v in dff[x]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dff[y],
            y=dff[x],
            orientation="h",
            marker=dict(color=dff["color"], line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[f"{v:.1f}" for v in dff[y]],
            textposition="outside",
            textfont=dict(color="#111827", size=12),
            cliponaxis=False,
            hovertemplate=f"%{{y}}<br>{ylabel}: %{{x:.2f}}<extra></extra>",
        )
    )
    fig.update_layout(
        template="simple_white",
        height=320,
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis_title=ylabel,
        yaxis_title="",
        showlegend=False,
        bargap=0.35,
        font=dict(size=13, color="#111827"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.18)", zeroline=False, tickfont=dict(color="#111827", size=12), title_font=dict(color="#111827", size=13))
    fig.update_yaxes(showgrid=False, tickfont=dict(color="#111827", size=12), title_font=dict(color="#111827", size=13))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_equipment_chart(costs: Dict[str, float], family: str, title: str):
    if not costs:
        st.info("No equipment cost breakdown available.")
        return
    items = sorted(costs.items(), key=lambda kv: kv[1], reverse=True)[:8]
    labels = [k.replace("EQ_", "").replace("_", " ") for k, _ in items][::-1]
    vals = [v / 1e6 for _, v in items][::-1]
    color = FAMILY_COLORS.get(family, "#334155")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=vals,
            y=labels,
            orientation="h",
            marker=dict(color=color, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[f"{v:.2f} M€" for v in vals],
            textposition="outside",
            textfont=dict(color="#111827", size=12),
            cliponaxis=False,
            hovertemplate="%{y}<br>CAPEX: %{x:.2f} M€<extra></extra>",
        )
    )
    fig.update_layout(
        template="simple_white",
        height=320,
        margin=dict(l=10, r=30, t=35 if title else 10, b=10),
        xaxis_title="CAPEX (M€)",
        yaxis_title="",
        showlegend=False,
        font=dict(size=13, color="#111827"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=18)) if title else None,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.18)", zeroline=False, tickfont=dict(color="#111827", size=12), title_font=dict(color="#111827", size=13))
    fig.update_yaxes(showgrid=False, tickfont=dict(color="#111827", size=12), title_font=dict(color="#111827", size=13))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_donut_breakdown(parts: Dict[str, float], family: str, title: str, show_value_legend: bool = True, show_pct_labels: bool = True):
    filtered = {k: float(v) for k, v in parts.items() if float(v) > 0}
    if not filtered:
        st.info("No breakdown available.")
        return

    labels = list(filtered.keys())
    vals = list(filtered.values())
    total = sum(vals)
    base = FAMILY_COLORS.get(family, "#2563eb")
    palette = [base, "#93c5fd", "#cbd5e1", "#d1fae5", "#fde68a", "#fecaca"][:len(vals)]

    if show_value_legend:
        legend_labels = [f"{lab}: {money(val)}" for lab, val in zip(labels, vals)]
    else:
        legend_labels = [f"{lab}: {((val/total)*100 if total else 0):.0f}%" for lab, val in zip(labels, vals)]

    textinfo = "percent+label" if show_pct_labels else "none"
    textposition = "outside"

    fig = go.Figure(
        data=[
            go.Pie(
                labels=legend_labels,
                values=vals,
                hole=0.62,
                sort=False,
                direction="clockwise",
                marker=dict(colors=palette, line=dict(color="white", width=2)),
                textinfo=textinfo,
                textposition=textposition,
                textfont=dict(size=12, color="#111827"),
                hovertemplate="%{label}<br>Value: %{value:,.0f} €<br>Share: %{percent}<extra></extra>",
                automargin=True,
            )
        ]
    )

    fig.update_layout(
        template="simple_white",
        height=360,
        margin=dict(l=10, r=10, t=48, b=85),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color="#111827"),
            itemwidth=90,
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=13, color="#111827"),
        title=dict(text=title, x=0.0, xanchor="left", y=0.98, font=dict(size=18)),
        annotations=[
            dict(
                text=f"<b>{money(total)}</b><br><span style='font-size:12px;color:#6b7280'>total</span>",
                x=0.5, y=0.5, showarrow=False, align="center", font=dict(size=15, color="#111827")
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_compact_opex_breakdown(parts: Dict[str, float], family: str):
    st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Annual OPEX breakdown</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([0.9, 1.1])
    with c1:
        render_donut_breakdown(parts, family, "Annual OPEX", show_value_legend=False, show_pct_labels=False)
    with c2:
        rows = [{"OPEX item": k, "Annual value": money(v)} for k, v in sorted(parts.items(), key=lambda kv: kv[1], reverse=True)]
        st.markdown(html_table(pd.DataFrame(rows), index=False), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



def render_overview(results: List[Dict[str, Any]], db: DataPack, feed: FeedCase, econ: Economics):
    top = results[0]
    fam = family_best(results)
    if TWIN_AVAILABLE:
        render_twin_overview_card(results)
    st.markdown(
        f'<div class="cc-banner">Suggested balanced route for current inputs: <b>{top["family"].capitalize()}</b> — '
        f'{top["option_name"]}. This is the best balance of route feasibility, TEA, benchmark distance, and confidence under the current screening logic.</div>',
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Balanced score", f"{top['balanced_score']:.1f}")
    k2.metric("LCOC", f"€{top['lcoc_eur_t']:.1f}/t")
    k3.metric("Energy", f"{top['energy_gj_t']:.2f} GJ/t")
    k4.metric("Confidence", top["confidence_label"])

    c1, c2 = st.columns([1.0, 1.35])
    with c1:
        feed_summary = pd.DataFrame([
            {"Item": "Source", "Value": label_source_name(db, feed.source_id)},
            {"Item": "Flow", "Value": f"{feed.flow_nm3_h:,.0f} Nm³/h"},
            {"Item": "Pressure", "Value": f"{feed.pressure_bar:.2f} bar abs"},
            {"Item": "Temperature", "Value": f"{feed.temperature_c:.1f} °C"},
            {"Item": "Composition basis", "Value": "mol%"},
            {"Item": "Capture target", "Value": f"{feed.capture_target_pct:.0f}%"},
            {"Item": "Product purity target", "Value": f"{feed.product_purity_pct:.0f}%"},
        ])
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Current case summary</div>' + html_table(feed_summary, index=False) + '</div>', unsafe_allow_html=True)
    with c2:
        help_df = pd.DataFrame([
            ["Suggested balanced route", "Best overall screening result after route feasibility, TEA, benchmark distance, and confidence are considered."],
            ["Balanced score", "A combined score using cost, energy, technical fit, maturity, and confidence. It is not a direct economic KPI."],
            ["LCOC", "Screening-level levelized cost of capture for the current modeled route scope."],
            ["Confidence", "How strongly the current route sits inside supported benchmark and validity space."],
            ["Payback", "Simple screening payback from installed CAPEX divided by annual net benefit under the current carbon-price assumption. It is hidden when net benefit is not positive."],
        ], columns=["Metric", "Meaning"])
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">How to read these results</div>' + html_table(help_df, index=False) + '</div>', unsafe_allow_html=True)

    show = fam.copy()
    show["Balanced score"] = show["Balanced score"].map(lambda x: f"{x:.1f}")
    show["LCOC (€/tCO2)"] = show["LCOC (€/tCO2)"].map(lambda x: f"{x:.1f}")
    show["Energy (GJ/tCO2)"] = show["Energy (GJ/tCO2)"].map(lambda x: f"{x:.2f}")
    st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Top options across all families</div>' + html_table(show, index=False) + '</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Cost ranking by family</div>', unsafe_allow_html=True)
        render_line_ranking(fam, "Family", "LCOC (€/tCO2)", "€/tCO2")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Energy ranking by family</div>', unsafe_allow_html=True)
        render_line_ranking(fam, "Family", "Energy (GJ/tCO2)", "GJ/tCO2")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="cc-warning">This is a benchmark-backed engineering screening tool, not detailed process design. Use it to narrow options, not to sign off a project estimate.</div>', unsafe_allow_html=True)




def conceptual_equipment_train(result: Dict[str, Any]) -> List[str]:
    equipment = list(result.get("equipment_costs", {}).keys())
    nice = [e.replace("EQ_", "").replace("_", " ").title() for e in equipment]
    pret = list(result.get("pretreatment", []))
    post = list(result.get("post_treatment", []))
    train = []
    for p in pret:
        train.append(f"Pretreatment: {p}")
    train.extend(nice)
    for p in post:
        train.append(f"Post-treatment: {p}")
    return train


def render_conceptual_pfd(result: Dict[str, Any]):
    steps = conceptual_equipment_train(result)
    if not steps:
        st.info("No conceptual equipment train available for this route.")
        return
    boxes = []
    for i, step in enumerate(steps[:10]):
        arrow = '<div style="font-size:1.4rem;color:#94a3b8;padding:0 0.15rem;">→</div>' if i < len(steps[:10]) - 1 else ''
        box = (
            '<div style="display:flex;align-items:center;gap:0.25rem;">'
            f'<div style="background:#ffffff;border:1px solid #dbe3ef;border-radius:14px;padding:0.75rem 0.9rem;min-width:120px;max-width:190px;box-shadow:0 1px 2px rgba(15,23,42,0.04);">'
            f'<div style="font-size:0.74rem;color:#64748b;font-weight:600;letter-spacing:0.03em;">STEP {i+1}</div>'
            f'<div style="font-size:0.9rem;color:#111827;font-weight:600;line-height:1.3;">{step}</div>'
            '</div>'
            f'{arrow}'
            '</div>'
        )
        boxes.append(box)
    html = (
        '<div class="cc-card-tight">'
        '<div class="cc-section-title">Conceptual PFD</div>'
        '<div class="cc-muted" style="margin-bottom:0.65rem;">Auto-generated process block diagram from the selected route. This is a conceptual screening PFD, not a detailed P&ID.</div>'
        '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.35rem 0.2rem;">' + ''.join(boxes) + '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _df_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_No data available._"
    sub = df.head(max_rows).copy()
    headers = [str(c) for c in sub.columns]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in sub.iterrows():
        vals = []
        for val in row.tolist():
            s = str(val).replace("\n", " ").replace("|", "/")
            vals.append(s)
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)

def build_detailed_report_markdown(result: Dict[str, Any], results: List[Dict[str, Any]], db: DataPack, feed: FeedCase, econ: Economics, sections: Dict[str, str]) -> str:
    fam_table = family_best(results).copy()
    selected_df = pd.DataFrame([
        ["Selected family", result.get("family", "")],
        ["Selected route", result.get("option_name", "")],
        ["Balanced score", f"{result.get('balanced_score', 0.0):.1f}"],
        ["Technical fit", f"{result.get('technical_fit', 0.0):.1f}"],
        ["LCOC", f"€{result.get('lcoc_eur_t', 0.0):.1f}/tCO2"],
        ["Energy", f"{result.get('energy_gj_t', 0.0):.2f} GJ/tCO2"],
        ["Annual capture", f"{result.get('captured_tpy', 0.0):,.0f} tCO2/y"],
        ["Confidence", result.get("confidence_label", "")],
        ["Payback", payback_label(result.get('simple_payback_y'))],
    ], columns=["Parameter", "Value"])
    benchmark_df = benchmark_rows(db, result.get("nearest_benchmarks", []))
    refs_df = literature_rows(db, result.get("family", ""))
    pret_df = pd.DataFrame({"Pretreatment": result.get("pretreatment", [])}) if result.get("pretreatment") else pd.DataFrame()
    post_df = pd.DataFrame({"Post-treatment": result.get("post_treatment", [])}) if result.get("post_treatment") else pd.DataFrame()
    pfd = conceptual_equipment_train(result)

    candidates = pd.DataFrame([
        {
            "Route": r.get("option_name", ""),
            "Balanced score": f"{r.get('balanced_score', 0.0):.1f}",
            "LCOC (€/tCO2)": f"{r.get('lcoc_eur_t', 0.0):.1f}",
            "Energy (GJ/tCO2)": f"{r.get('energy_gj_t', 0.0):.2f}",
            "Confidence": r.get("confidence_label", ""),
        }
        for r in sorted([x for x in results if x.get("family") == result.get("family")], key=lambda x: x.get("balanced_score", 0.0), reverse=True)[:8]
    ])

    equipment_df = pd.DataFrame(
        [{"Equipment": k.replace("EQ_", "").replace("_", " ").title(), "CAPEX": money(v)} for k, v in result.get("equipment_costs", {}).items()]
    ) if result.get("equipment_costs") else pd.DataFrame()

    capex_capsule = pd.DataFrame(
        [{"CAPEX component": k, "Value": money(v)} for k, v in result.get("capex_capsule", {}).items()]
    ) if result.get("capex_capsule") else pd.DataFrame()

    opex_items = pd.DataFrame(
        [{"OPEX item": k, "Annual value": money(v)} for k, v in result.get("opex_breakdown", {}).items()]
    ) if result.get("opex_breakdown") else pd.DataFrame()

    process_flow = "\n".join([f"{i+1}. {step}" for i, step in enumerate(pfd)]) if pfd else "No conceptual process flow available."

    report = (
        f"# Carbon Capture Screening Report\n\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"## 1. Executive summary\n\n{sections['executive']}\n\n"
        f"## 2. Technical summary\n\n{sections['technical']}\n\n"
        f"## 3. Input case\n\n"
        f"- Source archetype: {feed.source_name}\n"
        f"- Gas flow: {feed.flow_nm3_h:,.0f} Nm3/h\n"
        f"- Pressure: {feed.pressure_bar:.2f} bar abs\n"
        f"- Temperature: {feed.temperature_c:.1f} °C\n"
        f"- CO2: {feed.co2_mol_pct:.1f} mol%\n"
        f"- H2: {feed.h2_mol_pct:.1f} mol%\n"
        f"- N2: {feed.n2_mol_pct:.1f} mol%\n"
        f"- CH4: {feed.ch4_mol_pct:.1f} mol%\n"
        f"- CO: {feed.co_mol_pct:.1f} mol%\n"
        f"- H2O: {feed.h2o_mol_pct:.1f} mol%\n"
        f"- Capture target: {feed.capture_target_pct:.1f}%\n"
        f"- Product purity target: {feed.product_purity_pct:.1f}%\n\n"
        f"## 4. Selected route snapshot\n\n{_df_to_markdown(selected_df)}\n\n"
        f"## 5. Best route by family\n\n{_df_to_markdown(fam_table)}\n\n"
        f"## 6. Candidate routes within selected family\n\n{_df_to_markdown(candidates)}\n\n"
        f"## 7. Conceptual process flow\n\n{process_flow}\n\n"
        f"## 8. Triggered pretreatment\n\n{_df_to_markdown(pret_df)}\n\n"
        f"## 9. Triggered post-treatment\n\n{_df_to_markdown(post_df)}\n\n"
        f"## 10. CAPEX component view\n\n{_df_to_markdown(capex_capsule)}\n\n"
        f"## 11. Equipment CAPEX drivers\n\n{_df_to_markdown(equipment_df)}\n\n"
        f"## 12. Annual OPEX breakdown\n\n{_df_to_markdown(opex_items)}\n\n"
        f"## 13. Nearest benchmark cases\n\n{_df_to_markdown(benchmark_df)}\n\n"
        f"## 14. Relevant literature anchors\n\n{_df_to_markdown(refs_df)}\n\n"
        f"## 15. Notes\n\n"
        f"- Graphs remain available in the app for the current run and can be exported separately if needed.\n"
        f"- The report text is deterministic unless AI rewriting is explicitly enabled by the host environment.\n"
        f"- This remains a screening-level engineering result, not FEED, Aspen simulation, or vendor design.\n"
    )
    return report

def build_summary_sections(result: Dict[str, Any], results: List[Dict[str, Any]], db: DataPack, feed: FeedCase, econ: Economics) -> Dict[str, str]:
    fam_results = sorted([r for r in results if r["family"] == result["family"]], key=lambda x: x["balanced_score"], reverse=True)
    runner_up = fam_results[1]["option_name"] if len(fam_results) > 1 else "No close same-family runner-up"
    family_table = family_best(results)
    second_overall = family_table.iloc[1]["Best route"] if len(family_table) > 1 else "No second overall route"
    consistency = "aligned with nearest benchmark anchors" if result.get("benchmark_distance", 1.0) <= 0.25 else ("partly aligned with benchmark anchors" if result.get("benchmark_distance", 1.0) <= 0.6 else "weakly aligned with benchmark anchors")
    pfd = conceptual_equipment_train(result)
    pfd_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(pfd)]) if pfd else "No route equipment list available."
    summary = (
        f"For the current case, the tool selects {result['family']} using the route '{result['option_name']}' as the best balanced option. "
        f"The route achieves an estimated LCOC of €{result['lcoc_eur_t']:.1f}/tCO₂ at an energy demand of {result['energy_gj_t']:.2f} GJ/tCO₂, "
        f"with confidence rated as {result['confidence_label'].lower()}. The estimated capture duty corresponds to approximately "
        f"{result['captured_tpy']:,.0f} tCO₂/y under the current operating-hours assumption. Screening payback is reported as {payback_label(result.get('simple_payback_y'))}."
    )
    why = " ".join(result.get("why_selected", []))
    technical = (
        f"The selected route sits in a pressure/composition regime that gives it a technical-fit score of {result['technical_fit']:.1f}. "
        f"Benchmark consistency is {consistency}. The closest same-family alternative is {runner_up}, while the next best overall family route is {second_overall}. "
        f"Triggered pretreatment requirements are: {', '.join(result.get('pretreatment', [])) or 'none identified at screening level'}. "
        f"Triggered post-treatment requirements are: {', '.join(result.get('post_treatment', [])) or 'none beyond standard conditioning'}. "
        f"Key process-context notes are: {', '.join(result.get('process_context_notes', [])) or 'no additional context penalties recorded'}."
    )
    report = (
        f"Case Summary — {feed.source_name.replace('_',' ')}\n\n"
        f"The route-first screening framework identifies {result['option_name']} in the {result['family']} family as the recommended route for the specified input conditions. "
        f"The recommendation is driven by the combined effect of route feasibility, balanced-score ranking, benchmark distance, and confidence scoring. "
        f"At the current assumptions, the route delivers €{result['lcoc_eur_t']:.1f}/tCO₂, {result['energy_gj_t']:.2f} GJ/tCO₂, and annual capture of {result['captured_tpy']:,.0f} tCO₂/y. "
        f"The route remains {consistency}. {why}\n\n"
        f"From a process-engineering standpoint, the route requires the following conceptual train:\n{pfd_text}\n\n"
        f"The principal CAPEX drivers are {', '.join([k.replace('EQ_','').replace('_',' ').lower() for k in list(result.get('equipment_costs', {}).keys())[:3]]) or 'not available'}, "
        f"while the dominant annual operating-cost elements follow the route-specific electricity, heat, labor, maintenance, and consumables burdens already included in the screening TEA. "
        f"This text is screening-level and should be treated as pre-design narrative, not as a detailed process design basis."
    )
    return {
        "executive": summary,
        "technical": technical,
        "report": report,
        "pfd": pfd_text,
    }

def try_ai_summary(payload: Dict[str, Any], sections: Dict[str, str]) -> Dict[str, str] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        try:
            from openai import OpenAI
        except Exception:
            return None
        client = OpenAI(api_key=api_key)
        prompt = (
            "You are assisting with a chemical process engineering screening tool. "
            "Rewrite the supplied deterministic screening summary into concise, technically grounded report text. "
            "Do not invent calculations, routes, or literature. Use only the provided facts. "
            "Return JSON with keys executive, technical, report."
        )
        resp = client.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"payload": payload, "sections": sections}, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = resp.output_text.strip()
        try:
            data = json.loads(content)
            if all(k in data for k in ["executive", "technical", "report"]):
                return data
        except Exception:
            return {"executive": content, "technical": sections["technical"], "report": sections["report"]}
    except Exception:
        return None
    return None



def render_twin_overview_card(results: List[Dict[str, Any]]) -> None:
    """Show a compact twin validation summary across all families."""
    validated_families = [
        r["family"] for r in results
        if r.get("twin_validated") and r.get("twin_source")
    ]
    if not validated_families:
        return
    unique_fam = sorted(set(validated_families))
    fam_str = ", ".join(f.capitalize() for f in unique_fam)
    st.markdown(
        f'<div class="cc-card" style="border-color:#a7f3d0;background:#f0fdf4;">'
        f'<b>🔬 Twin-validated families:</b> {fam_str} — '
        f'energy demand independently confirmed by rigorous process models. '
        f'See each family tab for detail.</div>',
        unsafe_allow_html=True,
    )


def render_summary_tab(results: List[Dict[str, Any]], db: DataPack, feed: FeedCase, econ: Economics):
    top = results[0]
    fam_table = family_best(results)
    st.subheader("Summary & report")
    st.markdown(
        '<div class="cc-card-tight"><div class="cc-section-title">How to use this tab</div>'
        '<div class="cc-muted">This tab converts the calculated screening result into a compact engineering report shell. '
        'The calculations remain deterministic; AI, if enabled, only rewrites the result into report-style text.</div></div>',
        unsafe_allow_html=True,
    )

    sections = build_summary_sections(top, results, db, feed, econ)
    payload = {
        "selected_family": top["family"],
        "selected_route": top["option_name"],
        "lcoc_eur_t": top["lcoc_eur_t"],
        "energy_gj_t": top["energy_gj_t"],
        "confidence": top["confidence_label"],
        "payback": payback_label(top.get("simple_payback_y")),
        "captured_tpy": top["captured_tpy"],
        "pretreatment": top.get("pretreatment", []),
        "post_treatment": top.get("post_treatment", []),
        "nearest_benchmarks": top.get("nearest_benchmarks", []),
        "benchmark_distance": top.get("benchmark_distance", None),
    }

    use_ai = st.toggle("Use AI rewriting (requires OPENAI_API_KEY on the host)", value=False)
    final_sections = sections
    if use_ai:
        ai_sections = try_ai_summary(payload, sections)
        if ai_sections:
            final_sections = {**sections, **ai_sections}
            st.success("AI rewrite applied to the narrative text.")
        else:
            st.warning("AI rewrite was requested but no usable API configuration was available. Showing deterministic summary instead.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Executive summary</div>'
                    f'<div class="cc-small">{final_sections["executive"]}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Technical summary</div>'
                    f'<div class="cc-small">{final_sections["technical"]}</div></div>', unsafe_allow_html=True)

    if not fam_table.empty:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Best route by family</div>' +
                    html_table(fam_table.head(4), index=False) + '</div>', unsafe_allow_html=True)

    render_conceptual_pfd(top)

    report_text = build_detailed_report_markdown(top, results, db, feed, econ, final_sections)

    with st.expander("Report-ready text", expanded=True):
        st.text_area("Generated report text", report_text, height=560)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Download report text (.md)",
                data=report_text,
                file_name=f"screening_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
            )
        with d2:
            st.download_button(
                "Download report text (.txt)",
                data=report_text,
                file_name=f"screening_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
            )

    with st.expander("Reference and benchmark note", expanded=False):
        refs = literature_rows(db, top["family"])
        nb = benchmark_rows(db, top.get("nearest_benchmarks", []))
        if not nb.empty:
            st.markdown("**Nearest benchmark cases**", unsafe_allow_html=True)
            st.markdown(html_table(nb, index=False), unsafe_allow_html=True)
        if not refs.empty:
            st.markdown("**Relevant literature anchors**", unsafe_allow_html=True)
            st.markdown(html_table(refs, index=False), unsafe_allow_html=True)




# ─────────────────────────────────────────────────────────────────────────
# v2.1 — Twin model panel
# ─────────────────────────────────────────────────────────────────────────
def render_twin_panel(best: Dict[str, Any], family: str) -> None:
    """
    Render the twin-model validation panel for the best route in a family.
    Called from render_family_tab() when twin data is present.
    Displays twin energy vs screening energy, profiles, and confidence upgrade.
    """
    validated   = best.get("twin_validated", False)
    twin_source = best.get("twin_source")

    if not twin_source:
        return   # no twin ran — silent

    # ── Header badge ──────────────────────────────────────────────────────
    badge_color = "#ecfdf5" if validated else "#fffbeb"
    badge_border= "#a7f3d0" if validated else "#fde68a"
    badge_text  = "#065f46" if validated else "#92400e"
    badge_label = "✅ Twin-validated" if validated else "⚠ Twin ran — outside lit. range"
    st.markdown(
        f'<div style="background:{badge_color};border:1px solid {badge_border};'
        f'border-radius:10px;padding:0.6rem 1rem;margin-bottom:0.6rem;'
        f'color:{badge_text};font-weight:600;">'
        f'{badge_label} · Source: <code>{twin_source}</code></div>',
        unsafe_allow_html=True,
    )

    # ── Energy comparison ─────────────────────────────────────────────────
    screening_E = best.get("screening_energy_GJ_t")
    twin_E      = best.get("twin_energy_GJ_t")
    Q_twin      = best.get("twin_Q_specific_GJ_t")
    W_twin      = best.get("twin_W_specific_MWh_t")
    lit_range   = best.get("twin_lit_range", (None, None))

    col1, col2, col3 = st.columns(3)
    if screening_E is not None:
        col1.metric("Screening energy", f"{screening_E:.2f} GJ/t",
                    help="Database mid-point from regeneration energy range")
    if twin_E is not None:
        delta = twin_E - screening_E if screening_E else None
        delta_str = f"{delta:+.2f} GJ/t" if delta is not None else None
        col2.metric("Twin energy", f"{twin_E:.2f} GJ/t", delta=delta_str,
                    help="Rigorous twin model computation")
    if W_twin is not None:
        col3.metric("Twin electricity", f"{W_twin:.3f} MWh/t",
                    help="Compression / refrigeration / pump work from twin")

    # ── Literature range check ─────────────────────────────────────────────
    if lit_range[0] is not None:
        st.markdown(
            f'<div class="cc-card-tight cc-muted">Literature range: '
            f'<b>{lit_range[0]}</b> – <b>{lit_range[1]}</b> '
            f'{"GJ/t (heat)" if Q_twin is not None else "MWh/t (electricity)"} · '
            f'{"Within range ✓" if validated else "Outside range ⚠"}</div>',
            unsafe_allow_html=True,
        )

    # ── Family-specific detail ─────────────────────────────────────────────
    if family == "absorption":
        rows = []
        for label, key, fmt in [
            ("Capture rate",     "twin_capture_rate",    ".1%"),
            ("Rich loading α",   "twin_alpha_rich",      ".3f"),
            ("Lean loading α",   "twin_alpha_lean",      ".3f"),
            ("L/G ratio",        "twin_L_G_ratio",       ".2f"),
            ("Reboiler duty MW", "twin_reboiler_MW",     ".1f"),
            ("Q reaction GJ/t",  "twin_Q_reaction_GJ_t", ".2f"),
            ("Q latent GJ/t",    "twin_Q_latent_GJ_t",   ".2f"),
            ("Q sensible GJ/t",  "twin_Q_sensible_GJ_t", ".2f"),
        ]:
            val = best.get(key)
            if val is not None:
                rows.append({"Parameter": label, "Value": format(val, fmt)})
        if rows:
            df = pd.DataFrame(rows)
            st.markdown(
                '<div class="cc-card-tight"><div class="cc-section-title">Absorber simulation detail</div>'
                + html_table(df, index=False) + '</div>',
                unsafe_allow_html=True,
            )

    elif family == "adsorption":
        rows = []
        for label, key, fmt in [
            ("Working capacity mol/kg", "twin_working_capacity", ".3f"),
            ("Bed inventory kg",        "twin_bed_inventory_kg", ",.0f"),
            ("Electricity MWh/t",       "twin_W_specific_MWh_t", ".3f"),
            ("Steam GJ/t",              "twin_Q_specific_GJ_t",  ".2f"),
            ("Purity achievable",       "twin_purity_achievable", ""),
            ("Compatibility",           "twin_compatibility",     ""),
        ]:
            val = best.get(key)
            if val is not None:
                rows.append({"Parameter": label,
                             "Value": format(val, fmt) if fmt else str(val)})
        if rows:
            df = pd.DataFrame(rows)
            st.markdown(
                '<div class="cc-card-tight"><div class="cc-section-title">Adsorption cycle detail</div>'
                + html_table(df, index=False) + '</div>',
                unsafe_allow_html=True,
            )

    elif family == "membrane":
        rows = []
        for label, key, fmt in [
            ("CO2 purity %",       "twin_purity_pct",       ".1f"),
            ("CO2 recovery",       "twin_recovery",          ".1%"),
            ("Electricity MWh/t",  "twin_W_specific_MWh_t",  ".3f"),
            ("Membrane area m²",   "twin_membrane_area_m2",  ",.0f"),
            ("Permeance GPU",      "twin_perm_GPU",           ".0f"),
            ("Eff. selectivity α", "twin_alpha_eff",          ".1f"),
            ("Purity meets spec",  "twin_purity_meets_spec",  ""),
        ]:
            val = best.get(key)
            if val is not None:
                rows.append({"Parameter": label,
                             "Value": format(val, fmt) if fmt else str(val)})
        if rows:
            df = pd.DataFrame(rows)
            st.markdown(
                '<div class="cc-card-tight"><div class="cc-section-title">Membrane separation detail</div>'
                + html_table(df, index=False) + '</div>',
                unsafe_allow_html=True,
            )

    elif family == "cryogenic":
        rows = []
        for label, key, fmt in [
            ("CO2 purity %",        "twin_purity_pct",       ".1f"),
            ("CO2 recovery",        "twin_recovery",          ".1%"),
            ("W total MWh/t",       "twin_W_specific_MWh_t",  ".3f"),
            ("W compression MWh/t", "twin_W_compression",     ".3f"),
            ("W refrigeration MWh/t","twin_W_refrigeration",  ".3f"),
            ("W drying MWh/t",      "twin_W_drying",          ".3f"),
            ("Feasible",            "twin_feasible",           ""),
            ("Above P gate",        "twin_above_P_gate",       ""),
        ]:
            val = best.get(key)
            if val is not None:
                rows.append({"Parameter": label,
                             "Value": format(val, fmt) if fmt else str(val)})
        if rows:
            df = pd.DataFrame(rows)
            st.markdown(
                '<div class="cc-card-tight"><div class="cc-section-title">Cryogenic separation detail</div>'
                + html_table(df, index=False) + '</div>',
                unsafe_allow_html=True,
            )

    # ── Warnings ──────────────────────────────────────────────────────────
    twin_warns = best.get("twin_warnings", [])
    if twin_warns:
        with st.expander("Twin model warnings", expanded=False):
            for w in twin_warns:
                st.warning(w)

    # ── Confidence label upgrade ───────────────────────────────────────────
    if validated:
        st.markdown(
            '<div class="cc-card-tight" style="border-color:#a7f3d0;">'
            '<b>Confidence upgrade:</b> This route energy demand has been '
            'independently validated by a rigorous twin model. Confidence is '
            'elevated above the database-range-only estimate.</div>',
            unsafe_allow_html=True,
        )


def render_family_tab(results: List[Dict[str, Any]], family: str, db: DataPack):
    fam_results = [r for r in results if r["family"] == family]
    if not fam_results:
        st.info("No feasible routes found.")
        return
    fam_results = sorted(fam_results, key=lambda x: x["balanced_score"], reverse=True)
    best = fam_results[0]
    st.subheader(family.capitalize())
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Selected route", best["option_name"])
    c2.metric("Balanced score", f"{best['balanced_score']:.1f}")
    c3.metric("LCOC", f"€{best['lcoc_eur_t']:.1f}/tCO₂")
    # Show twin energy if available, else screening estimate
    _twin_E = best.get("twin_energy_GJ_t")
    _scr_E  = best.get("energy_gj_t", 0.0)
    if _twin_E is not None:
        _delta_E = _twin_E - _scr_E
        c4.metric("Energy (twin)", f"{_twin_E:.2f} GJ/tCO₂",
                  delta=f"{_delta_E:+.2f} vs screening",
                  help="Twin-model computed value. Δ vs database mid-point.")
    else:
        c4.metric("Energy", f"{best['energy_gj_t']:.2f} GJ/tCO₂")
    # Upgrade confidence label when twin validates
    _conf_label = best["confidence_label"]
    if best.get("twin_validated"):
        _conf_label = _conf_label + " ✓"
    c5.metric("Confidence", _conf_label,
              help="✓ = twin model independently validated energy demand")
    c6.metric("Payback", payback_label(best.get("simple_payback_y")))

    consistency = "Aligned" if best.get("benchmark_distance", 1.0) <= 0.25 else ("Watch" if best.get("benchmark_distance", 1.0) <= 0.6 else "Weak")
    st.markdown(
        f'<div class="cc-card-tight"><b>Benchmark consistency:</b> {consistency}. '
        f'Nearest anchor(s): {", ".join(best["nearest_benchmarks"]) if best["nearest_benchmarks"] else "none"} '
        f'(distance {best["benchmark_distance"]:.2f}).</div>',
        unsafe_allow_html=True,
    )

    # ── v2.1: Twin model panel ────────────────────────────────────────────
    if TWIN_AVAILABLE and best.get("twin_source"):
        with st.expander("🔬 Twin model validation", expanded=True):
            render_twin_panel(best, family)

    top_left, top_right = st.columns([1.05, 1.1])
    with top_left:
        with st.expander("Why this route was selected", expanded=True):
            for line in best["why_selected"]:
                st.write(f"- {line}")
            st.write(f"- Benchmark consistency classification: {consistency}.")
            st.write(f"- Confidence level: {best['confidence_label']}.")
            st.write(f"- Screening payback: {payback_label(best.get('simple_payback_y'))}.")
    with top_right:
        tech = pd.DataFrame([
            ["Technical fit", f"{best['technical_fit']:.1f}"],
            ["Energy", f"{best['energy_gj_t']:.2f} GJ/tCO₂"],
            ["Annual capture", f"{best['captured_tpy']:,.0f} t/y"],
            ["Annual OPEX", money(best['opex_eur_y'])],
            ["Annualized CAPEX", money(best['annualized_capex_eur_y'])],
            ["Screening payback", payback_label(best.get("simple_payback_y"))],
            ["TRL", str(best['trl'])],
        ], columns=["Parameter", "Value"])
        if best.get("perf"):
            for k, v in best["perf"].items():
                if isinstance(v, (int, float)) and k not in ["trl"]:
                    tech.loc[len(tech)] = [k.replace('_',' ').capitalize(), f"{v:,.2f}"]
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Technical summary</div>' + html_table(tech, index=False) + '</div>', unsafe_allow_html=True)

    mid_left, mid_right = st.columns([1.1, 0.9])
    with mid_left:
        opt_rows = []
        for r in fam_results[:8]:
            twin_E = r.get("twin_energy_GJ_t")
            twin_tag = " ✓" if r.get("twin_validated") else ""
            opt_rows.append({
                "Route": r["option_name"],
                "LCOC (€/tCO₂)": f"{r['lcoc_eur_t']:.1f}",
                "Energy (GJ/tCO₂)": f"{r['energy_gj_t']:.2f}",
                "Twin energy": f"{twin_E:.2f}" if twin_E else "—",
                "Balanced": f"{r['balanced_score']:.1f}",
                "TRL": r["trl"],
                "Confidence": r["confidence_label"] + twin_tag,
            })
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Compare candidate options and process-engineering aspects</div>' + html_table(pd.DataFrame(opt_rows), index=False) + '</div>', unsafe_allow_html=True)
    with mid_right:
        with st.expander("Triggered pretreatment and impurity constraints", expanded=False):
            st.write("**Pretreatment**")
            render_string_list_table(best["pretreatment"], "pretreatment")
            st.write("**Impurity / feed-quality impacts**")
            render_string_list_table(best["impurity_warnings"], "impurity_warning")
        with st.expander("Triggered post-treatment and process-context effects", expanded=False):
            st.write("**Post-treatment**")
            render_string_list_table(best["post_treatment"], "post_treatment")
            st.write("**Process context**")
            render_string_list_table(best["process_context_notes"], "process_context_note")

    capex_parts = {
        "Core equipment": best.get("capex_core_equipment_eur", 0.0),
        "Pretreat / post-treat / integration": best.get("capex_integration_eur", 0.0),
        "Installation / contingency": best.get("capex_installation_contingency_eur", 0.0),
    }
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">CAPEX component view</div>', unsafe_allow_html=True)
        render_donut_breakdown(capex_parts, family, "Installed CAPEX")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="cc-card-tight"><div class="cc-section-title">Equipment CAPEX drivers</div>', unsafe_allow_html=True)
        render_equipment_chart(best["equipment_costs"], family, "")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Annual OPEX breakdown", expanded=False):
        render_compact_opex_breakdown(best.get("opex_breakdown_eur_y", {}), family)

    with st.expander("Nearest benchmark cases", expanded=False):
        nb = benchmark_rows(db, best.get("nearest_benchmarks", []))
        if not nb.empty:
            st.markdown(html_table(nb, index=False), unsafe_allow_html=True)
        else:
            st.write("No matching benchmark rows found.")

    with st.expander("Relevant literature anchors", expanded=False):
        tea = literature_rows(db, family)
        if not tea.empty:
            st.markdown(html_table(tea, index=False), unsafe_allow_html=True)
        else:
            st.write("No TEA literature rows available for this family in the current pack.")

    with st.expander("Assumptions and limits", expanded=False):
        for line in generic_assumptions(best, family):
            st.write(f"- {line}")


def main():
    st.set_page_config(page_title="Carbon Capture Screening v1.8.8", layout="wide")
    apply_styles()
    st.title("Carbon Capture Screening Tool v2.1")
    st.caption("Route-first screening with Database V6 · Twin-validated energy models · v2.1 — Haroon Al Kasim Panangadantakath")
    try:
        db = load_data()
    except Exception as e:
        st.error(str(e))
        return
    feed, econ, run = build_feed_case(db)
    st.session_state.econ = econ
    st.session_state.db = db
    st.session_state.feed = feed
    if not run:
        st.info("Enter the case and run the screening. Custom mode is available again for niche validation.")
        return
    with st.spinner("Running route-first screening..."):
        results = run_engine(db, feed, econ)
    if not results:
        st.error("No feasible routes found for the current input set.")
        return

    # ── v2.1: Twin-validate best route per family ─────────────────────────
    if TWIN_AVAILABLE:
        with st.spinner("Running twin models for energy validation..."):
            try:
                results = enrich_all_results(feed, results)
            except Exception as _twin_err:
                pass   # twin enrichment is non-blocking — screening continues
    tabs = st.tabs(["Overview", "Absorption", "Adsorption", "Membrane", "Cryogenic", "Summary"])
    with tabs[0]:
        render_overview(results, db, feed, econ)
    with tabs[1]:
        render_family_tab(results, "absorption", db)
    with tabs[2]:
        render_family_tab(results, "adsorption", db)
    with tabs[3]:
        render_family_tab(results, "membrane", db)
    with tabs[4]:
        render_family_tab(results, "cryogenic", db)
    with tabs[5]:
        render_summary_tab(results, db, feed, econ)


if __name__ == "__main__":
    main()