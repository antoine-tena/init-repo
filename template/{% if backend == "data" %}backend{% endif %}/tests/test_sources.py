from pathlib import Path

import polars as pl
import pytest

from pipeline.sources import MEASUREMENTS_SCHEMA, DatasetSchemaError, load_measurements


def test_sample_measurements_match_schema() -> None:
    measurements = load_measurements()

    assert measurements.schema == MEASUREMENTS_SCHEMA
    assert measurements.height > 0


def test_missing_column_fails_at_load(tmp_path: Path) -> None:
    incomplete_csv = tmp_path / "incomplete.csv"
    incomplete_csv.write_text("date,value\n2025-01-15,1.0\n")

    with pytest.raises(DatasetSchemaError, match="category"):
        load_measurements(incomplete_csv)


def test_wrong_type_fails_at_load(tmp_path: Path) -> None:
    wrong_type_csv = tmp_path / "wrong_type.csv"
    wrong_type_csv.write_text("date,category,value\n2025-01-15,nord,beaucoup\n")

    with pytest.raises(DatasetSchemaError):
        load_measurements(wrong_type_csv)


def test_loaded_columns_are_in_schema_order() -> None:
    assert load_measurements().columns == pl.Schema(MEASUREMENTS_SCHEMA).names()
