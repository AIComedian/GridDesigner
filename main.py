from flask import Flask, render_template_string, redirect, url_for, jsonify
import os
import sys
import subprocess
import threading
import time

app = Flask(__name__)

# Path to the stickfigureanimation script in this repo
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "stickfigureanimation.py")

# Keep track of the subprocess so we don't launch multiple GUIs
_launched_process = None
_launched_lock = threading.Lock()

INDEX_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>GridDesigner - GUI Launcher</title>
  </head>
  <body>
    <h1>GridDesigner</h1>
    <p>This small local web server lets you launch the Stick Figure Animation GUI (Tkinter) provided by stickfigureanimation.py.</p>
    <p>Click the button below to open the GUI as a separate application window.</p>
    <form action="/launch" method="post">
      <button type="submit">Open GUI</button>
    </form>
    <p><a href="/status">View launch status</a></p>
  </body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


@app.route("/launch", methods=["POST"])
def launch_gui():
    """Launch the stickfigureanimation.py in a separate process. Returns a redirect back to the index."""
    global _launched_process
    with _launched_lock:
        # If a process was launched and still running, inform the user
        if _launched_process is not None and _launched_process.poll() is None:
            return redirect(url_for('status'))

        # Ensure the script exists
        if not os.path.exists(SCRIPT_PATH):
            return "Error: stickfigureanimation.py not found in the repository.", 500

        # Launch a new process to run the GUI script.
        # Use the same Python interpreter that's running this Flask app.
        try:
            _launched_process = subprocess.Popen([sys.executable, SCRIPT_PATH], cwd=os.path.dirname(__file__))
        except Exception as e:
            return f"Failed to launch GUI: {e}", 500

    # Redirect back to index or status page
    return redirect(url_for('status'))


@app.route("/status")
def status():
    """Return a simple JSON status about whether the GUI process is running."""
    global _launched_process
    with _launched_lock:
        running = False
        pid = None
        if _launched_process is not None:
            pid = _launched_process.pid
            running = (_launched_process.poll() is None)
    return jsonify({"running": running, "pid": pid})


if __name__ == "__main__":
    # Try to open the user's browser to the index page on start.
    try:
        import webbrowser
        threading.Timer(0.5, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    except Exception:
        pass

    # Run the Flask development server locally.
    app.run(host='127.0.0.1', port=5000, debug=True)
