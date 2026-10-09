"""Point d'entrée Dash : `uv run python app.py` (ou `kiln dev`)."""

from dashboard.layout import create_app

app = create_app()
# Serveur WSGI exposé pour la production (gunicorn app:server).
server = app.server

if __name__ == "__main__":
    app.run(debug=True)
