# ♟️ Chess Analysis Web Application (v1.3.2)

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

A focused chess position analysis tool powered by the **Stockfish engine**, with a clean web UI, AI move suggestions, and explicit dependency management. Version **1.3.2** keeps the Python 3.14–ready stack while removing hard-coded paths from scripts/docs so the project runs cleanly from any clone. See the [CHANGELOG](CHANGELOG.md) for release notes.

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

1.  Clone the repository

```bash
git clone https://github.com/AprilLorDrake/Analyze_Chess.git
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

5. Install the dependencies

```bash
pip install -r requirements.txt
```

6. Run the application

```bash
python app.py
```

7. Open your browser: <http://127.0.0.1:5000/analyze_chess_move>

---

## 🖥️ Desktop Integration (Windows)

1. **Automatic shortcut creation** (PowerShell):

  ```powershell
  .\create_shortcut.ps1
  ```

2. **Manual with dynamic path detection**:

  ```powershell
  $DesktopPath = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" Desktop).Desktop
  $RepoPath = "<path-to-your-Analyze_Chess-clone>"  # e.g. (Get-Location).Path
  $WshShell = New-Object -ComObject WScript.Shell
  $Shortcut = $WshShell.CreateShortcut("$DesktopPath\Analyze Chess.lnk")
  $Shortcut.TargetPath = "$RepoPath\launch_analyze_chess.bat"
  $Shortcut.IconLocation = "$RepoPath\assets\chess_icon.ico"
  $Shortcut.WorkingDirectory = $RepoPath
  $Shortcut.Save()
  ```

3. **Manual UI**:
  - Desktop → New → Shortcut → point to `launch_analyze_chess.bat`
  - Name it “Analyze Chess” and assign `assets\chess_icon.ico`

The shortcut kills conflicting Python processes, activates the venv, runs Flask, and opens your browser automatically.

---

## 📁 Project Structure

<details>
<summary>Click to expand</summary>

```
.
├── app.py
├── assets
│   ├── chess_banner.png
│   ├── chess_icon.ico
│   ├── chess_icon.png
│   ├── Example UI Results 1.png
│   └── Example UI Results 2 (Component Management).png
├── CONTRIBUTOR.md
├── create_shortcut.ps1
├── Dockerfile
├── INSTALL.md
├── README.md
├── requirements.txt
├── run_app.bat
├── tests
│   └── test_placeholder.py
└── ...
```

</details>

---

## ♟️ What is FEN?

**FEN (Forsyth–Edwards Notation)** encodes a board position, side to move, castling rights, en passant square, halfmove clock, and fullmove number.

Example:

```
rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
```

---

## 🧠 AI Analysis Approach

The fallback AI suggestions consider:

- Material evaluation (piece values)
- Tactical signals (checks/mates)
- Center control
- Basic safety heuristics

It complements Stockfish rather than replacing it.

---

## 🧩 Architecture & Internals

- **Backend**: Flask
- **Engine**: Stockfish 17.1
- **Frontend**: HTML/CSS
- **Dependencies**: python-chess, Flask, requests, stockfish
- **Packaging**: Docker-ready
- **Dependency Health**: Runtime PyPI checks

---

## 📌 Recent Updates (v1.3.2)

- ✅ **Portable launch scripts** (no hard-coded paths)
- ✅ **Docs without hard-coded paths** plus OneDrive-safe desktop detection
- ✅ **Version metadata synced** across project + packaging
- 🔜 Docker image rebuild (pending)

Previous releases are listed in [CHANGELOG](CHANGELOG.md).

---

## 🙌 Contributors

See [CONTRIBUTOR.md](CONTRIBUTOR.md) for the growing list of folks helping build Analyze_Chess. Want to join in? Fork, open a PR, or start a discussion!

---

© 2025 Drake Svc LLC

## Contributing

PRs welcome — ideas, fixes, features… all help make the puzzle feel smoother.

------------------------------------------------------------------------

## Collaborators

![Contributors](https://contrib.rocks/image?repo=AprilLorDrake/Analyze_Chess=10)

Meet all our amazing contributors here:

➡️ **[CONTRIBUTORS.md](./CONTRIBUTORS.md)**

---

© 2025 Drake Svc LLC. All rights reserved.
