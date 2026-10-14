# Region- / class-appropriate renewable technology for CF generation

Reviewer concern: a single global turbine (low-specific-power NREL 4 MW) over-
states capacity factor at very windy sites, where such a machine would never be
deployed. Likewise a single fixed-tilt PV array understates yield in sunny
markets that now overwhelmingly use trackers. We therefore choose technology by
local wind regime (wind) and by resource quality (PV), following the standard
IEC / NREL ATB practice of matching turbine configuration to the site.

## 1. Wind — IEC 61400-1 class matching

IEC 61400-1 defines turbine classes by design mean/extreme wind speed
(Class I ≈ 10, II ≈ 8.5, III ≈ 7.5 m/s). Low-wind (III) machines have **larger
rotors and taller towers** (low specific power → high CF); high-wind (I)
machines are **robust, smaller-rotor** (high specific power → lower CF but
survive storms). Modern fleets have trended to low specific power: US average
fell from **393 W/m² (1998) → 233 W/m² (2022)**, hub height **~103 m (2023)**.

Sources:
- LBNL *Land-Based Wind Market Report 2023* — US specific power 233 W/m², hub 103 m,
  trend since 1998. https://www.energy.gov/sites/default/files/2023-08/land-based-wind-market-report-2023-edition.pdf
- IEC 61400-1 turbine classes. https://en.wikipedia.org/wiki/IEC_61400
- NREL ATB 2024 Land-Based Wind (wind speed classes / techno-resource groups).
  https://atb.nrel.gov/electricity/2024/land-based_wind

| Local mean wind @100 m | IEC class | Representative turbine (atlite) | hub | rated wind | character |
|---|---|---|---|---|---|
| < 7.5 m/s | **III** | NREL 2020 ATB 4 MW | 110 m | 9.8 m/s | modern low specific power (~233 W/m²) |
| 7.5–9.0 m/s | **II** | Enercon E101 3 MW | 99 m | 13 m/s | medium |
| ≥ 9.0 m/s | **I** | Vestas V90 3 MW | 80 m | 15 m/s | robust, high specific power |

Effect: very windy cells (Patagonia, exposed coasts) switch from the low-SP
machine to a Class I machine → their CF drops to realistic values; low/medium
sites keep modern low-SP machines. The **CAPEX must follow the class** (Class I
cheaper $/MW, Class III pricier large rotor) to stay self-consistent — to be
wired into params.py if the class-matched CF is adopted in LCOS.

Regional note: new build in low-wind markets (India, much of US interior,
inland Australia) is dominated by Class III low-SP machines → our Class III pick
is representative there. ninja's default Vestas V90-2MW @80 m is a 2000s-era
high-SP machine and understates a *modern* build.

## 2. Solar PV — fixed-tilt vs single-axis tracking

Module tech is globally homogeneous (c-Si ≈ 95 %+), so the regional lever is
**tracking**, not cell type. Single-axis trackers now dominate new utility PV in
sunny markets and add 12–28 % yield:
- US utility-scale 2023: **96 % of new capacity used trackers**.
- Heavy tracker markets: US, Spain, Middle East, India, Australia, Chile.
- Tracking gain: 12–25 % at high irradiance (22–28 % S. Europe/N. Africa).

Sources:
- GMInsights / market.us single-axis tracker market (US 96 % 2023, >30 % global).
  https://www.gminsights.com/industry-analysis/utility-single-axis-solar-tracker-market
- NREL ATB Utility-Scale PV (CF ranges, tracking). https://atb.nrel.gov/electricity/2024/utility-scale_pv

Rule used: single-axis horizontal tracking where the fixed-tilt resource is good
(fixed CF ≥ 0.17 — captures deserts/subtropics: US SW, MENA, Australia, India,
Chile, S. Africa, China west, S. Europe); fixed-tilt elsewhere (cloudier / high
latitude). This raises PV CF in exactly the regions that deploy trackers and
leaves the conservative fixed-tilt baseline where trackers are uncommon.

### Real-deployment correction (country-based, 35_regional_corrected_cf.py)

The pure resource threshold mis-classified some real tracker markets (e.g.
monsoon cloudiness pushed India's fixed CF below 0.17). We therefore override the
PV mode by country using actual 2024 tracker-market data, with the resource rule
only as a fallback for unlisted countries:

- **Tracking** (real heavy markets): US, India, Saudi Arabia, Spain, Brazil,
  Australia, Mexico, Chile, MENA (UAE/Oman/Qatar/Egypt/Morocco/Algeria...),
  S. Africa, Turkey, Iran, Central Asia, Sahel. (US utility-scale 96 % trackers
  2023; India+Saudi > all Europe in 2024; top-5 US/India/Saudi/Spain/Brazil ≈
  70 % of the market.)
- **Fixed** (high-latitude / diffuse / humid-tropics): Germany, UK, N. Europe,
  Scandinavia, Russia, Canada, Japan, Korea, SE-Asia (Indonesia/Vietnam/...),
  France, Bangladesh.

Sources:
- Solar tracker 2024 regional shares (APAC 36 %, N.America 33 %, Europe 22 %,
  LatAm 6 %, MEA 3 %; top-5 markets). https://www.rinnovabili.net/business/markets/solar-trackers-record/
- Tracker outlook by market. https://www.pv-tech.org/global-solar-tracker-installations-to-reach-752gw-between-2024-and-2030/

Result (land cells): 1407 tracking / 1333 fixed. India correctly flips to
tracking (PV median 0.172 fixed → 0.204 tracking); Germany/Russia stay fixed.

Wind note: turbines ARE selected by site wind class in reality, so the IEC-class
assignment already reflects regional practice — e.g. low-wind Germany uses very
tall towers + low specific power (<300 W/m², hub 138 m), which is our Class III
machine; US 233 W/m² @103 m likewise. Renewables.ninja itself assigns
representative turbines + country bias-corrections (Staffell & Pfenninger 2016).
We therefore keep IEC-class wind; a regional hub-height refinement is a possible
next step. https://www.renewables.ninja/documentation/science

## 3. Offshore wind — only countries that actually have it

Onshore is computed everywhere on land. Offshore is added **only for the 19
countries with operational offshore wind at end-2024** (existing-technology
route, not all coastal countries): 13 in Europe (UK, Germany, Netherlands,
Denmark, Belgium, France, Sweden, Finland, Ireland, Norway, Portugal, Spain,
Italy), 5 in Asia (China, Taiwan, Japan, South Korea, Vietnam), 1 in North
America (USA). Source: GWEC — 83 GW global offshore by end-2024, 19 countries.
https://www.gwec.net/news/offshore-wind-installed-capacity-reaches-83-gw-as-new-report-finds-2024-a-record-year-for-construction-and-auctions

- **Turbine**: marinised NREL 2020 ATB **15 MW** offshore (rotor ~240 m, hub
  ~150 m) — a different machine class from onshore; gives ~2× the CF of onshore
  (coastal median ≈ 0.46 vs 0.27).
- **Assignment**: a coastal LAND cell (in one of the 19 countries) inherits the
  best offshore CF among its 8 near-shore neighbours (`coastal_offshore` cells).
- **Foundation = lowest-LCOS feasible route**: fixed-bottom (~3300 $/kW) is
  always cheaper than floating (~5500 $/kW) and is feasible on shallow shelves,
  so it is the route in all shallow-shelf markets; **floating** is used only
  where near-shore water is too deep — in practice **Norway & Portugal**
  (Hywind Tampen, WindFloat Atlantic). CAPEX incl. foundation + array + export
  cable; ≈ NREL ATB 2024 offshore. https://atb.nrel.gov/electricity/2024/offshore_wind

The offshore option is held as a **separate** layer (CF + foundation type +
CAPEX) — NOT blended into the onshore CF — so the cost-aware choice (onshore vs
fixed- vs floating-offshore) is made later in the LCOS, never as a naive CF max.
