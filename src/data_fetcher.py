import json
import re
import urllib.request

import pandas as pd


FALLBACK_RATINGS: dict[str, str] = {
    "United States": "AA+",
    "Germany":       "AAA",
    "United Kingdom":"AA",
    "France":        "AA-",
    "Japan":         "A+",
    "China":         "A+",
    "Brazil":        "BB-",
    "South Africa":  "BB-",
    "Kenya":         "B",
    "Ethiopia":      "B-",
}

FALLBACK_RATES: dict[str, float] = {
    "EUR": 0.92,
    "GBP": 0.79,
    "CHF": 0.89,
    "JPY": 149.50,
    "CNY": 7.24,
}


def fetch_sovereign_ratings() -> dict[str, str]:
    """Fetch sovereign S&P credit ratings from Wikipedia.

    Returns a dict mapping country name to S&P rating string, e.g. {'Kenya': 'B'}.
    Falls back to FALLBACK_RATINGS on any error.
    """
    try:
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-Agent", "Mozilla/5.0")]
        urllib.request.install_opener(opener)

        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_countries_by_credit_rating",
            match="Country/Territory",
        )
        df = tables[0]

        country_col = next(c for c in df.columns if "country" in c.lower())
        sp_col = next(c for c in df.columns if "rating" in c.lower())

        df = df[[country_col, sp_col]].dropna()

        result: dict[str, str] = {}
        for _, row in df.iterrows():
            country = str(row[country_col]).strip()
            raw_rating = str(row[sp_col])
            rating = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]", "", raw_rating).strip()
            if rating:
                result[country] = rating

        return result

    except Exception as e:
        print(f"Warning: Could not fetch sovereign ratings ({e}). Using fallback data.")
        return FALLBACK_RATINGS.copy()


def fetch_exchange_rates(base: str = "USD") -> dict[str, float]:
    """Fetch live exchange rates from open.er-api.com (no API key required).

    Returns a dict mapping currency code to rate relative to base, e.g. {'EUR': 0.92}.
    Falls back to FALLBACK_RATES on any error.
    """
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
        return data["rates"]

    except Exception as e:
        print(f"Warning: Could not fetch exchange rates ({e}). Using fallback data.")
        return FALLBACK_RATES.copy()
