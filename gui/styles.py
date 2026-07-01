# ──────────────────────────────────────────────────────────────────────────────
#  TailChat — Premium Dark UI System
#  Palette: deep-space navy with cobalt-blue accent, glass surfaces, soft glows
# ──────────────────────────────────────────────────────────────────────────────
#
#  Dark palette
#    bg-deep:     #0d0f14   deep background (root canvas)
#    bg-base:     #13151c   primary surface
#    bg-panel:    #181b24   panels / sidebar
#    bg-card:     #1e2130   cards / dialogs
#    bg-elevated: #252839   elevated surfaces (hover, selected)
#    bg-input:    #1a1d27   input fields
#    accent:      #5b8af0   cobalt blue accent
#    accent-dim:  #3d64c8   pressed / darker accent
#    accent-glow: rgba(91,138,240,0.18)  glow ring
#    green:       #4ade80
#    amber:       #fbbf24
#    red:         #f87171
#    text-1:      #e8ecf4   primary text
#    text-2:      #8892a8   secondary text
#    text-3:      #4a5168   muted / placeholder
#    border:      rgba(255,255,255,0.06)
#    border-hover:rgba(91,138,240,0.40)
# ──────────────────────────────────────────────────────────────────────────────

DARK_STYLESHEET = '''
/* ═══════════════════════════════════════════════════════════════════ GLOBAL */
* {
    font-family: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
    font-size: 14px;
    color: #e8ecf4;
    outline: none;
}

/* ═══════════════════════════════════════════════════════════ BASE CONTAINERS */
QMainWindow, FramelessWindow, TailChatMainWindow {
    background-color: #0d0f14;
}
QDialog {
    background-color: #13151c;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
}
QStackedWidget {
    background-color: transparent;
}
QWidget {
    background-color: transparent;
    color: #e8ecf4;
}

/* ═══════════════════════════════════════════════════════════════════ SIDEBAR */
QWidget#leftPanel, SidebarWidget {
    background-color: #181b24;
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* ══════════════════════════════════════════════════════════════════ SPLITTER */
QSplitter::handle { background: transparent; width: 1px; }
QSplitter::handle:horizontal { border-left: 1px solid rgba(255,255,255,0.05); }
QSplitter::handle:vertical   { border-top:  1px solid rgba(255,255,255,0.05); }

/* ════════════════════════════════════════════════════════════════════ LABELS */
QLabel { color: #e8ecf4; background: transparent; }
QLabel#titleLabel {
    font-size: 30px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #8892a8;
}
QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: #4a5168;
    text-transform: uppercase;
}

/* ════════════════════════════════════════════════════════════ SEPARATOR LINE */
QFrame#separatorLine {
    background-color: rgba(255,255,255,0.06);
    max-height: 1px;
    min-height: 1px;
    border: none;
}

/* ══════════════════════════════════════════════════════════════════ QLineEdit */
QLineEdit {
    background-color: #1a1d27;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 9px 14px;
    min-height: 22px;
    color: #e8ecf4;
    selection-background-color: #5b8af0;
    selection-color: #ffffff;
}
QLineEdit:focus {
    border: 1px solid rgba(91,138,240,0.65);
    background-color: #1e2130;
}
QLineEdit:hover {
    border: 1px solid rgba(255,255,255,0.15);
}
QLineEdit[readOnly="true"] {
    color: #8892a8;
}

/* ══════════════════════════════════════════════════════════════════ QTextEdit */
QTextEdit {
    background-color: #1a1d27;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 8px 12px;
    color: #e8ecf4;
    selection-background-color: #5b8af0;
    selection-color: #ffffff;
}
QTextEdit:focus {
    border: 1px solid rgba(91,138,240,0.65);
}

/* ══════════════════════════════════════════════════════════════════ QComboBox */
QComboBox {
    background-color: #1a1d27;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 8px 14px;
    color: #e8ecf4;
    min-height: 22px;
}
QComboBox:focus, QComboBox:on {
    border: 1px solid rgba(91,138,240,0.65);
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e2130;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 8px;
    color: #e8ecf4;
    selection-background-color: #252839;
}

/* ════════════════════════════════════════════════════════════ PRIMARY BUTTON */
QPushButton {
    background-color: #5b8af0;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #6b97f2;
}
QPushButton:pressed {
    background-color: #3d64c8;
}
QPushButton:disabled {
    background-color: rgba(91,138,240,0.18);
    color: rgba(232,236,244,0.35);
}

/* ═══════════════════════════════════════════════════════ SECONDARY/GHOST BTN */
QPushButton#secondaryButton, QPushButton#greyButton {
    background-color: rgba(255,255,255,0.06);
    color: #8892a8;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
}
QPushButton#secondaryButton:hover, QPushButton#greyButton:hover {
    background-color: rgba(255,255,255,0.10);
    color: #e8ecf4;
    border-color: rgba(255,255,255,0.16);
}
QPushButton#secondaryButton:pressed, QPushButton#greyButton:pressed {
    background-color: rgba(255,255,255,0.04);
}

/* ═══════════════════════════════════════════════════════════════ DANGER BTN */
QPushButton#dangerButton {
    background-color: rgba(248,113,113,0.10);
    color: #f87171;
    border: 1px solid rgba(248,113,113,0.25);
    border-radius: 10px;
}
QPushButton#dangerButton:hover {
    background-color: rgba(248,113,113,0.20);
    border-color: rgba(248,113,113,0.45);
}

/* ══════════════════════════════════════════════════════════════ ICON BUTTON */
QPushButton#iconButton {
    background-color: transparent;
    color: #8892a8;
    border: none;
    border-radius: 20px;
    padding: 0px;
    min-width: 36px;
    min-height: 36px;
}
QPushButton#iconButton:hover {
    background-color: rgba(91,138,240,0.14);
    color: #e8ecf4;
}
QPushButton#iconButton:pressed {
    background-color: rgba(91,138,240,0.24);
}

/* ══════════════════════════════════════════════════════════ CONTROL BUTTONS */
QPushButton#controlButton {
    background-color: rgba(255,255,255,0.08);
    color: #e8ecf4;
    border: none;
    border-radius: 24px;
    padding: 0px;
}
QPushButton#controlButton:hover {
    background-color: rgba(255,255,255,0.14);
}
QPushButton#controlButton:checked {
    background-color: rgba(91,138,240,0.25);
    color: #5b8af0;
}
QPushButton#dangerControlButton {
    background-color: #f87171;
    color: #ffffff;
    border: none;
    border-radius: 24px;
    padding: 0px;
}
QPushButton#dangerControlButton:hover { background-color: #ef4444; }
QPushButton#dangerControlButton:pressed { background-color: #dc2626; }

/* ════════════════════════════════════════════════════════════ TRANSPARENT BTN */
QPushButton#transparentButton {
    background-color: transparent;
    color: #8892a8;
    border: none;
    padding: 6px 10px;
    text-align: left;
    border-radius: 8px;
}
QPushButton#transparentButton:hover {
    background-color: rgba(255,255,255,0.06);
    color: #e8ecf4;
}

/* ══════════════════════════════════════════════════════════════ LIST WIDGET */
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-radius: 10px;
    color: #e8ecf4;
    margin: 1px 0px;
}
QListWidget::item:hover { background-color: rgba(255,255,255,0.05); }
QListWidget::item:selected {
    background-color: rgba(91,138,240,0.18);
    color: #ffffff;
    border-left: 2px solid #5b8af0;
}

/* ══════════════════════════════════════════════════════════════ SCROLL BARS */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 5px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: rgba(91,138,240,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 5px;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover { background: rgba(91,138,240,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ══════════════════════════════════════════════════════════ PROGRESS BARS */
QProgressBar {
    background-color: rgba(255,255,255,0.07);
    border-radius: 6px;
    text-align: center;
    color: #e8ecf4;
    font-size: 12px;
    border: none;
    min-height: 8px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #5b8af0, stop:1 #7c9ff4);
    border-radius: 6px;
}

/* ════════════════════════════════════════════════════ CHECK BOX / RADIO BTN */
QCheckBox {
    spacing: 8px;
    color: #8892a8;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid rgba(255,255,255,0.18);
    background-color: #1a1d27;
}
QCheckBox::indicator:checked {
    background-color: #5b8af0;
    border-color: #5b8af0;
    image: url(none);
}
QCheckBox::indicator:hover {
    border-color: rgba(91,138,240,0.60);
}

/* ══════════════════════════════════════════════════════════════════ TOOLTIPS */
QToolTip {
    background-color: #252839;
    color: #e8ecf4;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ══════════════════════════════════════════════════════════ MESSAGE BOXES */
QMessageBox {
    background-color: #13151c;
}
QMessageBox QLabel { color: #e8ecf4; }
QMessageBox QPushButton {
    min-width: 80px;
    padding: 7px 16px;
}

/* ═══════════════════════════════════════════════════════════════════ MENUS */
QMenu {
    background-color: #1e2130;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 4px;
}
QMenu::item {
    padding: 7px 18px;
    border-radius: 6px;
    color: #e8ecf4;
}
QMenu::item:selected { background-color: rgba(91,138,240,0.18); }
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.07);
    margin: 3px 10px;
}

/* ══════════════════════════════════════════════════════════════ SCROLL AREA */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ═════════════════════════════════════════════════ TAB WIDGET (room panels) */
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #8892a8;
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}
QTabBar::tab:selected {
    color: #5b8af0;
    border-bottom: 2px solid #5b8af0;
    font-weight: 600;
}
QTabBar::tab:hover { color: #e8ecf4; }
'''


# ─── Light variant (slightly brightened surfaces, same accent) ───────────────
LIGHT_STYLESHEET = '''
* {
    font-family: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
    font-size: 14px;
    color: #e8ecf4;
    outline: none;
}
QMainWindow, FramelessWindow, TailChatMainWindow { background-color: #111318; }
QDialog { background-color: #181b24; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; }
QStackedWidget { background: transparent; }
QWidget { background: transparent; color: #e8ecf4; }
QWidget#leftPanel, SidebarWidget { background-color: #1a1d26; border-right: 1px solid rgba(255,255,255,0.06); }

QLabel { color: #e8ecf4; background: transparent; }
QLabel#titleLabel { font-size: 30px; font-weight: 700; color: #ffffff; }
QLabel#subtitleLabel { font-size: 13px; color: #7a84a0; }

QLineEdit, QTextEdit, QComboBox {
    background-color: #1e2130;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 9px 14px;
    color: #e8ecf4;
    selection-background-color: #5b8af0;
}
QLineEdit:focus, QTextEdit:focus { border: 1px solid rgba(91,138,240,0.65); }

QPushButton {
    background-color: #5b8af0; color: #ffffff;
    border: none; border-radius: 10px;
    padding: 9px 20px; font-weight: 600;
}
QPushButton:hover { background-color: #6b97f2; }
QPushButton:pressed { background-color: #3d64c8; }
QPushButton:disabled { background-color: rgba(91,138,240,0.18); color: rgba(255,255,255,0.35); }

QPushButton#secondaryButton, QPushButton#greyButton {
    background-color: rgba(255,255,255,0.08); color: #8892a8;
    border: 1px solid rgba(255,255,255,0.10);
}
QPushButton#secondaryButton:hover, QPushButton#greyButton:hover {
    background-color: rgba(255,255,255,0.12); color: #e8ecf4;
}

QPushButton#dangerButton {
    background-color: rgba(248,113,113,0.10); color: #f87171;
    border: 1px solid rgba(248,113,113,0.25);
}
QPushButton#dangerButton:hover { background-color: rgba(248,113,113,0.20); }

QPushButton#controlButton { background-color: rgba(255,255,255,0.09); color: #e8ecf4; border: none; border-radius: 24px; }
QPushButton#controlButton:hover { background-color: rgba(255,255,255,0.15); }
QPushButton#dangerControlButton { background-color: #f87171; color: #fff; border: none; border-radius: 24px; }
QPushButton#dangerControlButton:hover { background-color: #ef4444; }

QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 10px 14px; border-radius: 10px; color: #e8ecf4; margin: 1px 0; }
QListWidget::item:hover { background-color: rgba(255,255,255,0.06); }
QListWidget::item:selected { background-color: rgba(91,138,240,0.20); border-left: 2px solid #5b8af0; }

QScrollBar:vertical { border: none; background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.14); border-radius: 3px; }
QScrollBar::handle:vertical:hover { background: rgba(91,138,240,0.55); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QProgressBar { background: rgba(255,255,255,0.07); border-radius: 6px; text-align: center; color: #e8ecf4; min-height: 8px; max-height: 8px; border: none; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #5b8af0, stop:1 #7c9ff4); border-radius: 6px; }

QToolTip { background-color: #252839; color: #e8ecf4; border: 1px solid rgba(255,255,255,0.10); border-radius: 8px; padding: 5px 10px; }
QMessageBox { background-color: #181b24; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
'''
