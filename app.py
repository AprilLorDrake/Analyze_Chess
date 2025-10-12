from flask import Flask, request, render_template_string
import chess
import chess.engine

app = Flask(__name__)

# Path to the Stockfish engine
engine_path = r"C:\Projects\pyscripts\bin\stockfish.exe"

@app.route('/')
def index():
    return render_template_string('''
        <form action="/submit" method="post">
            FEN: <input type="text" name="fen"><br>
            <input type="submit" value="Submit">
        </form>
    ''')

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
    if not os.path.isfile(engine_path):
        # Fallback: return the first legal move (UCI) so the endpoint is usable
        try:
            first_move = next(iter(board.legal_moves))
            return (f"Engine not found at configured path: {engine_path}. 
Fallback move: {first_move}", 200)
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
if __name__ == "__main__":
    app.run()
