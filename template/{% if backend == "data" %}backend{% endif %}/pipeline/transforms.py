"""Transformations pures : un DataFrame en entrée, un DataFrame en sortie, aucun effet de bord."""

import polars as pl


def monthly_totals(measurements: pl.DataFrame) -> pl.DataFrame:
    """Total des valeurs par mois et par catégorie, trié par mois puis par catégorie."""
    return (
        measurements.with_columns(pl.col("date").dt.truncate("1mo").alias("month"))
        .group_by("month", "category")
        .agg(pl.col("value").sum().alias("total"))
        .sort("month", "category")
    )
