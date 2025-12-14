# Installation Guide for Analyze Chess

## Method 1: Direct Installation from GitHub

### Prerequisites
- **Python 3.11** (Python 3.12+ not yet supported)
- Git

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/AprilLorDrake/Analyze_Chess.git
   cd Analyze_Chess
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open your browser to http://localhost:5000

### Optional: Desktop Shortcut (Windows)
Create a convenient desktop shortcut for one-click access.

**Option A: PowerShell Script (recommended)**
```powershell
.\create_shortcut.ps1
```

**Option B: Manual PowerShell command**
```powershell
$DesktopPath = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" Desktop).Desktop
$RepoPath = "<path-to-your-Analyze_Chess-clone>"  # e.g., (Get-Location).Path if you're in the repo root
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Analyze Chess.lnk")
$Shortcut.TargetPath = "$RepoPath\launch_analyze_chess.bat"
$Shortcut.IconLocation = "$RepoPath\assets\chess_icon.ico"
$Shortcut.WorkingDirectory = $RepoPath
$Shortcut.Save()
```

**Option C: Manual creation**
1. Right-click the desktop → New → Shortcut
2. Point to `launch_analyze_chess.bat` in your clone directory
3. Name it "Analyze Chess"
4. Right-click the shortcut → Properties → Change Icon
5. Select `assets\chess_icon.ico` from your clone

**Launcher perks**
- Activates the virtual environment automatically
- Provides a professional startup experience
- Opens the browser to the chess analysis page
- Displays clear error handling
- Uses the custom chess icon

## Method 2: Python Package Installation (Coming Soon)
These commands will work once the package is published:
```bash
pip install --index-url https://pypi.org/simple/ analyze-chess
analyze-chess
```

## Method 3: Docker Container

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)

### Steps
1. Run the container:
   ```bash
   docker run -p 5000:5000 ghcr.io/aprillordrake/analyze_chess:latest
   ```
2. Open your browser to http://localhost:5000

## Method 4: One-Click Deploy

### Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AprilLorDrake/Analyze_Chess)

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/AprilLorDrake/Analyze_Chess)

## System Requirements
- **OS**: Windows 10+, macOS 10.14+, or Ubuntu 18.04+
- **Python**: 3.11 (recommended)
- **Memory**: 1 GB RAM (minimum 512 MB)
- **Storage**: 100 MB free space
- **Network**: Internet access for Stockfish updates

## Troubleshooting

1. **Port 5000 already in use**
   - Edit `app.py` and run the server on a different port: `app.run(host="0.0.0.0", port=8000)`
2. **Stockfish not found**
   - The app downloads Stockfish automatically on first run.
   - Alternatively place the Stockfish binary in the `bin/` directory.
3. **Dependency installation errors**
   - Verify you are using Python 3.11.
   - Upgrade tooling: `python -m pip install --upgrade pip setuptools wheel`.

### Support
- Report issues: [GitHub Issues](https://github.com/AprilLorDrake/Analyze_Chess/issues)
- Documentation: [README](https://github.com/AprilLorDrake/Analyze_Chess/blob/master/README.md)
