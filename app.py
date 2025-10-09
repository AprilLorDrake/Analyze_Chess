from flask import Flask, request, render_template_string
import chess
import chess.engine

app = Flask(__name__)

# Path to the Stockfish engine
engine_path = r"C:\Users\April\stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"

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
    fen = request.form['fen']
    board = chess.Board()
    board.set_fen(fen)

    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    result = engine.play(board, chess.engine.Limit(time=2.0))
    engine.quit()

    return f"Best move: {result.move}"

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

