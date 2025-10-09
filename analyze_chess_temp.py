# analyze_chess.py
from flask import Flask, request, jsonify
import os, shutil
import chess
import chess.engine

app = Flask(__name__)

def find_engine():
    # 1) honor explicit path via env var if you want
    explicit = os.environ.get("STOCKFISH_PATH")
    if explicit and os.path.exists(explicit):
        return explicit

    # 2) try your known local path (edit if different)
    candidates = [
        r"C:\Users\April\stockfish\stockfish\stockfish-windows-x86-64-avx2.exe",
        r".\stockfish.exe",
        r".\stockfish\stockfish-windows-x86-64-avx2.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
