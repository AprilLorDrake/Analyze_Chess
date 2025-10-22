# Create Desktop Shortcut for Chess Analysis
# This script automatically detects the correct Desktop path (even with OneDrive)

Write-Host "Creating Desktop Shortcut for Chess Analysis..." -ForegroundColor Cyan

# Get the actual Desktop path from registry (handles OneDrive Desktop redirection)
try {
    $DesktopPath = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" Desktop -ErrorAction Stop | Select-Object -ExpandProperty Desktop
    Write-Host "Desktop path detected: $DesktopPath" -ForegroundColor Green
} catch {
    # Fallback to standard path if registry read fails
    $DesktopPath = "$env:USERPROFILE\Desktop"
    Write-Host "Using fallback desktop path: $DesktopPath" -ForegroundColor Yellow
}

# Verify desktop path exists
if (-not (Test-Path $DesktopPath)) {
    Write-Host "Error: Desktop path does not exist: $DesktopPath" -ForegroundColor Red
    exit 1
}

# Get the directory where this script is located (project root)
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define paths
$ShortcutPath = Join-Path $DesktopPath "Analyze Chess.lnk"
$TargetPath = Join-Path $ProjectPath "launch_analyze_chess.bat"
$IconPath = Join-Path $ProjectPath "assets\chess_icon.ico"

# Verify required files exist
if (-not (Test-Path $TargetPath)) {
    Write-Host "Error: Launch script not found: $TargetPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $IconPath)) {
    Write-Host "Warning: Icon file not found: $IconPath" -ForegroundColor Yellow
    $IconPath = $null
}

# Create the shortcut
try {
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.WorkingDirectory = $ProjectPath
    $Shortcut.Description = "Launch Chess Analysis Application with Stockfish Engine"
    
    if ($IconPath) {
        $Shortcut.IconLocation = $IconPath
    }
    
    $Shortcut.Save()
    
    Write-Host "✅ Desktop shortcut created successfully!" -ForegroundColor Green
    Write-Host "📍 Shortcut location: $ShortcutPath" -ForegroundColor Cyan
    Write-Host "🎯 Target: $TargetPath" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Error creating shortcut: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n🚀 You can now double-click 'Analyze Chess' on your desktop to launch the application!" -ForegroundColor Green