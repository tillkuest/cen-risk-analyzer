import os

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import seaborn as sns

from src.models import MultiCountryPolicy, SingleCountryPolicy

sns.set_theme(style="whitegrid", palette="muted")

_FIGSIZE = (10, 6)
_PALETTE = sns.color_palette("muted", 2)
_TYPE_COLORS = {"single": _PALETTE[0], "multi": _PALETTE[1]}


def plot_top_exposures(results: pd.DataFrame, output_dir: str = "visuals", n: int = 10) -> None:
    """Bar chart of top n policies by expected loss, colored by type."""
    top = results.head(n).copy()
    top["el_m"] = top["expected_loss"] / 1e6

    fig, ax = plt.subplots(figsize=_FIGSIZE)

    bar_colors = [_TYPE_COLORS[t] for t in top["type"]]
    ax.bar(top["policy_id"], top["el_m"], color=bar_colors)

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


def plot_country_concentration(policies: list, output_dir: str = "visuals", n: int = 10) -> None:
    """Stacked horizontal bar chart of top n countries by expected loss contribution."""
    from collections import defaultdict
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


def plot_pd_distribution(results: pd.DataFrame, output_dir: str = "visuals") -> None:
    """Stacked bar chart of policy counts per PD bucket, split by type."""
    bins = [0, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    bin_labels = ["<0.5%", "0.5–1%", "1–5%", "5–10%", "10–50%", "≥50%"]

    temp = results[["pd", "type"]].copy()
    temp["bucket"] = pd.cut(temp["pd"], bins=bins, labels=bin_labels, include_lowest=True)
    counts = temp.groupby(["bucket", "type"], observed=True).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    counts.plot(kind="bar", stacked=True, ax=ax, rot=0,
                color=[_TYPE_COLORS[c] for c in counts.columns])

    ax.set_title("Portfolio PD Distribution")
    ax.set_ylabel("Number of Policies")
    ax.set_xlabel("")
    ax.legend(title="Type")

    plt.savefig(os.path.join(output_dir, "pd_distribution.png"), dpi=150, bbox_inches="tight")
    plt.close()


def plot_portfolio_composition(results: pd.DataFrame, output_dir: str = "visuals") -> None:
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


def generate_all(results: pd.DataFrame, policies: list, output_dir: str = "visuals") -> None:
    """Generate all four visualizations and save to output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    plot_top_exposures(results, output_dir)
    plot_country_concentration(policies, output_dir)
    plot_pd_distribution(results, output_dir)
    plot_portfolio_composition(results, output_dir)
    print(f"Generated 4 visualizations in {output_dir}/")
