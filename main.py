#!/usr/bin/env python3
"""
Entry point for GridDesigner.

This script creates the Flask app using the factory in app.flask_app.create_app,
tries to open the user's default browser to the intro page, and runs the
development server on 127.0.0.1:5000.

The actual desktop GUI (Tkinter) is still provided by stickfigureanimation.py and
is launched from the Flask app (app.flask_app.create_app) when requested.
"""
from app.flask_app import create_app

def main():
    app = create_app()

    # Try to open the browser shortly after startup for convenience.
    try:
        import webbrowser
        import threading
        threading.Timer(0.5, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    except Exception:
        # Best-effort only — failure to auto-open the browser is non-fatal.
        pass

    # Run the Flask development server locally.
    app.run(host="127.0.0.1", port=5000, debug=True)

if __name__ == "__main__":
    main()