"""CEN Risk Analyzer – End-to-End-Pipeline.

Lädt Excel, holt Live-Ratings, berechnet Expected Loss, exportiert Excel und Charts.
"""

from src.data_fetcher import fetch_moodys_ratings, fetch_sovereign_ratings
from src.processor import DataProcessor
from src.visualizer import generate_all


def main() -> None:
    print("🔍 Fetching ratings from Wikipedia...")
    sp_ratings = fetch_sovereign_ratings()
    moodys_ratings = fetch_moodys_ratings()
    print(f" S&P: {len(sp_ratings)} countries, Moodys: {len(moodys_ratings)} countries")

    print("\n⚙️  Running pipeline...")
    processor = DataProcessor("data/CEN_Test Case.xlsx", sp_ratings, moodys_ratings)
    results = processor.run("Output_Results.xlsx")

    print("\n🎨 Generating visualizations...")
    generate_all(results, processor.policies)

    print("\n✅ Done. See Output_Results.xlsx and visuals/ folder.")


if __name__ == "__main__":
    main()
