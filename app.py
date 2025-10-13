import ctypes
def is_file_locked(filepath):
    try:
        fh = open(filepath, 'a')
        fh.close()
        return False
    except Exception:
        return True

from flask import Flask, request, render_template_string, redirect, url_for
import chess
import chess.engine

app = Flask(__name__)

# Path to the Stockfish engine (will be auto-discovered at runtime)
engine_path = None

def _paths():
    import os
    root = os.path.dirname(__file__)
    return {
        'root': root,
        'bin': os.path.join(root, 'bin'),
        'selected': os.path.join(root, '.engine_selected'),
        'previous': os.path.join(root, '.engine_previous')
    }

def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def _write_text(path, text):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception:
        return False

def find_stockfish():
    """Attempt to locate a Stockfish executable.

    Order of checks:
    1. STOCKFISH_PATH environment variable
    2. 'stockfish' on PATH (shutil.which)
    3. Common Windows locations
    4. Project local 'bin/stockfish.exe'
    Returns the absolute path or None if not found.
    """
    import os
    import shutil

    # 1) environment override
    env = os.environ.get('STOCKFISH_PATH')
    if env and os.path.isfile(env):
        return env

    # 2) selection file (persisted choice)
    p = _paths()
    chosen = _read_text(p['selected'])
    if chosen and os.path.isfile(chosen):
        return chosen

    # 3) on PATH
    which = shutil.which('stockfish')
    if which:
        return which

    # 4) common install locations (32/64-bit Program Files, user directories)
    common = [
        r"C:\Program Files\Stockfish\stockfish.exe",
        r"C:\Program Files (x86)\Stockfish\stockfish.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Stockfish\stockfish.exe"),
        os.path.expanduser(r"~\stockfish\stockfish.exe"),
    ]
    for p in common:
        if p and os.path.isfile(p):
            return p

    # 5) project-local bin folder: accept any executable whose name contains
    # 'stockfish' so we will honor the real filename someone installed.
    proj_bin = os.path.join(os.path.dirname(__file__), 'bin')
    try:
        if os.path.isdir(proj_bin):
            for entry in os.listdir(proj_bin):
                if entry.lower().endswith('.exe') and 'stockfish' in entry.lower():
                    candidate = os.path.join(proj_bin, entry)
                    if os.path.isfile(candidate):
                        return candidate
    except Exception:
        # ignore permission/listing errors and continue
        pass

    return None

def install_stockfish_to_dir(target_dir: str):
    """Download latest Stockfish zip and extract the engine exe into target_dir.

    Preserves the original filename from the archive. Returns absolute path to
    the installed executable on success, else None.
    """
    import os
    try:
        import requests, zipfile, io, tempfile
    except ImportError:
        print("requests package not available; cannot auto-install Stockfish.")
        return None
    os.makedirs(target_dir, exist_ok=True)
    url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            exe_candidates = [f for f in z.namelist() if f.lower().endswith('.exe')]
            if not exe_candidates:
                print("No executable found inside Stockfish archive.")
                return None
            exe_name = exe_candidates[0]
            basename = os.path.basename(exe_name)
            target_path = os.path.join(target_dir, basename)
            # backup any current engine in bin
            paths = _paths()
            current = find_stockfish()
            if current and os.path.commonpath([os.path.dirname(current), target_dir]) == target_dir:
                # only back up if current is inside target_dir (our managed bin)
                import time, shutil as _sh
                bdir = os.path.join(target_dir, 'backup')
                os.makedirs(bdir, exist_ok=True)
                stamp = time.strftime('%Y%m%d-%H%M%S')
                bname = os.path.basename(current)
                backup_path = os.path.join(bdir, f"{bname}.{stamp}.bak")
                try:
                    _sh.copy2(current, backup_path)
                    _write_text(paths['previous'], backup_path)
                except Exception:
                    pass
            # extract to a temp file then move to target_path
            with z.open(exe_name) as src:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
                    tmp.write(src.read())
                    tmp_path = tmp.name
            try:
                os.replace(tmp_path, target_path)
            except Exception:
                with open(tmp_path, 'rb') as srcf, open(target_path, 'wb') as dstf:
                    dstf.write(srcf.read())
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        try:
            os.chmod(target_path, 0o755)
        except Exception:
            pass
        # persist selection
        _write_text(paths['selected'], target_path)
        return target_path if os.path.isfile(target_path) else None
    except Exception as e:
        print(f"Stockfish install failed: {e}")
        return None

def get_engine_version(exec_path: str) -> str:
    import subprocess
    try:
        cp = subprocess.run([exec_path, '--version'], capture_output=True, text=True, timeout=5)
        out = (cp.stdout or cp.stderr or '').strip()
        return out.splitlines()[0] if out else 'unknown'
    except Exception:
        return 'unknown'

def get_latest_stockfish_tag(timeout: float = 5.0) -> str | None:
    """Return latest Stockfish release tag from GitHub, or None on error.

    This is a lightweight check used only to display an 'update available' hint.
    """
    try:
        import requests
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "analyze-chess-app"}
        r = requests.get(
            "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest",
            headers=headers,
            timeout=timeout,
        )
        if r.ok:
            data = r.json()
            tag = data.get("tag_name")
            return str(tag) if tag else None
    except Exception:
        pass
    return None

def _extract_numeric_version(s: str) -> str | None:
    import re
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)*)", s)
    return m.group(1) if m else None

@app.route('/')
@app.route("/analyze_chess_move")
def analyze_chess_move():
    import os
    # Determine current engine status
    current = engine_path or find_stockfish()
    version = get_engine_version(current) if current else 'not installed'
    latest_tag = get_latest_stockfish_tag()
    latest_num = _extract_numeric_version(latest_tag or '')
    curr_num = _extract_numeric_version(version)
    update_available = bool(latest_num and curr_num and latest_num != curr_num)
    msg = request.args.get('msg', '')
        return render_template_string('''
            <html>
            <head><title>Analyze Next Best Chess Move!</title></head>
            <body>
                <div style="text-align:center;margin-bottom:18px;">
                    <img src="/assets/chess_icon.png" alt="Chess Icon" style="height:64px;vertical-align:middle;margin-right:12px;">
                    <span style="font-size:2em;font-weight:bold;vertical-align:middle;">Analyze Next Best Chess Move!</span>
                </div>
                {% if msg %}<div style="padding:8px;margin-bottom:10px;background:#eef;border:1px solid #99c;">{{msg}}</div>{% endif %}
                <div style="margin-bottom:12px;">
                    <strong>Engine:</strong>
                    {% if current %}
                        <div>Path: {{current}}</div>
                        <div>Version: {{version}}</div>
                        {% if latest_tag %}<div>Latest release: {{latest_tag}}</div>{% endif %}
                        {% if update_available %}
                            <div style="color:#b00;font-weight:bold;">Update available</div>
                        {% endif %}
                    {% else %}
                        <div>Not installed</div>
                    {% endif %}
                </div>

                <div style="display:flex;gap:10px;margin-bottom:16px;">
                    <form action="/update_engine_now" method="post">
                        <button type="submit">Update Engine Now</button>
                    </form>
                    <form action="/schedule_update" method="post">
                        <input type="hidden" name="what" value="engine" />
                        <button type="submit">Update Engine on Next Launch</button>
                    </form>
                    <form action="/schedule_update" method="post">
                        <input type="hidden" name="what" value="deps" />
                        <button type="submit">Update Python Packages on Next Launch</button>
                    </form>
                    <form action="/rollback_engine_now" method="post">
                        <button type="submit">Rollback Engine (Use Previous)</button>
                    </form>
                </div>

            <form action="/submit" method="post">
                FEN: <input type="text" name="fen"><br>
                <input type="submit" value="Submit">
            </form>
        </body>
        </html>
        ''', current=current, version=version, latest_tag=latest_tag, update_available=update_available, msg=msg)

@app.route('/submit', methods=['POST'])
def submit():
    fen = request.form.get('fen', '').strip()

    # Validate input
    if not fen:
        return ("Missing FEN in form data", 400)

    try:
        # chess.Board will raise for invalid FEN
        board = chess.Board(fen)
    except Exception as e:
        return (f"Invalid FEN: {e}", 400)

    # Use the globally determined engine_path. Installation is performed at
    # startup (interactive prompt) and will populate `engine_path` if the
    # user accepted installation. If no engine is available, return a safe
    # fallback move so the endpoint remains usable.
    import os
    global engine_path
    if not engine_path or not os.path.isfile(engine_path):
        try:
            first_move = next(iter(board.legal_moves))
            return (f"Engine not available. Fallback move: {first_move}", 200)
        except StopIteration:
            return ("No legal moves available for this position", 400)

    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        result = engine.play(board, chess.engine.Limit(time=2.0))
        try:
            engine.quit()
        except Exception:
            pass
        return f"Best move: {result.move}"
    except Exception as e:
        # Return an HTML page with actionable buttons and a retry form
        return render_template_string('''
            <html><body>
            <div style="padding:8px;margin-bottom:10px;background:#fee;border:1px solid #c99;">
            <strong>Engine error:</strong> {{err}}
            </div>
            <div style="display:flex;gap:10px;margin-bottom:16px;">
              <form action="/update_engine_now" method="post"><button type="submit">Update Engine Now</button></form>
              <form action="/schedule_update" method="post"><input type="hidden" name="what" value="engine" /><button type="submit">Update on Next Launch</button></form>
              <form action="/schedule_update" method="post"><input type="hidden" name="what" value="deps" /><button type="submit">Update Packages Next Launch</button></form>
              <form action="/rollback_engine_now" method="post"><button type="submit">Rollback Engine</button></form>
            </div>
            <form action="/submit" method="post">
              <input type="hidden" name="fen" value="{{fen}}" />
              <button type="submit">Retry Submit</button>
            </form>
            <div style="margin-top:10px;"><a href="{{url_for('analyze_chess_move')}}">Back</a></div>
            </body></html>
        ''', err=str(e), fen=fen), 500

@app.post('/update_engine_now')
def update_engine_now():
    import os
    bin_dir = os.path.join(os.path.dirname(__file__), 'bin')
    path = install_stockfish_to_dir(bin_dir)
    if path:
        global engine_path
        engine_path = path
        return redirect(url_for('analyze_chess_move', msg=f'Engine installed: {os.path.basename(path)}'))
    return redirect(url_for('analyze_chess_move', msg='Engine update failed. Check logs.'))

@app.post('/schedule_update')
def schedule_update():
    import os
    what = request.form.get('what', '')
    root = os.path.dirname(__file__)
    if what == 'engine':
        flag = os.path.join(root, '.update_engine')
        open(flag, 'a').close()
        return redirect(url_for('analyze_chess_move', msg='Engine update scheduled. It will install on next launch.'))
    elif what == 'deps':
        flag = os.path.join(root, '.update_deps')
        open(flag, 'a').close()
        return redirect(url_for('analyze_chess_move', msg='Dependency update scheduled. It will install on next launch.'))
    else:
        return redirect(url_for('analyze_chess_move', msg='Unknown update type.'))

@app.post('/rollback_engine_now')
def rollback_engine_now():
    import os
    p = _paths()
    prev = _read_text(p['previous'])
    if prev and os.path.isfile(prev):
        _write_text(p['selected'], prev)
        global engine_path
        engine_path = prev
        return redirect(url_for('analyze_chess_move', msg='Rolled back to previous engine.'))
    return redirect(url_for('analyze_chess_move', msg='No previous engine to rollback to.'))

@app.errorhandler(500)
def handle_internal_error(err):
    # Generic friendly error page with actions
    return render_template_string('''
        <html><body>
        <div style="padding:8px;margin-bottom:10px;background:#fee;border:1px solid #c99;">
          <strong>Unexpected error:</strong> {{err}}
        </div>
        <div style="display:flex;gap:10px;margin-bottom:16px;">
          <form action="/update_engine_now" method="post"><button type="submit">Update Engine Now</button></form>
          <form action="/schedule_update" method="post"><input type="hidden" name="what" value="engine" /><button type="submit">Update Engine Next Launch</button></form>
          <form action="/schedule_update" method="post"><input type="hidden" name="what" value="deps" /><button type="submit">Update Packages Next Launch</button></form>
          <form action="/rollback_engine_now" method="post"><button type="submit">Rollback Engine</button></form>
        </div>
        <div><a href="{{url_for('analyze_chess_move')}}">Go to Home</a></div>
        </body></html>
    ''', err=str(err)), 500

# --- HEALTH CHECK (add near your other routes) ---
@app.get("/__ac_health")
def ac_health():
    # return a fixed token the launcher will look for
    return "analyze_chess_ok"

# Optional: standard Flask entry point
import socket
def find_free_port(default_port=5002):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", default_port))
        s.close()
        return default_port
    except OSError:
        s.close()
        # Find a free port
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.bind(("127.0.0.1", 0))
        port = s2.getsockname()[1]
        s2.close()
        return port

import webbrowser
import os
if __name__ == "__main__":
    # Auto-discover the engine if not explicitly set
    stockfish_path = engine_path or find_stockfish()
    # If not found, and running interactively, offer to download and install
    # Stockfish into the project ./bin folder so everyone uses a consistent
    # binary regardless of renamed local files.
    if not stockfish_path:
        import sys
        proj_bin = os.path.join(os.path.dirname(__file__), 'bin')
        os.makedirs(proj_bin, exist_ok=True)

        def install_stockfish(target_dir):
            """Download Stockfish zip, extract the engine exe and preserve its filename.

            Returns the absolute path to the installed executable on success, or
            None on failure.
            """
            try:
                import requests, zipfile, io, tempfile
            except ImportError:
                print("requests package not available; cannot auto-install Stockfish.")
                return None
            url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    exe_candidates = [f for f in z.namelist() if f.lower().endswith('.exe')]
                    if not exe_candidates:
                        print("No executable found inside Stockfish archive.")
                        return None
                    exe_name = exe_candidates[0]
                    basename = os.path.basename(exe_name)
                    target_path = os.path.join(target_dir, basename)
                    # extract to a temp file then move to target_path
                    with z.open(exe_name) as src:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp:
                            tmp.write(src.read())
                            tmp_path = tmp.name
                    try:
                        os.replace(tmp_path, target_path)
                    except Exception:
                        with open(tmp_path, 'rb') as srcf, open(target_path, 'wb') as dstf:
                            dstf.write(srcf.read())
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                try:
                    os.chmod(target_path, 0o755)
                except Exception:
                    pass
                return target_path if os.path.isfile(target_path) else None
            except Exception as e:
                print(f"Stockfish install failed: {e}")
                return None

        if sys.stdin and sys.stdin.isatty():
            resp = input("Stockfish engine not found. Download and install Stockfish into './bin'? [Y/n]: ").strip().lower()
            if resp in ('', 'y', 'yes'):
                print('Downloading Stockfish...')
                installed_path = install_stockfish(proj_bin)
                if installed_path:
                    stockfish_path = installed_path
                    print(f"Installed Stockfish to {installed_path}")
                else:
                    print("Automatic installation failed. You can set STOCKFISH_PATH to point to a Stockfish executable.")
            else:
                print("Skipping Stockfish installation; engine features will fallback.")
        else:
            print("Stockfish not found. To enable engine features, set STOCKFISH_PATH or run the app interactively to install automatically.")
    if stockfish_path:
        print(f"Using Stockfish at: {stockfish_path}")
        # export to module-global engine_path so request handlers can use it
        engine_path = stockfish_path
        if os.path.isfile(stockfish_path) and is_file_locked(stockfish_path):
            print(f"ERROR: The Stockfish engine file '{stockfish_path}' is locked by another process.\nPlease close all Python, Flask, or Stockfish windows and try again.")
            input("Press Enter to exit...")
            exit(1)
    else:
        print("Stockfish executable not found; engine features will fallback to a legal-move response.")
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Analyze Chess Flask app on http://{host}:{port}/analyze_chess_move ...")
    try:
        app.run(host=host, port=port)
    except Exception as e:
        print(f"Flask failed to start: {e}")
