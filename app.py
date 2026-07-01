import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gui.main_window import TailChatMainWindow
from gui.styles import DARK_STYLESHEET
from services.room_service import room_service
from utils.logger import logger

_ROOT = Path(__file__).parent.resolve()


def main():
    logger.info("Starting TailChat desktop application…")
    app = QApplication(sys.argv)

    # App icon — relative path so it works on any machine
    icon_path = _ROOT / "assets" / "images" / "app_logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Theme
    from config.settings import load_settings
    from gui.styles import LIGHT_STYLESHEET
    settings = load_settings()
    theme = settings.get("theme", "dark")
    stylesheet = LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
    app.setStyleSheet(stylesheet)

    window = TailChatMainWindow()
    window.setStyleSheet(stylesheet)
    window.showMaximized()

    exit_code = app.exec()

    # Clean up room service on close
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
