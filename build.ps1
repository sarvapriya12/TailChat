# ============================================================
#  TailChat — One-Click Secure Build Script
#  Run from the project root:
#    powershell -ExecutionPolicy Bypass -File build.ps1
#
#  What this script does:
#    1. Runs PyArmor to obfuscate all Python source into obf_dist/
#       (if PyArmor trial is exhausted, the obfuscated files already
#        in obf_dist/ are reused — only app.py is re-patched)
#    2. Patches obf_dist/app.py with our plain-Python bootstrapper
#       that imports hidden_imports to force module bundling
#    3. Copies .env into obf_dist/
#    4. Runs PyInstaller from obf_dist/ using TailChat.spec
#    5. Creates a distributable TailChat_Release.zip
# ============================================================

# $ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TailChat Secure Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Paths ────────────────────────────────────────────────────────────
$VENV_PYTHON  = "$ROOT\.venv\Scripts\python.exe"
$VENV_PYARMOR = "$ROOT\.venv\Scripts\pyarmor.exe"
$VENV_PYINST  = "$ROOT\.venv\Scripts\pyinstaller.exe"
$OBF_DIR      = "$ROOT\obf_dist"
$DIST_DIR     = "$OBF_DIR\dist\TailChat"
$ZIP_PATH     = "$OBF_DIR\dist\TailChat_Release.zip"

# ── Sanity checks ────────────────────────────────────────────────────
foreach ($exe in @($VENV_PYTHON, $VENV_PYINST)) {
    if (-not (Test-Path $exe)) {
        Write-Host "ERROR: Not found: $exe" -ForegroundColor Red
        Write-Host "Run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt pyarmor pyinstaller" -ForegroundColor Yellow
        exit 1
    }
}

# ── Step 1: PyArmor obfuscation (optional — skipped if trial expired) ─
Write-Host "[1/4] Running PyArmor obfuscation..." -ForegroundColor Yellow
Set-Location $ROOT

if (Test-Path $VENV_PYARMOR) {
    & $VENV_PYARMOR gen `
        --output obf_dist `
        --recursive `
        app.py gui auth network services voice video files database config utils `
        2>&1 | Tee-Object -Variable pyarmorOutput

    if ($LASTEXITCODE -ne 0) {
        Write-Host "      WARNING: PyArmor returned exit code $LASTEXITCODE" -ForegroundColor Yellow
        Write-Host "      (Trial may be exhausted - using previously obfuscated obf_dist/ files)" -ForegroundColor Yellow
        Write-Host "      Continuing build with existing obf_dist/ contents..." -ForegroundColor Yellow
    } else {
        Write-Host "      Obfuscation complete." -ForegroundColor Green
    }
} else {
    Write-Host "      PyArmor not found - using existing obf_dist/ files." -ForegroundColor Yellow
}

# ── Step 1b: Always patch obf_dist/app.py with our bootstrapper ──────
#   This is necessary whether or not PyArmor ran, because PyArmor
#   overwrites app.py with an obfuscated blob that doesn't call
#   hidden_imports. Our bootstrapper is the entry point PyInstaller uses.
Write-Host "      Patching obf_dist/app.py (hidden_imports bootstrapper)..." -ForegroundColor Yellow
$APP_CONTENT = @'
import hidden_imports   # Force PyInstaller to bundle all required modules
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import TailChatMainWindow
from gui.styles import DARK_STYLESHEET
from services.room_service import room_service
from utils.logger import logger

_ROOT = Path(__file__).parent.resolve()


def main():
    logger.info("Starting TailChat desktop application...")
    app = QApplication(sys.argv)

    # App icon — resolved relative to the EXE/_internal directory
    icon_path = _ROOT / "assets" / "images" / "app_logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from config.settings import load_settings
    from gui.styles import LIGHT_STYLESHEET, DARK_STYLESHEET
    settings = load_settings()
    theme = settings.get("theme", "dark")
    active_style = LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
    app.setStyleSheet(active_style)

    main_window = TailChatMainWindow()
    main_window.setStyleSheet(active_style + "\n#mainWindow { background-color: #121212; }")
    main_window.showMaximized()

    exit_code = app.exec()

    # Clean up room service on exit
    try:
        room_service.leave_room()
        if room_service.loop:
            room_service.loop.call_soon_threadsafe(room_service.loop.stop)
    except Exception:
        pass

    logger.info("Application exited.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
'@
Set-Content -Path "$OBF_DIR\app.py" -Value $APP_CONTENT -Encoding UTF8
Write-Host "      app.py patched." -ForegroundColor Green

# ── Step 2: Copy .env into obf_dist/ (needed at runtime) ─────────────
Write-Host "[2/4] Copying .env to obf_dist/..." -ForegroundColor Yellow
Copy-Item -Force "$ROOT\.env" "$OBF_DIR\.env"
Write-Host "      .env copied." -ForegroundColor Green

# ── Step 3: PyInstaller from obf_dist using TailChat.spec ────────────
Write-Host "[3/4] Running PyInstaller..." -ForegroundColor Yellow
Set-Location $OBF_DIR

& $VENV_PYINST TailChat.spec --noconfirm 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller failed (exit $LASTEXITCODE)" -ForegroundColor Red
    Set-Location $ROOT
    exit 1
}
Write-Host "      PyInstaller complete." -ForegroundColor Green

# ── Step 4: Create release zip ────────────────────────────────────────
Write-Host "[4/4] Creating release zip..." -ForegroundColor Yellow
if (Test-Path $ZIP_PATH) { Remove-Item $ZIP_PATH -Force }
Compress-Archive -Path $DIST_DIR -DestinationPath $ZIP_PATH -CompressionLevel Optimal

$zipItem = Get-Item $ZIP_PATH
$exeItem = Get-Item "$DIST_DIR\TailChat.exe"
Write-Host "      Zip created: $([math]::Round($zipItem.Length / 1MB, 1)) MB" -ForegroundColor Green

# ── Summary ───────────────────────────────────────────────────────────
Set-Location $ROOT

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  EXE  : $DIST_DIR\TailChat.exe" -ForegroundColor Cyan
Write-Host "  Size : $([math]::Round($exeItem.Length / 1MB, 2)) MB" -ForegroundColor White
Write-Host ""
Write-Host "  ZIP  : $ZIP_PATH" -ForegroundColor Cyan
Write-Host "  Size : $([math]::Round($zipItem.Length / 1MB, 1)) MB" -ForegroundColor White
Write-Host ""
Write-Host "  To distribute: share the ZIP file." -ForegroundColor White
Write-Host "  Recipient extracts it and runs TailChat\TailChat.exe" -ForegroundColor White
Write-Host ""
