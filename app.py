from flask import Flask, request, render_template_string
import chess
import chess.engine

app = Flask(__name__)

# Path to the Stockfish engine
engine_path = r"C:\Projects\pyscripts\bin\stockfish.exe"

@app.route('/')
@app.route("/analyze_chess_move")
def analyze_chess_move():
    return render_template_string('''
        <html>
        <head><title>analyze_chess_move</title></head>
        <body>
        <form action="/submit" method="post">
            FEN: <input type="text" name="fen"><br>
            <input type="submit" value="Submit">
        </form>
        </body>
        </html>
    ''')

# Optionally keep the old index route, or redirect it:
@app.route("/")
def index():
    return analyze_chess_move()

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

    # Ensure engine binary exists; if not, provide a fallback move for testing
    import os
    def ensure_stockfish(engine_path):
        if os.path.isfile(engine_path):
            return True
        # Try to download and extract Stockfish
        import requests, zipfile, io
        url = "https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-windows-x86-64-avx2.zip"
        bin_dir = os.path.dirname(engine_path)
        os.makedirs(bin_dir, exist_ok=True)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                exe = [f for f in z.namelist() if f.lower().endswith(".exe")][0]
                with z.open(exe) as src, open(engine_path, "wb") as dst:
                    dst.write(src.read())
            return os.path.isfile(engine_path)
        except Exception as e:
            print(f"Stockfish download failed: {e}")
            return False

    if not ensure_stockfish(engine_path):
        # Fallback: return the first legal move (UCI) so the endpoint is usable
        try:
            first_move = next(iter(board.legal_moves))
            return (f"Engine not found and auto-download failed. Fallback move: {first_move}", 200)
        except StopIteration:
            return ("No legal moves available for this position", 400)

    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        result = engine.play(board, chess.engine.Limit(time=2.0))
    finally:
        try:
            engine.quit()
        except Exception:
            # ignore quit errors
            pass

    return f"Best move: {result.move}"

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
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting Analyze Chess Flask app on http://{host}:{port}/analyze_chess_move ...")
    try:
        app.run(host=host, port=port)
    except Exception as e:
        print(f"Flask failed to start: {e}")
