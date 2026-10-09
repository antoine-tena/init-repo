"""Chargement des jeux de données, validés à la frontière ([VALIDATION-AUX-FRONTIERES])."""

from pathlib import Path

import polars as pl

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_MEASUREMENTS = DATA_DIR / "sample" / "measurements.csv"

MEASUREMENTS_SCHEMA = pl.Schema({"date": pl.Date, "category": pl.String, "value": pl.Float64})


class DatasetSchemaError(ValueError):
    """Colonnes ou types inattendus : le chargement échoue, pas la figure."""


def load_measurements(path: Path = SAMPLE_MEASUREMENTS) -> pl.DataFrame:
    """Mesures datées par catégorie ; colonnes et types vérifiés avant tout usage."""
    measurements = pl.read_csv(path, try_parse_dates=True)
    missing_columns = set(MEASUREMENTS_SCHEMA.names()) - set(measurements.columns)
    if missing_columns:
        raise DatasetSchemaError(
            f"colonnes manquantes dans {path.name} : {sorted(missing_columns)}"
        )
    try:
        return measurements.select(MEASUREMENTS_SCHEMA.names()).cast(MEASUREMENTS_SCHEMA)
    except pl.exceptions.InvalidOperationError as error:
        raise DatasetSchemaError(f"types inattendus dans {path.name}") from error
