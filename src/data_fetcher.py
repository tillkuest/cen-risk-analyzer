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

FALLBACK_MOODYS: dict[str, str] = {
    "United States": "Aaa",
    "Germany":       "Aaa",
    "United Kingdom":"Aa3",
    "France":        "Aa2",
    "Japan":         "A1",
    "China":         "A1",
    "Brazil":        "Ba1",
    "Argentina":     "Caa3",
    "Pakistan":      "Caa2",
    "South Africa":  "Ba2",
}

FALLBACK_RATES: dict[str, float] = {
    "EUR": 0.92,
    "GBP": 0.79,
    "CHF": 0.89,
    "JPY": 149.50,
    "CNY": 7.24,
}

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_credit_rating"


def set_browser_user_agent():
    """Install a Mozilla User-Agent globally so Wikipedia accepts our requests."""
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    urllib.request.install_opener(opener)


def fetch_sovereign_ratings() -> dict[str, str]:
    """Fetch sovereign S&P credit ratings from Wikipedia.

    Returns a dict mapping country name to S&P rating string, e.g. {'Germany': 'AAA'}.
    Falls back to FALLBACK_RATINGS on any error.
    """
    try:
        set_browser_user_agent()

        tables = pd.read_html(_WIKI_URL, match="Country/Territory")
        df = tables[0]

        country_col = next(c for c in df.columns if "country" in c.lower())
        sp_col = next(c for c in df.columns if "rating" in c.lower())

        df = df[[country_col, sp_col]].dropna()

        result = {}
        for _, row in df.iterrows(): # ignore index -> _ 
            country = str(row[country_col]).strip() 
            raw_rating = str(row[sp_col])
            rating = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]", "", raw_rating).strip() # wenn "AA [outlook: stable]" zu "AA"
            if rating: # ausführen, wenn rating = "A" z.B, aber nicht ausführen, wenn rating = ""!
                result[country] = rating

        return result

    except Exception as e:
        print(f"Warning: Could not fetch sovereign ratings ({e}). Using fallback data.")
        return FALLBACK_RATINGS.copy() # .copy() empfohlen, damit niemand die Dict mutiert


def fetch_moodys_ratings() -> dict[str, str]:
    """Fetch sovereign Moody's credit ratings from Wikipedia.

    Returns a dict mapping country name to Moody's rating string, e.g. {'Brazil': 'Ba1'}.
    Falls back to FALLBACK_MOODYS on any error.
    """
    try:
        set_browser_user_agent()

        tables = pd.read_html(_WIKI_URL, match="Country/Territory")
        df = tables[2]

        country_col = next(c for c in df.columns if "country" in c.lower())
        rating_col = next(c for c in df.columns if "rating" in c.lower())

        df = df[[country_col, rating_col]].dropna()

        result = {}
        for _, row in df.iterrows():
            country = str(row[country_col]).strip()
            raw_rating = str(row[rating_col])
            rating = re.sub(r"\s*[\[\(][^\]\)]*[\]\)]", "", raw_rating).strip()
            if rating:
                result[country] = rating

        return result

    except Exception as e:
        print(f"Warning: Could not fetch Moody's ratings ({e}). Using fallback data.")
        return FALLBACK_MOODYS.copy()


def fetch_exchange_rates(base = "USD") -> dict[str, float]:
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
