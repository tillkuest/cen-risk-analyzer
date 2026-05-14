# CEN Risk Analyzer

A Python application that automates Probability of Default (PD) and Expected Loss calculations for Political Risk Insurance (CEN) policies, based on Swiss Re's published Political Risk Modelling Framework. The system reads policy data from Excel, fetches live sovereign credit ratings (S&P and Moody's) from Wikipedia and live exchange rates from ExchangeRate-API, processes the data through an Object-Oriented model, and produces an annotated Excel output plus four analytical visualizations.

This project was developed as a semester project for INFPROG2 (FS26, ZHAW). It demonstrates programming competencies in OOP, internet data access, robust API handling, Pandas-based data processing, visualization, and unit testing.

---

## Fulfillment of Course Requirements

| Criterion (V0X) | Implementation | Where to look |
|---|---|---|
| **OOP Design (V02–V04)** | Four classes with clear inheritance and polymorphism. `Country` encapsulates rating→PD logic. `Policy` is the base class with `max_lol()` and `expected_loss()` shared methods. `SingleCountryPolicy` and `MultiCountryPolicy` override `calculate_pd()` — single returns the country's PD, multi applies the Swiss-Re multi-country formula `b · min(Σ LoLᵢ·PDᵢ, maxLoL) / maxLoL`. | `src/models.py` |
| **Internet Data Access (V05)** | Two independent data sources: Wikipedia (HTML-scraped via `pandas.read_html()` with browser User-Agent header) for S&P and Moody's sovereign ratings, plus ExchangeRate-API (`urllib.request` + JSON) for live FX rates. | `src/data_fetcher.py` |
| **Robustness & Validation (V06)** | Every external call wrapped in `try/except` with hardcoded fallback data, 5-second timeout on the FX API, and Unicode-minus normalization (`−` → `-`) for rating strings. During development, the code survived three real failures: HTTP 403 from Wikipedia, missing `html5lib` dependency, and a Wikipedia table-structure change — each was caught by the robustness layer. | `src/data_fetcher.py`, `src/processor.py` |
| **Data Processing with Pandas (V07–V09)** | The `DataProcessor` class reads the Excel input, cleans strings (`.str.strip()`), parses dates to `datetime`, groups rows by `IOL#`, dispatches each group to the correct `Policy` subclass, and aggregates results into an output DataFrame sorted by Expected Loss. Four visualizations (matplotlib + seaborn) are auto-generated. | `src/processor.py`, `src/visualizer.py` |
| **Code Quality (V10–V13)** | Six unit tests covering `Country`, `SingleCountryPolicy`, `MultiCountryPolicy` (including the Swiss-Re paper example and the `min()`-clipping edge case), and date-validation in the `Policy` base. Type hints throughout. Documented design decisions. | `tests/test_models.py` |

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
2. Fetch live USD exchange rates from ExchangeRate-API
3. Process `data/CEN_Test Case.xlsx` through the OOP model
4. Export `Output_Results.xlsx` with PD, Expected Loss, and rating source per policy
5. Generate four visualizations in `visuals/`

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

The model in `Political_Risk_Modelling_Framework_FINAL.pdf` describes a full Swiss-Re internal pricing framework. This implementation makes several deliberate simplifications, documented here for transparency:

1. **PDs derived from S&P ratings only, not iPDs.** The paper specifies iPDs = 33% SiEDF + 33% S&P + 33% Moody's. SiEDF data is proprietary and not publicly available, so I approximate by mapping S&P ratings to PD values directly (`RATING_TO_PD` in `models.py`).

2. **Only proportional reinsurance cover is modeled.** Non-proportional cover requires Underwriter judgment for peak-risk selection, which falls outside the automated scope.

3. **Tenor is computed as `(expiry_date − effective_date) / 365.25`.** The paper distinguishes an "economic tenor" with explicit amortization profiles (Appendix B). Without a UW providing these inputs, simple date difference is a consistent approximation.

4. **Default UGD / LGD / PHR values are used for all policies.** The paper's CEN defaults (UGD=0.5, LGD=0.3, PHR=0.1) are calibrated values. UW-level overrides would require domain expertise not reconstructible from the Excel input.

5. **Missing ratings are filled by a deterministic fallback chain.** Instead of UW judgment for unrated countries, the code tries S&P, then Moody's (with notation conversion via `MOODYS_TO_SP`), then defaults to `"B"`. The actual rating source per policy is tracked and exposed in the output (`rating_source` column).

6. **The `b`-scaling factor for the multi-country formula is looked up at `round(tenor)`.** The paper defines `b` only at tenors {1, 2, 3} years; out-of-range tenors are clipped to the nearest defined value.

7. **Political Violence loading (~3.5%) and the Sovereign GCorr correlation model are not implemented.** Both are mentioned in the paper but would require additional calibration and a Monte-Carlo simulation engine.

These simplifications keep the implementation focused on the core competencies the course measures, while preserving the conceptual structure of the Swiss-Re framework.

---

## Output

After running `python main.py`, the following artifacts are produced:

- **`Output_Results.xlsx`** – one row per policy with: `policy_id`, `type` (single/multi), `n_countries`, `max_lol`, `tenor_years`, `pd`, `expected_loss`, `rating_source`. Sorted descending by Expected Loss.
- **`visuals/top_exposures.png`** – Top 10 policies by Expected Loss.
- **`visuals/country_concentration.png`** – Top 10 countries by aggregated Expected Loss exposure.
- **`visuals/pd_distribution.png`** – Histogram of PDs across the portfolio.
- **`visuals/portfolio_composition.png`** – Single vs. Multi-country split, by count and by Expected Loss.

Typical run statistics (with the provided `CEN_Test Case.xlsx`):
- 101 policies processed, 0 skipped (100% coverage)
- ~77% via S&P ratings, ~5% via Moody's fallback, ~18% via default rating
