from datetime import date


RATING_TO_PD = {
    "AAA":  0.0001,
    "AA+":  0.0002,
    "AA":   0.0003,
    "AA-":  0.0005,
    "A+":   0.0007,
    "A":    0.0010,
    "A-":   0.0015,
    "BBB+": 0.0025,
    "BBB":  0.0040,
    "BBB-": 0.0060,
    "BB+":  0.0100,
    "BB":   0.0150,
    "BB-":  0.0220,
    "B+":   0.0350,
    "B":    0.0550,
    "B-":   0.0850,
    "CCC+": 0.1500,
    "CCC":  0.2200,
    "CCC-": 0.3000,
    "CC":   0.4500,
    "C":    0.4700,
    "D":    1.0000,
    "SD":   0.5000,  # Selective Default (S&P partial-default rating)
}

B_FACTOR = {1: 0.6, 2: 0.5, 3: 0.42}


class Country: # Country Objekt bauen
    def __init__(self, name, rating):
        if rating not in RATING_TO_PD:
            raise ValueError(f"Unknown rating '{rating}'. Valid ratings: {list(RATING_TO_PD)}") ## most likely never used (check resolve_rating() which checks rating or gives default), but here just in case
        self.name = name
        self.rating = rating
        self.pd = RATING_TO_PD[rating]

    def __repr__(self):
        return f"Country(name='{self.name}', rating='{self.rating}', pd={self.pd})"


class Policy:
    def __init__(self, policy_id: str, exposures: list[tuple[Country, float]], effective_date: date, expiry_date: date):
        if expiry_date <= effective_date:
            raise ValueError(f"expiry_date must be after effective_date (got {effective_date} → {expiry_date})")
        self.policy_id = policy_id
        self.exposures = exposures
        self.effective_date = effective_date
        self.expiry_date = expiry_date

    @property
    def duration_years(self):
        return (self.expiry_date - self.effective_date).days / 365.25 # wieso das property und die anderen nicht? hier mehr eine eigenschaft, die anderen sind mehr Methoden lastig

    def max_lol(self):
        return max(lol for _, lol in self.exposures)

    def calculate_pd(self):
        raise NotImplementedError("Subclasses must implement calculate_pd()") # Haben es in Subclasses, just in case, war früher da

    def expected_loss(self):
        return self.max_lol() * (1 - 0.1) * 0.5 * 0.3 * self.calculate_pd()


class SingleCountryPolicy(Policy):
    def calculate_pd(self):
        country, _ = self.exposures[0] # numm nur das Country-Objekt (Country(name='Hong Kong', rating='AA+', pd=0.0002), 79935892.61))
        return country.pd # country ist nur das (ohne LoL): Country(name='Cyprus', rating='A-', pd=0.0015) -- country.pd = 0.085 z.B. (von oben self.pd!)


class MultiCountryPolicy(Policy):
    def calculate_pd(self):
        tenor = min(max(round(self.duration_years), 1), 3) # runden, wenn über 3, nimm 3, sonst 1 oder 2
        b = B_FACTOR[tenor]
        weighted_sum = sum(lol * country.pd for country, lol in self.exposures)
        return b * min(weighted_sum, self.max_lol()) / self.max_lol()
