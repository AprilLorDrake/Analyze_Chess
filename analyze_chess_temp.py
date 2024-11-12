import chess
import chess.engine

# Path to the Stockfish engine
engine_path = r"C:\Users\April\stockfish\stockfish\stockfish-windows-x86-64-avx2.exe"

# Create a new chess board
board = chess.Board()

# Load the position from a FEN string
fen = "2kr3r/pbp2pb1/1pN5/3N3p/2PP1pq1/P2B3p/1PQ2PP1/2R1R1K1 w - - 1 21"
board.set_fen(fen)

# Initialize the engine
engine = chess.engine.SimpleEngine.popen_uci(engine_path)

# Get the best move
result = engine.play(board, chess.engine.Limit(time=2.0))
print(f"Best move: {result.move}")

# Close the engine
engine.quit()
