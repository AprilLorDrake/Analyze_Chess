# PowerShell script to create desktop shortcut and instructions for taskbar
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile = Join-Path $ScriptPath "launch_chess_simple.bat"
$ShortcutPath = [Environment]::GetFolderPath("Desktop") + "\Chess Analysis.lnk"
$IconPath = Join-Path $ScriptPath "assets\chess_icon.ico"

Write-Host "Creating desktop shortcut..." -ForegroundColor Green

# Create the shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $BatchFile
$Shortcut.WorkingDirectory = $ScriptPath
$Shortcut.Description = "Launch Chess Analysis Flask App"

# Set icon if available
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
    Write-Host "Using chess icon: $IconPath" -ForegroundColor Yellow
} else {
    Write-Host "Chess icon not found, using default icon" -ForegroundColor Yellow
}

$Shortcut.Save()

Write-Host ""
Write-Host "✅ Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "   Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "🖱️  To add to your taskbar:" -ForegroundColor Yellow
Write-Host "   1. Find the 'Chess Analysis' shortcut on your Desktop"
Write-Host "   2. Right-click on it"
Write-Host "   3. Select 'Pin to taskbar'"
Write-Host ""
Write-Host "   OR simply drag the shortcut from Desktop to your taskbar!"
Write-Host ""
Write-Host "🚀 You can now launch your chess app from the taskbar anytime!" -ForegroundColor Green