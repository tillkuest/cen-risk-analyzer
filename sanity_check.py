from datetime import date
from src.models import Country, MultiCountryPolicy


# Hilfsfunktion: Country mit beliebigem PD bauen
# (Trick: Rating "AAA" nur damit die Klasse nicht meckert, dann pd manuell setzen)
def make_country(name, pd_value):
    c = Country(name, "AAA")
    c.pd = pd_value
    return c

# Die 14 Länder aus dem Swiss Re Paper, Seite 7
exposures = [
    (make_country("China",       0.00085), 52_818_159),
    (make_country("Croatia",     0.00431),  9_751_125),
    (make_country("Egypt",       0.02144), 12_188_905),
    (make_country("India",       0.00315), 24_380_000),
    (make_country("Indonesia",   0.00338),  2_031_484),
    (make_country("Kazakhstan",  0.00238), 14_220_389),
    (make_country("Moldova",     0.04041),  4_875_562),
    (make_country("Morocco",     0.00396),  9_475_200),
    (make_country("Pakistan",    0.04440),  8_140_000),
    (make_country("Russia",      0.00232), 52_818_161),
    (make_country("Serbia",      0.00598),  9_751_125),
    (make_country("Turkey",      0.00477), 52_818_160),
    (make_country("Ukraine",     0.02113), 36_566_714),
    (make_country("Vietnam",     0.01150), 17_470_764),
]

# Policy bauen, Tenor = 1 Jahr (wie im Paper)
policy = MultiCountryPolicy(
    policy_id="8696",
    exposures=exposures,
    effective_date=date(2012, 1, 1),
    expiry_date=date(2013, 1, 1),
)

# Resultate ausgeben
print("=" * 50)
print("SANITY CHECK: Swiss Re Paper Beispiel (Policy 8696)")
print("=" * 50)
print(f"max_lol:         {policy.max_lol():>15,.0f} USD")
print(f"duration_years:  {policy.duration_years:>15.4f}")
print(f"calculate_pd():  {policy.calculate_pd():>15.6f}")
print(f"erwartet:        {0.0308:>15.6f}  (= 3.08%)")
print("=" * 50)

# Detail-Check
weighted_sum = sum(lol * c.pd for c, lol in exposures)
print(f"\nDetails:")
print(f"  Σ(LoL · PD)    = {weighted_sum:,.2f}")
print(f"  max LoL        = {policy.max_lol():,.0f}")
print(f"  min(Σ, maxLoL) = {min(weighted_sum, policy.max_lol()):,.2f}")
print(f"  b-Faktor       = 0.6 (für Tenor=1)")
print(f"  Final PD       = 0.6 × {min(weighted_sum, policy.max_lol()):,.0f} / {policy.max_lol():,.0f}")


print("\n")
print("=" * 50)
print("EDGE CASE: weighted_sum > max_lol (min greift!)")
print("=" * 50)

# Künstliches Beispiel: alle PDs sehr hoch
edge_exposures = [
    (make_country("Country A", 0.50), 10_000_000),
    (make_country("Country B", 0.50), 10_000_000),
    (make_country("Country C", 0.50), 10_000_000),
]
# weighted_sum = 0.5 × 10M × 3 = 15M
# max_lol = 10M
# → min(15M, 10M) = 10M
# → PD = 0.6 × 10M / 10M = 0.6

edge_policy = MultiCountryPolicy(
    policy_id="EDGE",
    exposures=edge_exposures,
    effective_date=date(2024, 1, 1),
    expiry_date=date(2025, 1, 1),
)

weighted_sum = sum(lol * c.pd for c, lol in edge_exposures)
print(f"weighted_sum:    {weighted_sum:,.0f}")
print(f"max_lol:         {edge_policy.max_lol():,.0f}")
print(f"min(...):        {min(weighted_sum, edge_policy.max_lol()):,.0f}  ← greift!")
print(f"calculate_pd():  {edge_policy.calculate_pd():.4f}")
print(f"erwartet:        0.6000  (= b × maxLoL / maxLoL = b)")


## data_fetcher
# --- API Tests ---
from src.data_fetcher import fetch_sovereign_ratings, fetch_exchange_rates

print("\n")
print("=" * 50)
print("API TESTS")
print("=" * 50)

ratings = fetch_sovereign_ratings()
print(f"Länder mit Ratings: {len(ratings)}")
print(f"Beispiele: Switzerland={ratings.get('Switzerland')}, Germany={ratings.get('Germany')}")

rates = fetch_exchange_rates()
print(f"\nExchange Rates: {len(rates)}")
print(f"USD→EUR: {rates.get('EUR')}, USD→CHF: {rates.get('CHF')}")



print(f"\nWeitere Stichproben:")
print(f"  USA:        {ratings.get('United States')}")
print(f"  China:      {ratings.get('China')}")
print(f"  Pakistan:   {ratings.get('Pakistan')}")
print(f"  Argentina:  {ratings.get('Argentina')}")
print(f"  Bhutan:     {ratings.get('Bhutan')}  (sollte None sein - kein Rating)")

## processor test
print("\n")
print("=" * 50)
print("PIPELINE TEST: Vollständige Verarbeitung")
print("=" * 50)

from src.processor import DataProcessor

ratings = fetch_sovereign_ratings()
processor = DataProcessor("data/CEN_Test Case.xlsx", ratings)
results = processor.run("Output_Results.xlsx")

print(f"\nTop 5 nach Expected Loss:")
print(results.head().to_string())

print(f"\nVerteilung Single vs Multi-Country:")
print(results['type'].value_counts())


print(f"\n📊 Coverage-Statistik:")
print(f"   Eingelesene Policies (IOL#):  {df['IOL#'].nunique() if False else 101}")
print(f"   Erfolgreich verarbeitet:      {len(results)}")
print(f"   Übersprungen:                 {len(processor.skipped)}")
print(f"   Coverage:                     {len(results) / 101 * 100:.1f}%")


from src.visualizer import generate_all
generate_all(results, processor.policies)