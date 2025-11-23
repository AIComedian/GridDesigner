"""
Web-backed Animation GUI utilities.

This module provides:
- an AnimationGUI class that inherits from StickFigureAnimation (from stickfigureanimation.py)
  and exposes higher-level operations useful for a browser-based GUI (add frame from a
  template, move a selected region within a frame, list frames/templates, save/load/export).
- a Flask Blueprint (animation_gui_api) which exposes a small JSON API under the
  /animationGUI/api/ prefix so the frontend (animationGUI.html) can drive the animation
  editor embedded in the browser.

Notes:
- This is intentionally a light-weight backend that manipulates the same "frame" JSON
  structures used by stickfigureanimation.py (frames are dicts with 'boxes', 'grid_width',
  'grid_height', 'default_color', etc).
- "Objects" in a frame are represented here as rectangular selections of filled boxes.
  The API supports moving a selection by a (dr,dc) offset. (This is a practical, generic
  approach that works with the existing frame JSON format.)
- Template JSON files are expected to be in the repository's top-level frame_templates/ directory.
"""

import os
import json
from copy import deepcopy
from flask import Blueprint, request, jsonify, current_app
from typing import List, Dict, Tuple, Optional

# Import the base class from the top-level stickfigureanimation module
try:
    # If running as package (app/...), go up one level
    from stickfigureanimation import StickFigureAnimation
except Exception:
    # Fallback - try relative import (in case packaging differs)
    from ..stickfigureanimation import StickFigureAnimation  # type: ignore

# Blueprint prefix: /animationGUI/api
animation_gui_api = Blueprint("animation_gui_api", __name__, url_prefix="/animationGUI/api")


def _repo_root() -> str:
    """Return the repository root directory (two levels up from this file)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _frame_templates_dir() -> str:
    """Path to the frame_templates directory at repo root."""
    return os.path.join(_repo_root(), "frame_templates")


class AnimationGUI(StickFigureAnimation):
    """
    Backend model for a browser-based animation editor.

    Inherits from StickFigureAnimation so it has the same frame storage and
    export/load/save functionality. Adds convenience methods for a web UI.
    """

    def __init__(self):
        super().__init__()  # initialize frames, timings, etc.

    # --- Template utilities ------------------------------------------------

    def list_templates(self) -> List[str]:
        """Return list of available JSON template filenames in frame_templates/."""
        tpl_dir = _frame_templates_dir()
        filenames = []
        if os.path.isdir(tpl_dir):
            for name in sorted(os.listdir(tpl_dir)):
                if name.lower().endswith(".json"):
                    filenames.append(name)
        return filenames

    def get_template_path(self, filename: str) -> str:
        """Return the absolute path for a template filename under frame_templates/."""
        tpl_dir = _frame_templates_dir()
        return os.path.join(tpl_dir, filename)

    def load_template(self, filename: str) -> Optional[Dict]:
        """Load and return template JSON content or None if not found/invalid."""
        path = self.get_template_path(filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    # --- Frame management --------------------------------------------------

    def add_frame_from_template(self, template_name: str, duration: int = 200, background_json: Optional[str] = None) -> bool:
        """
        Add a new frame to the animation using a JSON template file name from frame_templates/.

        Returns True on success, False otherwise.
        """
        path = self.get_template_path(template_name)
        if not os.path.exists(path):
            return False
        try:
            super().add_frame_from_json(path, duration=duration, background_json=background_json)
            return True
        except Exception:
            return False

    def get_frames_summary(self) -> List[Dict]:
        """
        Return a lightweight summary of frames for the UI (index, name, duration).
        """
        summaries = []
        for i, frame in enumerate(self.frames):
            summaries.append({
                "index": i,
                "name": self.frame_names[i] if i < len(self.frame_names) else f"Frame_{i+1}.json",
                "duration": int(self.timings[i]) if i < len(self.timings) else 200,
                "grid_width": frame.get("grid_width"),
                "grid_height": frame.get("grid_height")
            })
        return summaries

    # --- Selection / object-like manipulation -----------------------------

    def _parse_key(self, key: str) -> Tuple[int, int]:
        r, c = key.split(",")
        return int(r), int(c)

    def _make_key(self, r: int, c: int) -> str:
        return f"{r},{c}"

    def move_selection(self, frame_index: int, sel_r0: int, sel_c0: int, sel_r1: int, sel_c1: int, dr: int, dc: int) -> bool:
        """
        Move all boxes inside the rectangular selection [r0..r1] x [c0..c1] by (dr,dc)
        within the same frame. Boxes that would move outside the frame bounds are skipped.

        Returns True on success (frame exists), False if frame_index invalid.
        """
        if frame_index < 0 or frame_index >= len(self.frames):
            return False

        frame = self.frames[frame_index]
        grid_w = frame.get("grid_width")
        grid_h = frame.get("grid_height")
        if grid_w is None or grid_h is None:
            return False

        boxes = frame.get("boxes", {})
        # Collect keys to move
        keys_to_move = []
        for key in list(boxes.keys()):
            r, c = self._parse_key(key)
            if sel_r0 <= r <= sel_r1 and sel_c0 <= c <= sel_c1:
                keys_to_move.append(key)

        # Determine destination keys and apply changes
        new_boxes = {}
        for key in keys_to_move:
            val = boxes.get(key)
            r, c = self._parse_key(key)
            nr = r + int(dr)
            nc = c + int(dc)
            # Skip if out of bounds
            if nr < 0 or nc < 0 or nr >= grid_h or nc >= grid_w:
                continue
            new_k = self._make_key(nr, nc)
            new_boxes[new_k] = val

        # Remove old keys then add new ones (avoid overwriting boxes outside selection)
        for key in keys_to_move:
            boxes.pop(key, None)
        boxes.update(new_boxes)

        # Update the frame's boxes
        frame['boxes'] = boxes
        # update stored frame
        self.frames[frame_index] = frame
        return True

    def translate_object(self, frame_index: int, object_coords: List[Tuple[int, int]], dr: int, dc: int) -> bool:
        """
        Move a specific set of coordinates (object_coords) by (dr,dc).
        object_coords is a list of (r,c) tuples that belong to the object.
        This gives the client control to treat an arbitrary selection as an 'object'.
        """
        if frame_index < 0 or frame_index >= len(self.frames):
            return False
        frame = self.frames[frame_index]
        grid_w = frame.get("grid_width")
        grid_h = frame.get("grid_height")
        if grid_w is None or grid_h is None:
            return False
        boxes = frame.get("boxes", {})

        # Remove original coords and compute new ones
        new_boxes = {}
        for (r, c) in object_coords:
            key = self._make_key(r, c)
            if key not in boxes:
                continue
            val = boxes.pop(key)
            nr = r + int(dr)
            nc = c + int(dc)
            if nr < 0 or nc < 0 or nr >= grid_h or nc >= grid_w:
                # skip out-of-bounds
                continue
            new_boxes[self._make_key(nr, nc)] = val

        boxes.update(new_boxes)
        frame['boxes'] = boxes
        self.frames[frame_index] = frame
        return True


# Singleton instance used by the blueprint routes.
_backend = AnimationGUI()


# --- Blueprint routes -----------------------------------------------------
# The frontend (animationGUI.html) can call these JSON endpoints to manipulate frames.

@animation_gui_api.route("/templates", methods=["GET"])
def api_list_templates():
    """Return list of available template filenames."""
    return jsonify({"templates": _backend.list_templates()})


@animation_gui_api.route("/frames", methods=["GET"])
def api_get_frames():
    """Return summaries and (optionally) full frame data via ?full=1 query param."""
    full = request.args.get("full", "0") == "1"
    summaries = _backend.get_frames_summary()
    if not full:
        return jsonify({"frames": summaries})
    # full payload
    frames_data = []
    for idx, frame in enumerate(_backend.frames):
        frames_data.append({
            "index": idx,
            "name": _backend.frame_names[idx] if idx < len(_backend.frame_names) else f"Frame_{idx+1}.json",
            "duration": int(_backend.timings[idx]) if idx < len(_backend.timings) else 200,
            "frame": frame,
            "background": _backend.backgrounds[idx] if idx < len(_backend.backgrounds) else None
        })
    return jsonify({"frames": frames_data})


@animation_gui_api.route("/add_frame", methods=["POST"])
def api_add_frame():
    """
    Add a frame from a template.
    JSON body: { "template": "name.json", "duration": 200, "background_template": "bg.json" (optional) }
    """
    data = request.get_json() or {}
    template = data.get("template")
    duration = int(data.get("duration", 200))
    bg_tpl = data.get("background_template", None)

    if not template:
        return jsonify({"ok": False, "error": "template required"}), 400

    bg_path = None
    if bg_tpl:
        # find full path if exists; pass as background_json file path to add_frame_from_json
        bg_full = _backend.get_template_path(bg_tpl)
        if os.path.exists(bg_full):
            bg_path = bg_full

    ok = _backend.add_frame_from_template(template, duration=duration, background_json=bg_path)
    if not ok:
        return jsonify({"ok": False, "error": "failed to add frame (template not found or invalid)"}), 400
    return jsonify({"ok": True, "frames": _backend.get_frames_summary()})


@animation_gui_api.route("/move_selection", methods=["POST"])
def api_move_selection():
    """
    Move a rectangular selection inside a frame.
    JSON body:
    {
      "frame_index": 0,
      "sel": {"r0": 2, "c0": 3, "r1": 4, "c1": 6},
      "dr": 1, "dc": -2
    }
    """
    data = request.get_json() or {}
    try:
        fi = int(data.get("frame_index", -1))
        sel = data.get("sel", {})
        r0 = int(sel.get("r0", 0))
        c0 = int(sel.get("c0", 0))
        r1 = int(sel.get("r1", 0))
        c1 = int(sel.get("c1", 0))
        dr = int(data.get("dr", 0))
        dc = int(data.get("dc", 0))
    except Exception:
        return jsonify({"ok": False, "error": "invalid parameters"}), 400

    ok = _backend.move_selection(fi, r0, c0, r1, c1, dr, dc)
    if not ok:
        return jsonify({"ok": False, "error": "invalid frame index or frame has no grid info"}), 400
    return jsonify({"ok": True})


@animation_gui_api.route("/translate_object", methods=["POST"])
def api_translate_object():
    """
    Move a set of explicit coordinates (an 'object') by dr,dc.
    JSON body:
    {
      "frame_index": 0,
      "coords": [[r1,c1],[r2,c2],...],
      "dr": 1,
      "dc": 0
    }
    """
    data = request.get_json() or {}
    try:
        fi = int(data.get("frame_index", -1))
        coords = data.get("coords", [])
        dr = int(data.get("dr", 0))
        dc = int(data.get("dc", 0))
        coords_t = [(int(r), int(c)) for [r, c] in coords]
    except Exception:
        return jsonify({"ok": False, "error": "invalid parameters"}), 400

    ok = _backend.translate_object(fi, coords_t, dr, dc)
    if not ok:
        return jsonify({"ok": False, "error": "invalid frame index or frame has no grid info"}), 400
    return jsonify({"ok": True})


@animation_gui_api.route("/save_animation", methods=["POST"])
def api_save_animation():
    """
    Save the current animation to a file.
    JSON body: { "filename": "myanim.json" }
    The file is written relative to the repository root (overwrites if exists).
    """
    data = request.get_json() or {}
    fname = data.get("filename")
    if not fname:
        return jsonify({"ok": False, "error": "filename required"}), 400
    repo = _repo_root()
    path = os.path.join(repo, fname)
    try:
        _backend.save_animation(path)
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@animation_gui_api.route("/load_animation", methods=["POST"])
def api_load_animation():
    """
    Load an animation file into the backend.
    JSON body: { "filename": "myanim.json" }
    Path is resolved relative to repository root.
    """
    data = request.get_json() or {}
    fname = data.get("filename")
    if not fname:
        return jsonify({"ok": False, "error": "filename required"}), 400
    repo = _repo_root()
    path = os.path.join(repo, fname)
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "file not found"}), 404
    try:
        _backend.load_animation(path)
        return jsonify({"ok": True, "frames": _backend.get_frames_summary()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@animation_gui_api.route("/export_video", methods=["POST"])
def api_export_video():
    """
    Export current animation to an mp4 file.
    JSON body: { "filename": "animation.mp4", "fps": 5 }
    """
    data = request.get_json() or {}
    fname = data.get("filename", "animation.mp4")
    fps = int(data.get("fps", 5))
    path = os.path.join(_repo_root(), fname)
    try:
        _backend.export_to_video(path, fps=fps)
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Utility function to register the blueprint on an existing Flask app
def register_blueprint(app):
    """
    Register the animation GUI API blueprint on the given Flask app.

    Example:
        from app.animationUtils import animationGUI
        animationGUI.register_blueprint(app)
    """
    app.register_blueprint(animation_gui_api)
    # Expose the backend instance on the Flask app for convenience in templates/tests
    app.animation_backend = _backend
    return animation_gui_api