"""
params.py — techno-economic inputs for the two-stage LCOF model (Appendix A3 /
LCOF_plan.tex).  Costs in real USD; power in MW, energy in MWh (LHV); fuel costs
reported per GJ (LHV).

Tables mirror LCOF_plan.tex Table 2 (cost inputs) and Table 1 (stage-2 cascade).
Synthesis CAPEX and mu_el are literature placeholders (Schemme 2020 refinement is
open item 6 in the handoff).
"""

# ---- finance -----------------------------------------------------------------
WACC_DEFAULT = 0.07      # used only when a cell has no country WACC


def crf(r: float, n: float) -> float:
    """Capital recovery factor r(1+r)^n / ((1+r)^n - 1)."""
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


# ---- stage-1 technologies (LCOF_plan Table 2) --------------------------------
# capex: $/MW for power techs, $/MWh for storage-energy capacity.
TECH = {
    "pv":                     dict(capex=600e3,  life=25, opex=0.015),
    "wind_onshore":           dict(capex=1200e3, life=25, opex=0.025),
    "wind_offshore_fixed":    dict(capex=3300e3, life=25, opex=0.030),
    "wind_offshore_floating": dict(capex=5500e3, life=25, opex=0.035),
    "electrolyzer":           dict(capex=700e3,  life=20, opex=0.030),
    "h2_storage":             dict(capex=15e3,   life=30, opex=0.010),  # $/MWh_H2 tank
    "battery_power":          dict(capex=120e3,  life=15, opex=0.020),
    "battery_energy":         dict(capex=200e3,  life=15, opex=0.000),
}


def annuity(tech: str, r: float, capex_override: float | None = None) -> float:
    """Annualised fixed cost per unit capacity at WACC r ($/MW/yr or $/MWh/yr)."""
    t = TECH[tech]
    capex = t["capex"] if capex_override is None else capex_override
    return (crf(r, t["life"]) + t["opex"]) * capex


# ---- stage-1 operation / feedstock -------------------------------------------
ETA_EL = 0.65        # electrolyser: MWh_H2 (LHV) per MWh_el, constant (A3)
ETA_CH = 0.95        # battery charge efficiency
ETA_DH = 0.95        # battery discharge efficiency
OMEGA_H2O = 0.30     # t water per MWh_H2 (~10 kg/kg H2: stoichiometric minimum
                     # is 8.94 kg/kg = 0.268 t/MWh; + purification losses)
C_WATER_DEFAULT = 2.0   # $/t delivered water when no cell map value
LHV_H2_KWH_KG = 33.33   # kWh/kg (120 MJ/kg)

# ---- stage-2 cascade (LCOF_plan Table 1) -------------------------------------
# eta_syn : GJ fuel (LHV) per GJ H2 -> mu_h2 = 1/eta_syn
# mu_co2  : t CO2 per GJ fuel        (reaction stoichiometry)
# mu_n2   : t N2 per GJ fuel          (ammonia only)
# mu_el   : GJ direct electricity per GJ fuel (ASU, RWGS, compression) [placeholder]
# syn_capex : $/kW fuel output; cf_syn : synthesis load factor
# native  : conversions from $/GJ to native units (multiplier)
CF_SYN = 0.90
# N2 is made by the plant's OWN air-separation unit: its CAPEX is inside
# ammonia's syn_capex (the paper's tab:synparams says "Haber-Bosch loop;
# air-separation unit") and its electricity is inside ammonia's mu_el. A
# merchant N2 price on top of that charged nitrogen three times — the
# 2026-08-12 coauthor audit caught it. Keep mu_n2 as the (real) mass flow;
# price it at zero.
C_N2_DEFAULT = 0.0       # $/t N2 (own ASU; was 30 $/t merchant = double count)
C_CO2_DAC = 500.0        # $/t DAC at TODAY's cost (2025: $400-600, Climeworks/
                         # IEA); 2030/2050 values live in VINTAGES

# 2026-10-07 (b) synthesis capex: IEA Global Hydrogen Review 2026, Assumptions Annex, 2025
# installed costs in 2025 US$ (the latest year IEA reports), per tonne of annual output converted to
# US$ per kW of fuel output at nameplate (1 t/yr = LHV / 31.536 GJ per kW-yr):
#   Haber-Bosch incl. ASU 560-980 US$/(t NH3/yr), midpoint 770, 18.6 GJ/t   -> 1,306 US$/kW, O&M 3%
#   methanol synthesis incl. distillation 220 US$/(t MeOH/yr), 19.9 GJ/t    ->   349 US$/kW, O&M 3%
#   Fischer-Tropsch 2,770 US$/(t liquids/yr), 43.0 GJ/t                     -> 2,032 US$/kW,
#       O&M 5% fixed + 1.5% variable = 6.5%
# Lifetime 25 years (the annex's common assumption). Methanation keeps 700 (DEA renewable-fuels
# catalogue ~685). CO2-to-ethanol: no published plant cost; the methanol loop's value is used as
# the closest analogue (stated as an assumption). Previous values (IEA 2023 e-fuels, 2022 data):
# 1,378 / 1,482 / 2,903 US$/kW (lcof/params.py.pre_ghr2026).
FUELS = {
    "hydrogen":  dict(eta_syn=1.00, mu_co2=0.000, mu_n2=0.0,    mu_el=0.000,
                      syn_capex=50e3,  syn_life=20, syn_opex=0.03,
                      native={"$/kg": 0.120}),
    # eta_syn is H2-IN-FUEL ONLY (electricity is mu_el, by the convention
    # above): 180 kg H2/t NH3 (stoichiometric 176.5 + ~2 % purge; PtX-Hub,
    # hydrogentechworld, Fasihi 2021) -> 18.6/(0.180*120) = 0.86, ceiling
    # 0.878. The old 0.70 was a power-to-ammonia figure INCLUSIVE of
    # electricity and double-counted mu_el. mu_el raised to match the same
    # sources: HB loop incl. separation 0.6-0.7 + ASU 0.2-0.3 MWh/t
    # => ~0.9 MWh/t = 0.17 GJ/GJ (the old 0.06 was too small once eta was
    # H2-only).
    "ammonia":   dict(eta_syn=0.86, mu_co2=0.000, mu_n2=0.0442, mu_el=0.170,
                      syn_capex=1306e3, syn_life=25, syn_opex=0.03,
                      native={"$/t": 18.6}),
    "methanol":  dict(eta_syn=0.80, mu_co2=0.069, mu_n2=0.0,    mu_el=0.020,
                      syn_capex=349e3, syn_life=25, syn_opex=0.03,
                      native={"$/t": 19.9}),
    "e-methane": dict(eta_syn=0.78, mu_co2=0.055, mu_n2=0.0,    mu_el=0.015,
                      syn_capex=700e3, syn_life=25, syn_opex=0.04,
                      native={"$/MWh": 3.6, "$/MMBtu": 1.0551}),
    "e-diesel":  dict(eta_syn=0.70, mu_co2=0.072, mu_n2=0.0,    mu_el=0.040,
                      syn_capex=2032e3, syn_life=25, syn_opex=0.065,
                      native={"$/L": 0.0358, "$/bbl": 5.69}),
    "e-kerosene": dict(eta_syn=0.70, mu_co2=0.072, mu_n2=0.0,   mu_el=0.040,
                      syn_capex=2032e3, syn_life=25, syn_opex=0.065,
                      native={"$/L": 0.0351, "$/t": 43.0}),
    # 2026-10-07: the marine fuel, e-methanol and e-ammonia 70/30 by energy (the
    # dual-fuel orderbook split). Its cost per GJ is the same mix of the two
    # cascades: 1/eta, mu_co2, mu_n2 and mu_el are energy-weighted; the synthesis
    # annuity (25 yr for both) is reproduced exactly by the weighted capex and
    # the capex-weighted O&M share. Traded per tonne of fuel-oil equivalent
    # (40.2 GJ/t, IMO lower calorific value of heavy fuel oil).
    "marine":    dict(eta_syn=1.0 / (0.7 / 0.80 + 0.3 / 0.86),
                      mu_co2=0.7 * 0.069, mu_n2=0.3 * 0.0442,
                      mu_el=0.7 * 0.020 + 0.3 * 0.170,
                      syn_capex=0.7 * 349e3 + 0.3 * 1306e3, syn_life=25,
                      syn_opex=(0.7 * 349e3 * 0.03 + 0.3 * 1306e3 * 0.03) / (0.7 * 349e3 + 0.3 * 1306e3),
                      native={"$/t": 40.2}),
    # CO2-hydrogenation route (gas-fermentation sensitivity handled separately)
    "ethanol":   dict(eta_syn=0.72, mu_co2=0.071, mu_n2=0.0,    mu_el=0.030,
                      syn_capex=349e3, syn_life=25, syn_opex=0.03,
                      native={"$/t": 26.8, "$/L": 0.0212}),
}

MMBTU_PER_GJ = 1.0551    # $/MMBtu = $/GJ * 1.0551 (team common unit)

# ---- alternative synthesis routes (same LCOH field, different cascade) -------
# Parameters verified by lcof/verify_routes.py (thermo ceiling + stoichiometry).
# MtJ capex = MeOH plant scaled to jet output (800/0.875) + upgrading train.
ALT_ROUTES = {
    "e-kerosene (MtJ)": dict(base="e-kerosene", eta_syn=0.70, mu_co2=0.073,
                             mu_n2=0.0, mu_el=0.033, syn_capex=1360e3,
                             syn_life=25, syn_opex=0.04,
                             native={"$/L": 0.0351, "$/t": 43.0}),
    "ethanol (gas fermentation)": dict(base="ethanol", eta_syn=0.62,
                                       mu_co2=0.071, mu_n2=0.0, mu_el=0.050,
                                       syn_capex=1200e3, syn_life=20,
                                       syn_opex=0.05,
                                       native={"$/t": 26.8, "$/L": 0.0212}),
    "e-methane (biological)": dict(base="e-methane", eta_syn=0.75,
                                   mu_co2=0.055, mu_n2=0.0, mu_el=0.010,
                                   syn_capex=550e3, syn_life=20, syn_opex=0.05,
                                   native={"$/MWh": 3.6}),
}

# benchmark band (NOT an e-fuel): steel-mill off-gas fermentation ethanol,
# CO priced at opportunity cost (fuel-value replacement) + cleanup
ETOH_OFFGAS_BAND_GJ = (17.0, 24.0)   # $/GJ  (~$450-650/t)

# ---- cost-year vintages (2025 = TECH/ETA_EL baselines above) -----------------
# Projections: NREL ATB 2024 (moderate), IEA Net Zero, IRENA, DNV ETO; DAC:
# IEA/Mission Zero trajectories. syn_scale = uniform learning on synthesis
# CAPEX. A vintage bundles ALL cost assumptions consistently — never mix the
# 2050 CO2 map with 2025 equipment.
# WARNING — PLACEHOLDER, NOT A PROJECTION.
# The 2030/2050 entries below are round numbers with no cited source, cover only
# two years, and touch neither capacity factor nor WACC. They must not be used
# to produce results. The projection method (five-year steps, published cost
# trajectories, recomputed CF, decomposed WACC, and the deliberate NON-projection
# of fossil prices) is specified in PROJECTION_METHOD.md and is pending sign-off.
VINTAGES = {
    2025: {},
    2030: dict(capex=dict(pv=500e3, wind_onshore=1100e3,
                          wind_offshore_fixed=2600e3, electrolyzer=450e3,
                          h2_storage=12e3, battery_energy=150e3),
               eta_el=0.67, dac=300.0, syn_scale=0.90),
    2050: dict(capex=dict(pv=400e3, wind_onshore=950e3,
                          wind_offshore_fixed=2000e3, electrolyzer=250e3,
                          h2_storage=10e3, battery_energy=100e3),
               eta_el=0.70, dac=110.0, syn_scale=0.80),
}


# pristine 2025 base, captured at import time so apply_vintage can be
# IDEMPOTENT (the old version multiplied syn_capex in place on every
# call — two calls compounded the scale)
_BASE_TECH_CAPEX = {t: d["capex"] for t, d in TECH.items()}
_BASE_SYN = {f: d["syn_capex"] for f, d in FUELS.items()}
_BASE_SYN_ALT = {f: d["syn_capex"] for f, d in ALT_ROUTES.items()}
_BASE_ETA_EL, _BASE_DAC = ETA_EL, C_CO2_DAC


def apply_vintage(year: int) -> None:
    """Set module-level cost assumptions to the given vintage.
    Idempotent: always applied from the pristine 2025 base, so
    repeated or out-of-order calls cannot compound."""
    global ETA_EL, C_CO2_DAC
    for t, capex in _BASE_TECH_CAPEX.items():
        TECH[t]["capex"] = capex
    for f, cap in _BASE_SYN.items():
        FUELS[f]["syn_capex"] = cap
    for f, cap in _BASE_SYN_ALT.items():
        ALT_ROUTES[f]["syn_capex"] = cap
    ETA_EL, C_CO2_DAC = _BASE_ETA_EL, _BASE_DAC
    v = VINTAGES.get(year, {})
    for tech, capex in v.get("capex", {}).items():
        TECH[tech]["capex"] = capex
    if "eta_el" in v:
        ETA_EL = v["eta_el"]
    if "dac" in v:
        C_CO2_DAC = v["dac"]
    if "syn_scale" in v:
        for f in FUELS.values():
            f["syn_capex"] *= v["syn_scale"]
        for f in ALT_ROUTES.values():
            f["syn_capex"] *= v["syn_scale"]


def syn_cost_per_gj(fuel: str, r: float) -> float:
    """c_syn: annualised synthesis CAPEX+O&M per GJ fuel at load factor CF_SYN."""
    f = FUELS[fuel]
    a = (crf(r, f["syn_life"]) + f["syn_opex"]) * f["syn_capex"]   # $/MW_fuel/yr
    return a / (CF_SYN * 8760 * 3.6)                               # $/GJ
