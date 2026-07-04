# ──────────────────────────────────────────────────────────────────────────────
#  TailChat — Dracula-Inspired Premium Dark UI
#
#  Palette (derived from official Dracula spec + custom depth layers):
#
#    bg-deepest:   #121212   Pure black near-black     — root canvas
#    bg-base:      #121212   Pure black surface           — primary surface
#    bg-panel:     #121212   Pure black panels / sidebar  — side surfaces
#    bg-card:      #252526   Cards / inputs              — elevated cards
#    bg-elevated:  #2D2D30   Hover / selected states     — subtle elevation
#    bg-subtle:    rgba(17,18,24,0.50)                  — ghost bg
#
#    accent:       #8B5CF6   Discord 'blurple' ← primary brand colour
#    accent-dim:   #7C3AED   pressed / darker accent
#    accent-glow:  rgba(139,92,246,0.16)
#    pink:         #FF79C6   Accent pink for highlights
#    cyan:         #8BE9FD   Info badges and links
#    green:        #50FA7B   Success / online
#    amber:        #FFB86C   Warnings
#    red:          #FF5555   Errors / danger
#
#    text-1:       #F8F8F2   Primary text — bright on dark
#    text-2:       #98A0C6   Secondary / muted text
#    text-3:       #2D2D30   Very muted / placeholder
#    border:       rgba(80,86,120,0.20)
#    border-hover: rgba(139,92,246,0.40)
# ──────────────────────────────────────────────────────────────────────────────

DARK_STYLESHEET = '''
/* ═══════════════════════════════════════════════════════════════════ GLOBAL */
* {
    font-family: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
    font-size: 14px;
    color: #F8F8F2;
    outline: none;
}

/* ═══════════════════════════════════════════════════════════ BASE CONTAINERS */
QMainWindow, FramelessWindow, TailChatMainWindow {
    background-color: #121212;
}
QDialog {
    background-color: #121212;
    border: 1px solid rgba(80,86,120,0.22);
    border-radius: 16px;
}
QStackedWidget { background: transparent; }
QWidget { background: transparent; color: #F8F8F2; }

/* ══════════════════════════════════════════════════════════════════ SIDEBAR */
QWidget#leftPanel, SidebarWidget {
    background-color: #121212;
    border-right: 1px solid rgba(80,86,120,0.12);
}

/* ══════════════════════════════════════════════════════════════════ SPLITTER */
QSplitter::handle { background: transparent; width: 1px; }
QSplitter::handle:horizontal { border-left: 1px solid rgba(80,86,120,0.12); }
QSplitter::handle:vertical   { border-top:  1px solid rgba(80,86,120,0.12); }

/* ═══════════════════════════════════════════════════════════════════ LABELS */
QLabel { color: #F8F8F2; background: transparent; }
QLabel#titleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #F8F8F2;
    letter-spacing: -0.5px;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #6272A4;
}
QLabel#sectionLabel {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #2D2D30;
    text-transform: uppercase;
}

/* ═══════════════════════════════════════════════════════════ SEPARATOR LINE */
QFrame#separatorLine {
    background-color: rgba(80,86,120,0.18);
    max-height: 1px;
    min-height: 1px;
    border: none;
}
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    background-color: rgba(80,86,120,0.18);
    border: none;
    max-height: 1px;
}

/* ══════════════════════════════════════════════════════════════ INPUT FIELDS */
QLineEdit {
    background-color: #1E1E1E;
    border: 1px solid rgba(80,86,120,0.30);
    border-radius: 10px;
    padding: 9px 14px;
    min-height: 22px;
    color: #F8F8F2;
    selection-background-color: #8B5CF6;
    selection-color: #121212;
}
QLineEdit:focus {
    border: 1px solid rgba(139,92,246,0.85);
    background-color: #252526;
}
QLineEdit:hover {
    border: 1px solid rgba(80,86,120,0.55);
}
QLineEdit[readOnly="true"] { color: #6272A4; }

QTextEdit {
    background-color: #1E1E1E;
    border: 1px solid rgba(80,86,120,0.30);
    border-radius: 10px;
    padding: 8px 12px;
    color: #F8F8F2;
    selection-background-color: #8B5CF6;
    selection-color: #121212;
}
QTextEdit:focus { border: 1px solid rgba(139,92,246,0.85); }

QComboBox {
    background-color: #1E1E1E;
    border: 1px solid rgba(80,86,120,0.30);
    border-radius: 10px;
    padding: 8px 14px;
    color: #F8F8F2;
    min-height: 22px;
}
QComboBox:focus, QComboBox:on {
    border: 1px solid rgba(139,92,246,0.85);
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #1E1E1E;
    border: 1px solid rgba(80,86,120,0.30);
    border-radius: 8px;
    color: #F8F8F2;
    selection-background-color: #2D2D30;
}

/* ══════════════════════════════════════════════════════════ PRIMARY BUTTON */
QPushButton {
    background-color: #8B5CF6;
    color: #F8F8F2;
    border: none;
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton:hover { background-color: #7C3AED; }
QPushButton:pressed { background-color: #6D28D9; }
QPushButton:disabled {
    background-color: rgba(139,92,246,0.16);
    color: rgba(248,248,242,0.35);
}

/* ════════════════════════════════════════════════ SECONDARY / GHOST BUTTON */
QPushButton#secondaryButton, QPushButton#greyButton {
    background-color: rgba(80,86,120,0.12);
    color: #98A0C6;
    border: 1px solid rgba(80,86,120,0.20);
    border-radius: 10px;
}
QPushButton#secondaryButton:hover, QPushButton#greyButton:hover {
    background-color: rgba(80,86,120,0.20);
    color: #F8F8F2;
    border-color: rgba(139,92,246,0.28);
}
QPushButton#secondaryButton:pressed, QPushButton#greyButton:pressed {
    background-color: rgba(80,86,120,0.08);
}

/* ════════════════════════════════════════════════════════════ DANGER BUTTON */
QPushButton#dangerButton {
    background-color: rgba(255,85,85,0.12);
    color: #FF5555;
    border: 1px solid rgba(255,85,85,0.28);
    border-radius: 10px;
}
QPushButton#dangerButton:hover {
    background-color: rgba(255,85,85,0.22);
    border-color: rgba(255,85,85,0.50);
}

/* ════════════════════════════════════════════════════════════ ICON BUTTON */
QPushButton#iconButton {
    background-color: transparent;
    color: #6272A4;
    border: none;
    border-radius: 20px;
    padding: 0px;
    min-width: 36px;
    min-height: 36px;
}
QPushButton#iconButton:hover {
    background-color: rgba(139,92,246,0.12);
    color: #F8F8F2;
}
QPushButton#iconButton:pressed {
    background-color: rgba(139,92,246,0.22);
}

/* ═════════════════════════════════════════════════ TRANSPARENT NAV BUTTON */
QPushButton#transparentButton {
    background: transparent;
    color: #6272A4;
    border: none;
    padding: 0px 12px;
    text-align: left;
    border-radius: 10px;
}
QPushButton#transparentButton:hover {
    background-color: rgba(80,86,120,0.12);
    color: #F8F8F2;
}
QPushButton#transparentButton:pressed {
    background-color: rgba(139,92,246,0.14);
    color: #8B5CF6;
}

/* ════════════════════════════════════════════════════════ CONTROL BUTTONS */
QPushButton#controlButton {
    background-color: rgba(68,71,90,0.70);
    color: #F8F8F2;
    border: none;
    border-radius: 24px;
    padding: 0px;
}
QPushButton#controlButton:hover { background-color: #2D2D30; }
QPushButton#controlButton:checked {
    background-color: rgba(139,92,246,0.20);
    color: #8B5CF6;
}

QPushButton#dangerControlButton {
    background-color: #FF5555;
    color: #F8F8F2;
    border: none;
    border-radius: 24px;
    padding: 0px;
}
QPushButton#dangerControlButton:hover { background-color: #e04444; }
QPushButton#dangerControlButton:pressed { background-color: #c43333; }

/* ═══════════════════════════════════════════════════════════ LIST WIDGET */
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 10px 14px;
    border-radius: 10px;
    color: #F8F8F2;
    margin: 1px 0px;
}
QListWidget::item:hover { background-color: rgba(17,18,24,0.55); }
QListWidget::item:selected {
    background-color: rgba(139,92,246,0.18);
    color: #F8F8F2;
    border-left: 2px solid #8B5CF6;
}

/* ═════════════════════════════════════════════════════════ SCROLL BARS */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 5px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: rgba(80,86,120,0.30);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: rgba(139,92,246,0.55); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 5px;
}
QScrollBar::handle:horizontal {
    background: rgba(80,86,120,0.30);
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover { background: rgba(139,92,246,0.55); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ══════════════════════════════════════════════════════════ PROGRESS BAR */
QProgressBar {
    background-color: rgba(68,71,90,0.50);
    border-radius: 6px;
    text-align: center;
    color: #F8F8F2;
    font-size: 12px;
    border: none;
    min-height: 8px;
    max-height: 8px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #8B5CF6, stop:1 #A78BFA);
    border-radius: 6px;
}

/* ═══════════════════════════════════════════════════════ CHECK BOX */
QCheckBox {
    spacing: 8px;
    color: #6272A4;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid rgba(80,86,120,0.45);
    background-color: #1E1E1E;
}
QCheckBox::indicator:checked {
    background-color: #8B5CF6;
    border-color: #8B5CF6;
}
QCheckBox::indicator:hover { border-color: rgba(139,92,246,0.70); }

/* ══════════════════════════════════════════════════════════════ TOOLTIP */
QToolTip {
    background-color: #252526;
    color: #F8F8F2;
    border: 1px solid rgba(139,92,246,0.30);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ═══════════════════════════════════════════════════════ MESSAGE BOXES */
QMessageBox { background-color: #121212; }
QMessageBox QLabel { color: #F8F8F2; }
QMessageBox QPushButton { min-width: 80px; padding: 7px 16px; }

/* ═══════════════════════════════════════════════════════════════ MENUS */
QMenu {
    background-color: #1E1E1E;
    border: 1px solid rgba(80,86,120,0.26);
    border-radius: 10px;
    padding: 4px;
}
QMenu::item {
    padding: 7px 18px;
    border-radius: 6px;
    color: #F8F8F2;
}
QMenu::item:selected { background-color: rgba(139,92,246,0.20); }
QMenu::separator {
    height: 1px;
    background: rgba(80,86,120,0.18);
    margin: 3px 10px;
}

/* ══════════════════════════════════════════════════════════ SCROLL AREA */
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ═══════════════════════════════════════════════════════════ TAB WIDGET */
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #6272A4;
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}
QTabBar::tab:selected {
    color: #8B5CF6;
    border-bottom: 2px solid #8B5CF6;
    font-weight: 600;
}
QTabBar::tab:hover { color: #F8F8F2; }
'''

# ── Light variant (same hue family, slightly brighter surfaces) ───────────────
LIGHT_STYLESHEET = DARK_STYLESHEET  # ship one great dark theme only
