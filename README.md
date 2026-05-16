# CEN Risk Analyzer

A Python application that automates Probability of Default (PD) and Expected Loss calculations for Political Risk Insurance (CEN) policies, based on a smiplified Swiss Re's Political Risk Modelling Framework. The system reads policy data from Excel, fetches live sovereign credit ratings (S&P and Moody's) from Wikipedia and live exchange rates from ExchangeRate-API, processes the data through an Object-Oriented model, and produces an annotated Excel output plus four analytical visualizations.

This project was developed as a semester project. It demonstrates programming competencies in OOP, internet data access, robust API handling, Pandas-based data processing, visualization, and unit testing.

---

## Fulfillment of Course Requirements

| Criterion (V0X) | Implementation | Where to look |
|---|---|---|
| **OOP Design (V02–V04)** | Four classes with clear inheritance and polymorphism. `Country` encapsulates rating→PD logic. `Policy` is the base class with `max_lol()` and `expected_loss()` shared methods. `SingleCountryPolicy` and `MultiCountryPolicy` override `calculate_pd()` — single returns the country's PD, multi applies the Swiss-Re multi-country formula `b · min(Σ LoLᵢ·PDᵢ, maxLoL) / maxLoL`. | `src/models.py` |
| **Internet Data Access (V05)** | Two independent data sources: Wikipedia (HTML-scraped via `pandas.read_html()` with browser User-Agent header) for S&P and Moody's sovereign ratings, plus ExchangeRate-API (`urllib.request` + JSON) for live FX rates. | `src/data_fetcher.py` |
| **Robustness & Validation (V06)** | Every external call wrapped in `try/except` with hardcoded fallback data, 5-second timeout on the FX API, and Unicode-minus normalization (`−` → `-`) for rating strings. During development, the code survived three real failures: HTTP 403 from Wikipedia, missing `html5lib` dependency, and a Wikipedia table-structure change — each was caught by the robustness layer. | `src/data_fetcher.py`, `src/processor.py` |
| **Data Processing with Pandas (V07–V09)** | The `DataProcessor` class reads the Excel input, cleans strings (`.str.strip()`), parses dates to `datetime`, groups rows by `IOL#`, dispatches each group to the correct `Policy` subclass, and aggregates results into an output DataFrame sorted by Expected Loss. Four visualizations (matplotlib + seaborn) are auto-generated. | `src/processor.py`, `src/visualizer.py` |
| **Code Quality (V10–V13)** | Six unit tests covering `Country`, `SingleCountryPolicy`, `MultiCountryPolicy` (including the Swiss-Re paper example and the `min()`-clipping edge case), and date-validation in the `Policy` base. Type hints for help. Documented design decisions. | `tests/test_models.py` |

---

## Installation and Usage

**Requirements:** Python 3.10+.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the end-to-end pipeline

```bash
python main.py
```

This will:  

1. Fetch S&P and Moody's sovereign ratings from Wikipedia
2. Fetch live USD exchange rates from ExchangeRate-API (not used yet but I wanted to show a API fetch case and not only HTML (APIs for Ratings have costs))
3. Process `data/CEN_Test Case.xlsx` through the OOP model
4. Export `Output_Results.xlsx` with PD, Expected Loss, and rating source per policy
5. Generate eight visualizations in `visuals/`

### 3. Run the unit tests

```bash
python -m unittest tests.test_models -v
```

Expected output: 6 tests, all passing.

---

## Module Overview

| Module | Purpose |
|---|---|
| `main.py` | End-to-end demo script that runs the full pipeline. |
| `src/models.py` | OOP core: `Country`, `Policy` (base class), `SingleCountryPolicy`, `MultiCountryPolicy`. Contains `RATING_TO_PD` mapping. |
| `src/data_fetcher.py` | Stateless module with three functions: `fetch_sovereign_ratings()` (S&P), `fetch_moodys_ratings()`, and `fetch_exchange_rates()`. All have fallback dicts. |
| `src/processor.py` | `DataProcessor` class. Handles the Excel→DataFrame→Policy objects→output pipeline. Implements the S&P → Moody's → Default rating fallback chain. |
| `src/visualizer.py` | Generates four PNG charts: Top 10 Expected Loss, Country Concentration, PD Distribution, Portfolio Composition (single vs. multi). |
| `tests/test_models.py` | Six unit tests using built-in `unittest`. |
| `sanity_check.py` | Developer-only validation script: tests math against the Swiss-Re paper example, the min-clipping edge case, and API connectivity. Not part of the production pipeline. |

---

## Design Decisions and Simplifications

The model in `Political_Risk_Modelling_Framework_FINAL.pdf` (my company does not want me to share this...) describes a full Swiss-Re internal pricing framework. This implementation makes several deliberate simplifications (because of missing data and sensitive data from my company, that I cannot share), documented here for transparency:

1. **PDs derived from S&P ratings only, not iPDs.** The paper specifies for example iPDs = 33% SiEDF + 33% S&P + 33% Moody's. iPDs and SiEDF is not available in this project, so I approximate by mapping S&P ratings to PD values directly (`RATING_TO_PD` in `models.py`).

2. **Default UGD (Usage Given Default) / LGD (Loss Given Default) / PHR (Policy Holder Retention) values are used for all policies.** The paper's CEN defaults (UGD=0.5, LGD=0.3, PHR=0.1) are calibrated values. Underwriter could override those values but they are done mostly in the next tool that they use.

3. **Missing ratings are filled by a deterministic fallback chain.** Instead of UW judgment for unrated countries, the code tries S&P, then Moody's (with notation conversion via `MOODYS_TO_SP`), then defaults to `"B"`. The actual rating source per policy is tracked and exposed in the output (`rating_source` column).

4. **The `b`-scaling factor for the multi-country formula is looked up at `round(tenor)`.** The paper defines `b` at tenors {1, 2, 3} years; out-of-range tenors are clipped to the nearest defined value.

5. **Political Violence loading and the Sovereign correlation model are not implemented.** Both are mentioned in the paper but would require additional calibration and a Monte-Carlo simulation engine, maybe in the next project :)

These simplifications keep the implementation focused on the core competencies the course measures, while preserving the conceptual structure of the Swiss-Re framework.

---

## Output

After running `python main.py`, the following artifacts are produced:

**`Output_Results.xlsx`** — one row per policy with: `policy_id`, `type` (single/multi), `n_countries`, `max_lol`, `tenor_years`, `pd`, `expected_loss`, `rating_source`. Sorted descending by Expected Loss.

**`visuals/` directory — eight PNG charts:**

| File | Question it answers |
|---|---|
| `top_exposures.png` | Which 10 individual policies carry the largest Expected Loss? |
| `country_concentration.png` | Which 10 countries contribute the most Expected Loss (aggregated across all policies, multi-country contribution split proportionally by LoL share)? |
| `country_exposure.png` | Which 10 countries have the largest nominal exposure (sum of Limits of Liability)? |
| `pd_distribution.png` | How are policies distributed across PD buckets (<0.5%, 0.5–1%, …, ≥50%)? |
| `rating_distribution.png` | How many policies sit in each rating bucket (worst rating in multi-country groups)? |
| `rating_by_exposure.png` | How much total exposure sits in each rating bucket — i.e. is the nominal volume concentrated in investment-grade or speculative-grade countries? |
| `portfolio_composition.png` | What is the split between single-country and multi-country policies, by count and by Expected Loss? |
| `exposure_vs_tenor.png` | How does nominal exposure relate to tenor? (Log-scale Y, point size = Expected Loss.) |

Typical run statistics:
- 319 policies processed, 0 skipped (100% coverage)
- Rating sources approximately: ~85% S&P, ~5% Moody's, ~10% Default fallback
