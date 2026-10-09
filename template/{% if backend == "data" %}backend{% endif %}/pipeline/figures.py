"""Figures Plotly : une fonction par figure, qui reçoit des données déjà transformées."""

import plotly.graph_objects as go
import polars as pl

# Palette Okabe-Ito, lisible par les daltoniens ([FIGURES-ACCESSIBLES]).
COLORBLIND_PALETTE = ("#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00")


def monthly_totals_figure(totals: pl.DataFrame) -> go.Figure:
    """Courbes des totaux mensuels, une par catégorie, axes titrés avec leur unité."""
    figure = go.Figure()
    for index, category in enumerate(totals["category"].unique(maintain_order=True)):
        category_totals = totals.filter(pl.col("category") == category)
        figure.add_trace(
            go.Scatter(
                x=category_totals["month"].to_list(),
                y=category_totals["total"].to_list(),
                name=str(category),
                mode="lines+markers",
                line={"color": COLORBLIND_PALETTE[index % len(COLORBLIND_PALETTE)]},
            )
        )
    figure.update_layout(
        title="Totaux mensuels par catégorie",
        xaxis_title="Mois",
        yaxis_title="Total (unités)",
    )
    return figure
