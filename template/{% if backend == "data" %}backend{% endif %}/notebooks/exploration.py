import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from pipeline.figures import monthly_totals_figure
    from pipeline.sources import load_measurements
    from pipeline.transforms import monthly_totals

    return load_measurements, mo, monthly_totals, monthly_totals_figure


@app.cell
def _(load_measurements, monthly_totals):
    measurements = load_measurements()
    totals = monthly_totals(measurements)
    return (totals,)


@app.cell
def _(mo):
    mo.md("""
    # Exploration

    Le code qui produit une figure livrée vit dans `pipeline/` ([NOTEBOOKS]) : ce notebook
    l'importe et l'explore.
    """)
    return


@app.cell
def _(monthly_totals_figure, totals):
    monthly_totals_figure(totals)
    return


if __name__ == "__main__":
    app.run()
