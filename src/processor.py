import pandas as pd

from src.models import Country, MultiCountryPolicy, Policy, RATING_TO_PD, SingleCountryPolicy

# Mapping für dokumentierte Excel <-> Wikipedia-Namensunterschiede
NAME_MAPPING: dict[str, str] = {
    "Cape Verde":  "Cabo Verde",
    "Ivory Coast": "Côte d'Ivoire",
    "DR Congo":    "Democratic Republic of the Congo",
    "DRC":         "Democratic Republic of the Congo",
    "Congo":       "Republic of the Congo",
}

MOODYS_TO_SP: dict[str, str] = {
    "Aaa":  "AAA",
    "Aa1":  "AA+",  "Aa2":  "AA",    "Aa3":  "AA-",
    "A1":   "A+",   "A2":   "A",     "A3":   "A-",
    "Baa1": "BBB+", "Baa2": "BBB",   "Baa3": "BBB-",
    "Ba1":  "BB+",  "Ba2":  "BB",    "Ba3":  "BB-",
    "B1":   "B+",   "B2":   "B",     "B3":   "B-",
    "Caa1": "CCC+", "Caa2": "CCC",   "Caa3": "CCC-",
    "Ca":   "CC",
    "C":    "C",
}

DEFAULT_RATING: str = "B"


class DataProcessor:
    def __init__(
        self,
        excel_path: str,
        sp_ratings: dict[str, str],
        moodys_ratings: dict[str, str],
    ):
        self.excel_path = excel_path
        self.sp_ratings = sp_ratings
        self.moodys_ratings = moodys_ratings
        self.df_raw: pd.DataFrame | None = None
        self.policies: list[Policy] = []
        self.skipped: list[str] = []
        self.policy_sources: dict[str, str] = {}

    def _resolve_rating(self, country_name: str) -> tuple[str, str]:
        """Return (rating, source) for a country via S&P → Moody's → default fallback."""
        # 1. Try S&P
        if country_name in self.sp_ratings:
            rating = self.sp_ratings[country_name].replace("−", "-")
            if rating in RATING_TO_PD:
                return rating, "S&P"

        # 2. Try Moody's → convert to S&P notation
        if country_name in self.moodys_ratings:
            moodys = self.moodys_ratings[country_name].replace("−", "-")
            sp_equivalent = MOODYS_TO_SP.get(moodys)
            if sp_equivalent and sp_equivalent in RATING_TO_PD:
                return sp_equivalent, "Moody's"

        # 3. Default
        return DEFAULT_RATING, "default"

    def load_and_clean(self) -> pd.DataFrame:
        """Load Excel file, strip strings, parse dates. Saves result to self.df_raw."""
        df = pd.read_excel(self.excel_path)

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()

        for col in ["Effective Date", "Expiry Date"]:
            df[col] = pd.to_datetime(df[col])

        print(f"Loaded {len(df)} rows from {self.excel_path}")
        self.df_raw = df
        return df

    def build_policies(self, df: pd.DataFrame) -> list[Policy]:
        """Group rows by IOL#, build Policy objects. Saves result to self.policies."""
        policies: list[Policy] = []
        self.skipped = []
        self.policy_sources = {}

        for policy_id, group in df.groupby("IOL#"):
            exposures: list[tuple[Country, float]] = []
            country_sources: list[str] = []

            for _, row in group.iterrows():
                country_name = NAME_MAPPING.get(row["Risk Country"], row["Risk Country"])
                rating, source = self._resolve_rating(country_name)
                exposures.append((Country(country_name, rating), float(row["Exposure (USD)"])))
                country_sources.append(source)

            # Worst-link: default > Moody's > S&P
            if "default" in country_sources:
                policy_source = "default"
            elif "Moody's" in country_sources:
                policy_source = "Moody's"
            else:
                policy_source = "S&P"

            effective_date = group.iloc[0]["Effective Date"].date()
            expiry_date = group.iloc[0]["Expiry Date"].date()

            try:
                if len(exposures) == 1:
                    policy: Policy = SingleCountryPolicy(
                        policy_id=str(policy_id),
                        exposures=exposures,
                        effective_date=effective_date,
                        expiry_date=expiry_date,
                    )
                else:
                    policy = MultiCountryPolicy(
                        policy_id=str(policy_id),
                        exposures=exposures,
                        effective_date=effective_date,
                        expiry_date=expiry_date,
                    )
                policies.append(policy)
                self.policy_sources[str(policy_id)] = policy_source
            except ValueError as e:
                self.skipped.append(f"{policy_id}: {e}")

        self.policies = policies
        return policies

    def calculate_results(self, policies: list[Policy]) -> pd.DataFrame:
        """Build a results DataFrame from a list of policies, sorted by expected_loss."""
        rows = []
        for policy in policies:
            rows.append({
                "policy_id":     policy.policy_id,
                "type":          "single" if isinstance(policy, SingleCountryPolicy) else "multi",
                "n_countries":   len(policy.exposures),
                "max_lol":       policy.max_lol(),
                "tenor_years":   policy.duration_years,
                "pd":            policy.calculate_pd(),
                "expected_loss": policy.expected_loss(),
                "rating_source": self.policy_sources.get(policy.policy_id, "unknown"),
            })
        df = pd.DataFrame(rows)
        return df.sort_values("expected_loss", ascending=False).reset_index(drop=True)

    def export(self, results: pd.DataFrame, output_path: str) -> None:
        """Write results DataFrame to Excel."""
        results.to_excel(output_path, index=False)

    def run(self, output_path: str) -> pd.DataFrame:
        """Run the full pipeline: load → build → calculate → export."""
        df = self.load_and_clean()
        policies = self.build_policies(df)
        results = self.calculate_results(policies)
        self.export(results, output_path)

        n = len(policies)
        m = len(self.skipped)
        print(f"{n} Policies verarbeitet, {m} übersprungen")
        if m > 0:
            for reason in self.skipped[:5]:
                print(f"  - {reason}")

        return results
