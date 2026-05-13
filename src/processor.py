import pandas as pd

from src.models import Country, MultiCountryPolicy, Policy, RATING_TO_PD, SingleCountryPolicy

# Mapping für dokumentierte Excel↔Wikipedia-Namensunterschiede
NAME_MAPPING: dict[str, str] = {
    "Cape Verde":  "Cabo Verde",
    "Ivory Coast": "Côte d'Ivoire",
    "DR Congo":    "Democratic Republic of the Congo",
    "DRC":         "Democratic Republic of the Congo",
    "Congo":       "Republic of the Congo",
}


class DataProcessor:
    def __init__(self, excel_path: str, ratings: dict[str, str]):
        self.excel_path = excel_path
        self.ratings = ratings
        self.df_raw: pd.DataFrame | None = None
        self.policies: list[Policy] = []
        self.skipped: list[str] = []

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

        for policy_id, group in df.groupby("IOL#"):
            exposures: list[tuple[Country, float]] = []
            original_size = len(group)

            for _, row in group.iterrows():
                country_name = NAME_MAPPING.get(row["Risk Country"], row["Risk Country"])

                if country_name not in self.ratings:
                    self.skipped.append(f"{policy_id}: '{country_name}' not found in ratings")
                    continue

                rating = self.ratings[country_name].replace("−", "-")

                if rating not in RATING_TO_PD:
                    self.skipped.append(f"{policy_id}: rating '{rating}' for '{country_name}' not in RATING_TO_PD")
                    continue

                exposures.append((Country(country_name, rating), float(row["Exposure (USD)"])))

            if len(exposures) == 0:
                self.skipped.append(f"{policy_id}: all countries skipped, policy dropped")
                continue

            if len(exposures) == 1 and original_size > 1:
                self.skipped.append(f"{policy_id}: only 1 of {original_size} countries resolved, multi-country policy dropped")
                continue

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
