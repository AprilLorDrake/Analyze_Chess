# ♟️ Chess Analysis Web Application (v1.3.1)

<p align="center">
  <a href="assets/chess_banner.png">
    <img
      src="assets/chess_banner.png"
      alt="Wooden chessboard banner with a light king in focus and blurred pieces in the background"
      width="100%"
    />
  </a>
</p>

![Last Commit](https://img.shields.io/github/last-commit/AprilLorDrake/Analyze_Chess)
![CI](https://img.shields.io/github/actions/workflow/status/AprilLorDrake/Analyze_Chess/publish.yml?branch=master&label=CI)
![Repo Size](https://img.shields.io/github/repo-size/AprilLorDrake/Analyze_Chess)
![Issues](https://img.shields.io/github/issues/AprilLorDrake/Analyze_Chess)
![Stars](https://img.shields.io/github/stars/AprilLorDrake/Analyze_Chess)

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-web%20framework-black)
![Stockfish](https://img.shields.io/badge/engine-Stockfish-success)
![Docker](https://img.shields.io/badge/docker-ready-blue)

A focused chess position analysis tool powered by the **Stockfish engine**, with a clean web UI, built-in AI move suggestions, and explicit dependency management.

Designed for correctness, transparency, and fast iteration rather than opaque “one-click” analysis.

---

## ✨ Features

- **FEN Position Analysis**: Analyze any chess position using standard FEN notation
- **Stockfish Engine Integration**: Professional-grade engine analysis
- **AI Move Recommendations**: Custom chess logic for alternative move suggestions
- **Visual Chess Boards**: Interactive HTML board rendering
- **Smart UI Controls**: Button state guidance to prevent invalid actions
- **Component Management**: Dependency version tracking and updates
- **Modern UI**: Responsive purple-themed interface

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (fully tested up to Python 3.14)
- Virtual environment recommended

### Installation

Installation

1.  clone the repository

```bash
git clone https://github.com/AprilLorDrake/Analyze_Chess.git
```

2.  Change into the project directory

```bash
cd Analyze_Chess
```

3.  Create a virtual environment

```bash
python -m venv venv
```

4.  Activate the virtual environment

macOS / Linux

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

5.  Install dependencies

```bash
pip install -r requirements.txt
```

6. Run the application

```bash
python app.py
```

7.  Open the application in your browser

```bash
[http://127.0.0.1:5000/analyze_chess_move](localhost)
```

---
## Project Structure

```
<details>
<summary>Click to expand file structure</summary>
.
├── app.py
├── assets
│   ├── chess_icon.ico
│   ├── chess_icon.png
│   ├── Example UI Results 1.png
│   └── Example UI Results 2 (Component Management).png
├── auto_git_save.py
├── bin
│   └── stockfish.exe
├── CONTRIBUTOR.md
├── create_shortcut.ps1
├── DEVELOPMENT_SUMMARY.md
├── dev_start.bat
├── Dockerfile
├── .dockerignore
├── .github
│   ├── repository-info.md
│   └── workflows
│       └── publish.yml
├── .gitignore
├── INSTALL.md
├── launch_analyze_chess.bat
├── procfile
├── pyproject.toml
├── README.md
├── requirements.txt
├── run_app.bat
├── setup.py
├── step1.py
├── step2.py
├── step3.py
├── tests
│   └── test_placeholder.py
└── version.py

</details>
```
---

## ♟️ What is FEN?

**FEN (Forsyth–Edwards Notation)** is a compact representation of a chess position including:

- Piece placement
- Side to move
- Castling rights
- En passant square
- Halfmove clock
- Fullmove number

**Example**:
```
rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
```

---

## 🧠 AI Analysis Approach

The built-in AI provides alternative move suggestions using:

- Material evaluation (piece values)
- Tactical signals (checks and mates)
- Center control heuristics
- Basic safety evaluation

This complements Stockfish rather than replacing it.

---

## 🧩 Architecture & Internals

- **Backend**: Flask
- **Engine**: Stockfish 17.1
- **Frontend**: HTML/CSS
- **Dependencies**: python-chess, Flask, requests, stockfish
- **Packaging**: Docker-ready
- **Dependency Health**: Runtime version checks via PyPI

---

## 📌 Recent Updates (v1.3.1)

- Removed all image upload functionality
- Eliminated Pillow, OpenCV, NumPy dependencies
- Reduced startup time and memory usage
- Full Python 3.12–3.14 support
- Removed 144 lines of unused code

---

## Contributing

PRs welcome — ideas, fixes, features… all help make the puzzle feel smoother.

------------------------------------------------------------------------

## Collaborators

![Contributors](https://contrib.rocks/image?repo=AprilLorDrake/Analyze_Chess=10)

Meet all our amazing contributors here:

➡️ **[CONTRIBUTORS.md](./CONTRIBUTORS.md)**

---

© 2025 Drake Svc LLC. All rights reserved.
