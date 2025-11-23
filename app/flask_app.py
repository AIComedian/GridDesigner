import os
import sys
import threading
import subprocess
from flask import Flask, render_template, redirect, url_for, jsonify

def create_app():
    """
    Factory that returns a Flask app configured to launch the
    stickfigureanimation.py GUI as a separate process.
    """
    here = os.path.dirname(__file__)
    template_folder = os.path.join(here, "templates")
    app = Flask(__name__, template_folder=template_folder)

    # Absolute path to the stickfigureanimation script (one level up from app/)
    SCRIPT_PATH = os.path.abspath(os.path.join(here, "..", "stickfigureanimation.py"))

    # Process tracking stored on the app object
    app._launched_process = None
    app._launched_lock = threading.Lock()
    app.config.setdefault("SCRIPT_PATH", SCRIPT_PATH)

    @app.route("/")
    def intro():
        # Intro page gives a link to the animation GUI control page
        return render_template("intro.html")

    @app.route("/animationGUI")
    def animation_gui():
        # This is the browser control page for launching/monitoring the desktop Tk GUI
        return render_template("animationGUI.html")

    @app.route("/launch", methods=["POST"])
    def launch_gui():
        with app._launched_lock:
            # If already running, redirect to status
            if app._launched_process is not None and app._launched_process.poll() is None:
                return redirect(url_for("status"))

            script = app.config["SCRIPT_PATH"]
            if not os.path.exists(script):
                return "Error: stickfigureanimation.py not found in the repository.", 500

            try:
                # Use the same Python interpreter
                app._launched_process = subprocess.Popen([sys.executable, script], cwd=os.path.dirname(script))
            except Exception as e:
                app.logger.exception("Failed to launch GUI")
                return f"Failed to launch GUI: {e}", 500

        # Redirect to status (the animationGUI page also reads /status via JS)
        return redirect(url_for("status"))

    @app.route("/status")
    def status():
        with app._launched_lock:
            running = False
            pid = None
            if app._launched_process is not None:
                pid = app._launched_process.pid
                running = (app._launched_process.poll() is None)
        return jsonify({"running": running, "pid": pid})

    return app