from __future__ import annotations

from directory_storage_analyzer.app import create_dash_app
from directory_storage_analyzer.config import load_settings

settings = load_settings(debug=True)
app = create_dash_app(settings)


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
