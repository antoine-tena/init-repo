from datetime import date

import polars as pl

from pipeline.transforms import monthly_totals


def test_monthly_totals_sum_values_per_month_and_category() -> None:
    measurements = pl.DataFrame(
        {
            "date": [date(2025, 1, 3), date(2025, 1, 20), date(2025, 2, 1)],
            "category": ["nord", "nord", "nord"],
            "value": [1.0, 2.0, 5.0],
        }
    )

    totals = monthly_totals(measurements)

    assert totals["total"].to_list() == [3.0, 5.0]
    assert totals["month"].to_list() == [date(2025, 1, 1), date(2025, 2, 1)]
