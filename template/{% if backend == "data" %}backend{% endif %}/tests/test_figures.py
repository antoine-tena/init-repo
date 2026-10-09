from pipeline.figures import monthly_totals_figure
from pipeline.sources import load_measurements
from pipeline.transforms import monthly_totals


def test_figure_has_one_trace_per_category_and_titled_axes() -> None:
    totals = monthly_totals(load_measurements())

    figure = monthly_totals_figure(totals)

    assert len(figure.data) == totals["category"].n_unique()
    assert figure.layout.xaxis.title.text == "Mois"
    assert figure.layout.yaxis.title.text == "Total (unités)"
