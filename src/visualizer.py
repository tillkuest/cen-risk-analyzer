import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import seaborn as sns

from src.models import MultiCountryPolicy, SingleCountryPolicy
from collections import Counter
from collections import defaultdict


sns.set_theme(style="whitegrid", palette="muted")

_FIGSIZE = (10, 6)
_PALETTE = sns.color_palette("muted", 2)
_TYPE_COLORS = {"single": _PALETTE[0], "multi": _PALETTE[1]}


def plot_top_exposures(results: pd.DataFrame, output_dir = "visuals", n = 10): # n = 10 -> top10
    """Bar chart of top n policies by expected loss, colored by type."""
    top = results.head(n).copy()
    top["el_m"] = top["expected_loss"] / 1e6

    fig, ax = plt.subplots(figsize=_FIGSIZE)

    bar_colors = [_TYPE_COLORS[t] for t in top["type"]]
    ax.bar(top["policy_id"], top["el_m"], color=bar_colors)
    ax.set_ylim(0, top["el_m"].max() * 1.15)

    for _, row in top.iterrows():
        ax.text(row["policy_id"], row["el_m"], f"${row['el_m']:.1f}M",
                ha="center", va="bottom", fontsize=8)

    handles = [mpatches.Patch(color=_TYPE_COLORS[t], label=t) for t in _TYPE_COLORS]
    ax.legend(handles=handles, title="Type")
    ax.set_title(f"Top {n} Policies by Expected Loss")
    ax.set_ylabel("Expected Loss (Million USD)")
    ax.tick_params(axis="x", rotation=45)

    plt.savefig(os.path.join(output_dir, "top_exposures.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_country_concentration(policies: list, output_dir = "visuals", n = 10):
    """Stacked horizontal bar chart of top n countries by expected loss contribution."""
    single_contrib: dict[str, float] = defaultdict(float)
    multi_contrib: dict[str, float] = defaultdict(float)

    for policy in policies:
        el = policy.expected_loss()
        if isinstance(policy, SingleCountryPolicy):
            name = policy.exposures[0][0].name
            single_contrib[name] += el
        else:
            total_lol = sum(lol for _, lol in policy.exposures)
            for country, lol in policy.exposures:
                share = lol / total_lol
                multi_contrib[country.name] += el * share

    all_names = set(single_contrib) | set(multi_contrib)
    rows = [
        {
            "country": c,
            "single":  single_contrib[c] / 1e6,
            "multi":   multi_contrib[c] / 1e6,
            "total":   (single_contrib[c] + multi_contrib[c]) / 1e6,
        }
        for c in all_names
    ]
    df_c = (
        pd.DataFrame(rows)
        .sort_values("total", ascending=True)
        .tail(n)
    )

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.barh(df_c["country"], df_c["single"], color=_TYPE_COLORS["single"], label="single")
    ax.barh(df_c["country"], df_c["multi"],  color=_TYPE_COLORS["multi"],  label="multi",
            left=df_c["single"])

    ax.set_title(f"Top {n} Countries by Expected Loss Concentration")
    ax.set_xlabel("Expected Loss (Million USD)")
    ax.legend(title="Type")

    plt.savefig(os.path.join(output_dir, "country_concentration.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_pd_distribution(results: pd.DataFrame, output_dir = "visuals"):
    """Stacked bar chart of policy counts per PD bucket, split by type."""
    bins = [0, 0.005, 0.01, 0.05, 0.1, 0.499999, 1.0]
    bin_labels = ["<0.5%", "0.5–1%", "1–5%", "5–10%", "10–50%", "≥50%"]

    temp = results[["pd", "type"]].copy()
    temp["bucket"] = pd.cut(temp["pd"], bins=bins, labels=bin_labels, include_lowest=True)
    counts = temp.groupby(["bucket", "type"], observed=True).size().unstack(fill_value=0)
    counts = counts[[c for c in ["single", "multi"] if c in counts.columns]]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    counts.plot(kind="bar", stacked=True, ax=ax, rot=0,
                color=[_TYPE_COLORS[c] for c in counts.columns])

    ax.set_title("Portfolio PD Distribution")
    ax.set_ylabel("Number of Policies")
    ax.set_xlabel("")
    ax.legend(title="Type")

    plt.savefig(os.path.join(output_dir, "pd_distribution.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_portfolio_composition(results: pd.DataFrame, output_dir = "visuals"):
    """Two pie charts: policy count and expected loss, split by single vs multi."""
    counts = results["type"].value_counts()
    el_by_type = results.groupby("type")["expected_loss"].sum()
    pie_colors = [_TYPE_COLORS[t] for t in counts.index]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=_FIGSIZE)

    ax1.pie(counts, labels=counts.index, autopct="%1.1f%%", colors=pie_colors)
    ax1.set_title("By Policy Count")

    ax2.pie(el_by_type, labels=el_by_type.index, autopct="%1.1f%%",
            colors=[_TYPE_COLORS[t] for t in el_by_type.index])
    ax2.set_title("By Expected Loss")

    fig.suptitle("Portfolio Composition: Single vs Multi-Country")

    plt.savefig(os.path.join(output_dir, "portfolio_composition.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_country_exposure(policies: list, output_dir = "visuals", n = 10):
    """Stacked horizontal bar chart of top n countries by total nominal LoL."""
    single_lol: dict[str, float] = defaultdict(float)
    multi_lol: dict[str, float] = defaultdict(float)

    for policy in policies:
        if isinstance(policy, SingleCountryPolicy):
            name = policy.exposures[0][0].name
            single_lol[name] += policy.exposures[0][1]
        else:
            for country, lol in policy.exposures:
                multi_lol[country.name] += lol

    all_names = set(single_lol) | set(multi_lol)
    rows = [
        {
            "country": c,
            "single":  single_lol[c] / 1e6,
            "multi":   multi_lol[c] / 1e6,
            "total":   (single_lol[c] + multi_lol[c]) / 1e6,
        }
        for c in all_names
    ]
    df_c = (
        pd.DataFrame(rows)
        .sort_values("total", ascending=True)
        .tail(n)
    )

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.barh(df_c["country"], df_c["single"], color=_TYPE_COLORS["single"], label="single")
    ax.barh(df_c["country"], df_c["multi"],  color=_TYPE_COLORS["multi"],  label="multi",
            left=df_c["single"])

    ax.set_title(f"Top {n} Countries by Total Exposure (Nominal LoL)")
    ax.set_xlabel("Total Exposure (Million USD)")
    ax.legend(title="Type")

    plt.savefig(os.path.join(output_dir, "country_exposure.png"), dpi=150, bbox_inches="tight")
    plt.close()


_RATING_ORDER = [
    "AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
    "BBB+", "BBB", "BBB-",
    "BB+", "BB", "BB-",
    "B+", "B", "B-",
    "CCC+", "CCC", "CCC-", "CC",
    "C", "D", "SD",
]

_RATING_COLORS = {
    "AAA": "#4CAF50", "AA+": "#4CAF50", "AA": "#4CAF50", "AA-": "#4CAF50",
    "A+":  "#4CAF50", "A":   "#4CAF50", "A-": "#4CAF50",
    "BBB+":"#4CAF50", "BBB": "#4CAF50", "BBB-":"#4CAF50",
    "BB+": "#FFC107", "BB":  "#FFC107", "BB-": "#FFC107",
    "B+":  "#FF9800", "B":   "#FF9800", "B-":  "#FF9800",
    "CCC+":"#F44336", "CCC": "#F44336", "CCC-":"#F44336", "CC": "#F44336",
    "C":   "#B71C1C", "D":   "#B71C1C", "SD":  "#B71C1C",
}

_RATING_LEGEND = [
    mpatches.Patch(color="#4CAF50", label="Investment Grade (AAA–BBB-)"),
    mpatches.Patch(color="#FFC107", label="Crossover (BB+–BB-)"),
    mpatches.Patch(color="#FF9800", label="Speculative (B+–B-)"),
    mpatches.Patch(color="#F44336", label="Distressed (CCC+–CC)"),
    mpatches.Patch(color="#B71C1C", label="Default (C, D, SD)"),
]


def _get_policy_rating(policy) -> str:
    """Return the representative rating for a policy: single country's rating, or worst for multi."""
    if isinstance(policy, SingleCountryPolicy):
        return policy.exposures[0][0].rating
    worst_pd = max(country.pd for country, _ in policy.exposures)
    return next(country.rating for country, _ in policy.exposures if country.pd == worst_pd)


def plot_rating_distribution(policies: list, output_dir = "visuals"):
    """Bar chart of policy count per rating bucket, worst rating for multi-country."""
    rating_counts: Counter = Counter()

    for policy in policies:
        rating_counts[_get_policy_rating(policy)] += 1

    present = [r for r in _RATING_ORDER if r in rating_counts]
    counts  = [rating_counts[r] for r in present]
    colors  = [_RATING_COLORS[r] for r in present]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(present, counts, color=colors)

    ax.set_title("Portfolio Rating Distribution (Multi-Country: worst rating in group)")
    ax.set_ylabel("Number of Policies")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(handles=_RATING_LEGEND, fontsize=8)

    plt.savefig(os.path.join(output_dir, "rating_distribution.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_rating_by_exposure(policies: list, output_dir = "visuals"):
    """Bar chart of total max_lol per rating bucket, worst rating for multi-country."""
    lol_by_rating: dict[str, float] = defaultdict(float)

    for policy in policies:
        lol_by_rating[_get_policy_rating(policy)] += policy.max_lol()

    present = [r for r in _RATING_ORDER if r in lol_by_rating]
    values  = [lol_by_rating[r] / 1e6 for r in present]
    colors  = [_RATING_COLORS[r] for r in present]

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(present, values, color=colors)

    ax.set_title("Portfolio Rating-Bucket by Total Exposure (Multi-Country: worst rating in group)")
    ax.set_ylabel("Total Max Limit of Liability (Million USD)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(handles=_RATING_LEGEND, fontsize=8)

    plt.savefig(os.path.join(output_dir, "rating_by_exposure.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_exposure_vs_tenor(results: pd.DataFrame, output_dir = "visuals"):
    """Scatter plot of max_lol vs tenor_years, log y-scale, point size = expected_loss."""
    fig, ax = plt.subplots(figsize=_FIGSIZE)

    max_el = results["expected_loss"].max()

    for type_val, color in _TYPE_COLORS.items():
        subset = results[results["type"] == type_val]
        sizes = subset["expected_loss"] / max_el * 500 + 30
        ax.scatter(subset["tenor_years"], subset["max_lol"],
                   color=color, s=sizes, alpha=0.6, label=type_val)

    ax.set_yscale("log")
    ax.set_title("Exposure vs. Tenor — Point Size = Expected Loss")
    ax.set_xlabel("Tenor (years)")
    ax.set_ylabel("Max Limit of Liability (USD, log scale)")

    handles = [mpatches.Patch(color=_TYPE_COLORS[t], label=t) for t in _TYPE_COLORS]
    ax.legend(handles=handles, title="Type")

    plt.savefig(os.path.join(output_dir, "exposure_vs_tenor.png"), dpi=150, bbox_inches="tight")
    plt.close()


def generate_all(results: pd.DataFrame, policies: list, output_dir = "visuals"):
    """Generate all eight visualizations and save to output_dir."""
    os.makedirs(output_dir, exist_ok=True) # macht den visuals Folder, wenn schon exisitiert, kein error -> exist_ok=True
    plot_top_exposures(results, output_dir)
    plot_country_concentration(policies, output_dir)
    plot_pd_distribution(results, output_dir)
    plot_portfolio_composition(results, output_dir)
    plot_country_exposure(policies, output_dir)
    plot_rating_distribution(policies, output_dir)
    plot_rating_by_exposure(policies, output_dir)
    plot_exposure_vs_tenor(results, output_dir)
    print(f"Generated 8 visualizations in {output_dir}/")
