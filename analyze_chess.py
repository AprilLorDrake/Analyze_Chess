import chess
import chess.engine

# Path to the Stockfish engine
engine_path = r"C:\Users\April\stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"

# Create a new chess board
board = chess.Board()

# Load the position from a FEN string
fen = "rnbqkb1r/ppp2ppp/8/3pN3/4n3/8/PPPPQPPP/RNB1KB1R w KQkq d6 0 5"
board.set_fen(fen)

# Initialize the engine
engine = chess.engine.SimpleEngine.popen_uci(engine_path)

# Get the best move
result = engine.play(board, chess.engine.Limit(time=2.0))
print(f"Best move: {result.move}")

# Close the engine
engine.quit()
