
# Chess Analysis Web Application (v1.3.2)

A comprehensive chess analysis tool powered by Stockfish engine with built-in AI recommendations and dependency management. Version 1.3.2 keeps the Python 3.14-ready stack while cleaning up hard-coded paths and making launcher/docs fully portable. See [CHANGELOG](CHANGELOG.md) for release notes.

## Features

- **FEN Position Analysis**: Enter any chess position in FEN notation for analysis
- **Stockfish Engine Integration**: Professional-grade chess engine analysis
- **AI Move Recommendations**: Built-in custom chess logic AI for alternative move suggestions
- **Visual Chess Boards**: Interactive HTML chess board visualization
- **Smart UI Controls**: Intuitive button states guide workflow (green for active actions, grey for completed)
- **Component Management**: Individual dependency tracking and update management
- **Modern UI**: Purple-themed responsive web interface with enhanced user experience

## What is FEN?

**FEN (Forsyth-Edwards Notation)** is a standard notation for describing a particular board position in chess. It provides a compact way to represent:

- **Piece placement** on the board (rank by rank)
- **Active color** (whose turn it is)
- **Castling availability** for both sides
- **En passant target square** (if applicable)
- **Halfmove clock** (moves since last capture or pawn move)
- **Fullmove number** (increments after Black's move)

**Example FEN**: `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`

This represents the position after White plays 1.e4 in the opening, with Black to move next.

## Screenshots

### Main Analysis Interface
![Chess Analysis Interface](assets/Example%20UI%20Results%201.png)

The main interface shows FEN input, Stockfish recommendations, AI suggestions, and visual chess boards.

### Component Management System
![Component Management](assets/Example%20UI%20Results%202%20(Component%20Management).png)

Individual dependency management with version tracking and update controls for Stockfish engine and Python packages.

## Getting Started

### Prerequisites
- **Python 3.14** (recommended - latest stable version)
- **Python 3.11+** also supported
- Virtual environment (recommended)

### Installation

1. Clone the repository
2. Set up virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open your browser to `http://127.0.0.1:5000/analyze_chess_move`

### Desktop Integration (Windows)

For convenient desktop access, use the included launch script or create a shortcut:

1. **Automatic shortcut creation** (PowerShell):
   ```powershell
   # Run the provided script that auto-detects correct Desktop path
   .\create_shortcut.ps1
   ```
   
   Or manually with dynamic path detection:
   ```powershell
   # Auto-detect Desktop path (handles OneDrive redirection)
   $DesktopPath = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" Desktop).Desktop
   $RepoPath = "<path-to-your-Analyze_Chess-clone>"  # e.g., (Get-Location).Path if you're in the repo root
   $WshShell = New-Object -comObject WScript.Shell
   $Shortcut = $WshShell.CreateShortcut("$DesktopPath\Analyze Chess.lnk")
   $Shortcut.TargetPath = "$RepoPath\launch_analyze_chess.bat"
   $Shortcut.IconLocation = "$RepoPath\assets\chess_icon.ico"
   $Shortcut.WorkingDirectory = $RepoPath
   $Shortcut.Save()
   ```

2. **Manual shortcut creation**:
   - Right-click on desktop → New → Shortcut
   - Target: Path to `launch_analyze_chess.bat` in your clone
   - Name: "Analyze Chess"
   - Change icon to `assets\chess_icon.ico` in your clone

The desktop shortcut will:
- Kill any running Python processes
- Activate the Python virtual environment
- Start the Flask application
- Automatically open your default browser
- Display a professional startup sequence

## Usage

1. Enter a chess position in FEN notation
2. Click "Analyze Position" (green button) to get recommendations
3. View Stockfish engine analysis and AI suggestions
4. After analysis completes:
   - **Analyze button** turns grey (analysis complete)
   - **Reset button** turns green (ready for next analysis)
5. Click the green "Reset" button to clear results and start over
6. See visual chess boards showing recommended moves
7. Manage engine and dependencies in the About section

## Technical Details

- **Backend**: Flask web framework
- **Python Version**: 3.14.0 (latest stable)
- **Chess Engine**: Stockfish 17.1 (professional chess analysis)
- **AI Engine**: Custom chess principles evaluation with:
  - Piece capture analysis (material values)
  - Check and checkmate detection
  - Center square control evaluation
  - Basic safety assessment
- **Frontend**: HTML/CSS with purple gradient theme
- **Dependencies**: Flask, python-chess, requests, stockfish
- **Dependency Management**: Real-time version checking with PyPI integration

## Recent Updates (v1.3.2)

### What's New:
- ✅ **Portable Launch Scripts**: Batch/PowerShell launchers now use script-relative paths so the app runs from any clone location without hard-coded drive letters.
- ✅ **Docs Without Hard-Coded Paths**: README/INSTALL now show placeholder repo paths and OneDrive-safe desktop detection; no `C:\...` baked into instructions.
- ✅ **Release Metadata Sync**: Version bumped to 1.3.2 across code and packaging metadata.

### Previous Updates:
- v1.3.1: Removed image upload, dropped Pillow/OpenCV/numpy deps, improved performance, Python 3.14 ready
- v1.2.5: Fixed CI build by removing conflicting dependencies
- v1.2.4: Python 3.14 support, enhanced opening positions, auto-analysis
- v1.2.3: Modal board expansion for opening positions with full-size visualization
- v1.2.2: Improved button state management and launch scripts
- v1.2.1: Component management system with individual update controls

## AI Analysis Features

The built-in AI recommendation system provides alternative move suggestions using:
- **Material evaluation**: Prioritizes captures based on piece values
- **Tactical awareness**: Favors checks and checkmate opportunities  
- **Positional understanding**: Encourages center control
- **Safety assessment**: Avoids placing pieces in danger

This complements Stockfish analysis by offering a different analytical perspective.

---
© 2025 Drake Svc LLC. All rights reserved.

