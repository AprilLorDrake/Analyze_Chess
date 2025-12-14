# Installation Guide for Analyze Chess

This guide covers installation, deployment options, and common troubleshooting scenarios across Windows, macOS, and Linux.

---

## Method 1: Direct Installation from GitHub (Recommended)

### Prerequisites
- **Python 3.11+** (tested with 3.11 through 3.14)
- Git
- Internet access (for dependency and Stockfish checks)

> If multiple Python versions are installed, ensure `python --version` resolves to 3.11+.

---

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/AprilLorDrake/Analyze_Chess.git
   cd Analyze_Chess
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   ```

   **Windows**
   ```powershell
   venv\Scripts\activate
   ```

   **macOS / Linux**
   ```bash
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

5. Open your browser:
   ```
   http://127.0.0.1:5000/analyze_chess_move
   ```

---

## Optional: Desktop Shortcut (Windows)

Create a one-click launcher for a clean startup experience.

### Option A: PowerShell Script (Recommended)
```powershell
.\create_shortcut.ps1
```

### Option B: Manual PowerShell Command
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

### Option C: Manual Creation
1. Right-click Desktop → New → Shortcut
2. Target: `launch_analyze_chess.bat` inside your clone
3. Name it **Analyze Chess**
4. Right-click → Properties → Change Icon → `assets\chess_icon.ico`

### Launcher Behavior
- Activates the virtual environment
- Stops conflicting Python processes
- Starts the Flask server
- Opens the browser automatically
- Displays clear startup and error messages

---

## Method 2: Python Package Installation (Planned)

Once published:
```bash
pip install analyze-chess
analyze-chess
```

---

## Method 3: Docker Container

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)

### Run
```bash
docker run -p 5000:5000 ghcr.io/aprillordrake/analyze_chess:latest
```

Then open:
```
http://127.0.0.1:5000
```

---

## Method 4: One-Click Deploy

### Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AprilLorDrake/Analyze_Chess)

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/AprilLorDrake/Analyze_Chess)

---

## System Requirements

- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.11+
- **Memory**: 512 MB minimum (1 GB recommended)
- **Disk**: ~100 MB free space
- **Network**: Required for dependency checks and Stockfish updates

---

## Troubleshooting

### Port Already in Use (Very Common)

Error:
```
Address already in use
```

#### Free the Port

**Windows**
```powershell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**macOS / Linux**
```bash
lsof -i :5000
kill -9 <PID>
```

#### Or Change the Port (Safer)

Edit `app.py`:
```python
app.run(port=5001)
```

Then open:
```
http://127.0.0.1:5001/analyze_chess_move
```

---

### Browser Opens but Page Does Not Load

- Confirm Flask started without errors
- Verify the browser port matches terminal output
- Disable VPNs or corporate endpoint protection temporarily

---

### Stockfish Not Found or Not Running

- Stockfish downloads automatically on first run
- Restart the app after initial download
- On macOS/Linux, ensure executable permission:
```bash
chmod +x stockfish
```

---

### Dependency Installation Failures

Upgrade tooling:
```bash
python -m pip install --upgrade pip setuptools wheel
```

Verify Python version:
```bash
python --version
```

---

### Flask Will Not Restart Cleanly (Windows)

If repeated restarts fail:
```powershell
taskkill /IM python.exe /F
```

---

## Support

- Issues: https://github.com/AprilLorDrake/Analyze_Chess/issues
- Main README: https://github.com/AprilLorDrake/Analyze_Chess/blob/master/README.md

---

© 2025 Drake Svc LLC. All rights reserved.
