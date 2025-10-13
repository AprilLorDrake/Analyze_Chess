# Create Taskbar Shortcut for Chess Analysis App
$AppPath = "C:\Projects\stockfish\chess_analysis\launch_chess_app.bat"
$ShortcutPath = [Environment]::GetFolderPath("Desktop") + "\Chess Analysis.lnk"
$IconPath = "C:\Projects\stockfish\chess_analysis\assets\chess_icon.ico"

# Create the shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $AppPath
$Shortcut.WorkingDirectory = "C:\Projects\stockfish\chess_analysis"
$Shortcut.Description = "Launch Chess Analysis Flask App"

# Set icon if available
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}

$Shortcut.Save()

Write-Host "Shortcut created on Desktop: $ShortcutPath"
Write-Host ""
Write-Host "To add to taskbar:"
Write-Host "1. Right-click the shortcut on your Desktop"
Write-Host "2. Select 'Pin to taskbar'"
Write-Host ""
Write-Host "Or drag the shortcut from Desktop to your taskbar."