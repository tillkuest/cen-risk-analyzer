import unittest
from datetime import date

from src.models import (RATING_TO_PD, Country, MultiCountryPolicy, SingleCountryPolicy)


def make_country(name, pd) -> Country:
    """Create a Country with AAA rating, then override pd manually."""
    c = Country(name, "AAA")
    c.pd = pd
    return c


_DATE_START = date(2024, 1, 1)
_DATE_END_1Y = date(2025, 1, 1)   # ~1 year → round(0.999) = 1 → b = 0.6


class TestCountry(unittest.TestCase):

    def test_country_creation_valid_rating(self):
        """Country assigns correct pd from RATING_TO_PD for known ratings."""
        germany = Country("Germany", "AAA")
        self.assertEqual(germany.pd, 0.0001)

        pakistan = Country("Pakistan", "B-")
        self.assertEqual(pakistan.pd, 0.0850)

    def test_country_unknown_rating_raises(self):
        """Country raises ValueError for ratings not in RATING_TO_PD."""
        with self.assertRaises(ValueError):
            Country("Fantasialand", "XYZ")


class TestSingleCountryPolicy(unittest.TestCase):

    def test_single_country_pd_equals_country_pd(self):
        """calculate_pd() returns the pd of the single country unchanged."""
        germany = Country("Germany", "AAA")
        policy = SingleCountryPolicy(policy_id="TEST001", exposures=[(germany, 100_000_000)], effective_date=_DATE_START, expiry_date=_DATE_END_1Y)
        self.assertEqual(policy.calculate_pd(), germany.pd)


class TestMultiCountryPolicy(unittest.TestCase):

    def test_multi_country_paper_example(self):
        """Swiss-Re 14-country example: calculate_pd() lands in [0.025, 0.030]."""
        exposures = [
            (make_country("China",        0.00085), 100_000_000),
            (make_country("Croatia",      0.00431), 100_000_000),
            (make_country("Vietnam",      0.01150), 100_000_000),
            (make_country("Indonesia",    0.00200), 100_000_000),
            (make_country("Philippines",  0.00250), 100_000_000),
            (make_country("Brazil",       0.00300), 100_000_000),
            (make_country("Colombia",     0.00280), 100_000_000),
            (make_country("Peru",         0.00220), 100_000_000),
            (make_country("Mexico",       0.00240), 100_000_000),
            (make_country("India",        0.00270), 100_000_000),
            (make_country("Turkey",       0.00350), 100_000_000),
            (make_country("South Africa", 0.00300), 100_000_000),
            (make_country("Nigeria",      0.00330), 100_000_000),
            (make_country("Kenya",        0.00220), 100_000_000),
        ]
        policy = MultiCountryPolicy(policy_id="TEST002", exposures=exposures, effective_date=_DATE_START, expiry_date=_DATE_END_1Y)
        pd = policy.calculate_pd()
        self.assertGreaterEqual(pd, 0.025)
        self.assertLessEqual(pd, 0.030)

    def test_multi_country_min_clipping(self):
        """min() caps weighted_sum at max_lol when PDs are high; result = b = 0.6."""
        exposures = [
            (make_country("Alpha", 0.5), 10_000_000),
            (make_country("Beta", 0.5), 10_000_000),
            (make_country("Gamma", 0.5), 10_000_000),
        ]
        policy = MultiCountryPolicy(policy_id="TEST003", exposures=exposures, effective_date=_DATE_START, expiry_date=_DATE_END_1Y)
        # weighted_sum = 3 * 10M * 0.5 = 15M > max_lol = 10M → min clips to 10M
        # pd = 0.6 * 10M / 10M = 0.6
        self.assertAlmostEqual(policy.calculate_pd(), 0.6, places=10)


class TestPolicyBase(unittest.TestCase):

    def test_policy_invalid_dates_raises(self):
        """Policy raises ValueError when expiry_date is before effective_date."""
        germany = Country("Germany", "AAA")
        with self.assertRaises(ValueError):
            SingleCountryPolicy(policy_id="TEST004", exposures=[(germany, 100_000_000)], effective_date=date(2025, 1, 1), expiry_date=date(2024, 1, 1))


if __name__ == "__main__":
    unittest.main()
