# Installation Guide for Analyze Chess

## Method 1: Direct Installation from GitHub

### Prerequisites
- Python 3.8 or higher
- Git

### Steps
1. Clone the repository:
   `ash
   git clone https://github.com/AprilLorDrake/Analyze_Chess.git
   cd Analyze_Chess
   `

2. Create virtual environment:
   `ash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   `

3. Install dependencies:
   `ash
   pip install -r requirements.txt
   `

4. Run the application:
   `ash
   python app.py
   `

5. Open browser to: http://localhost:5000

### Optional: Desktop Shortcut (Windows)

Create a convenient desktop shortcut for one-click access:

**Option A: PowerShell Script** (Recommended)
```powershell
# Run the provided script that auto-detects correct Desktop path
.\create_shortcut.ps1
```

**Option B: Manual PowerShell Command** 
```powershell
# Auto-detect Desktop path (handles OneDrive redirection)
$DesktopPath = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" Desktop).Desktop
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Analyze Chess.lnk")
$Shortcut.TargetPath = "C:\Projects\Analyze_Chess\launch_analyze_chess.bat"
$Shortcut.IconLocation = "C:\Projects\Analyze_Chess\assets\chess_icon.ico"
$Shortcut.WorkingDirectory = "C:\Projects\Analyze_Chess"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully!"
```

**Option C: Manual Creation**
1. Right-click desktop → New → Shortcut
2. Browse to: `C:\Projects\Analyze_Chess\launch_analyze_chess.bat`
3. Name: "Analyze Chess"
4. Right-click shortcut → Properties → Change Icon
5. Browse to: `C:\Projects\Analyze_Chess\assets\chess_icon.ico`

**Features of the desktop launcher:**
- Automatic virtual environment activation
- Professional startup sequence with progress indicators
- Auto-opens browser to the chess analysis page
- Proper error handling and user feedback
- Custom chess piece icon

## Method 2: Python Package Installation (Coming Soon)

Once published to GitHub Packages:

`ash
pip install --index-url https://pypi.org/simple/ analyze-chess
analyze-chess
`

## Method 3: Docker Container

### Prerequisites
- Docker installed

### Steps
1. Pull and run the container:
   `ash
   docker run -p 5000:5000 ghcr.io/aprillordrake/analyze_chess:latest
   `

2. Open browser to: http://localhost:5000

## Method 4: One-Click Deploy

### Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AprilLorDrake/Analyze_Chess)

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/AprilLorDrake/Analyze_Chess)

## System Requirements
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **Memory**: 512MB RAM minimum, 1GB recommended
- **Storage**: 100MB free space
- **Network**: Internet connection for Stockfish updates

## Troubleshooting

### Common Issues
1. **Port 5000 already in use**:
   - Change port in pp.py: pp.run(host='0.0.0.0', port=8000)

2. **Stockfish not found**:
   - The app will auto-download Stockfish on first run
   - Or manually place Stockfish binary in in/ directory

3. **Python dependencies error**:
   - Ensure you're using Python 3.8+
   - Try: pip install --upgrade pip setuptools wheel

### Support
-  Report issues: [GitHub Issues](https://github.com/AprilLorDrake/Analyze_Chess/issues)
-  Documentation: [README.md](https://github.com/AprilLorDrake/Analyze_Chess/blob/master/README.md)
