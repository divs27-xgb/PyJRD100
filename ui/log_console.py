from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel


class LogConsole(QWidget):
    """Colored, timestamped log panel for TX / RX / ERROR / INFO messages."""

    COLORS = {
        "TX": "#569cd6",
        "RX": "#6a9955",
        "ERROR": "#f44747",
        "INFO": "#808080",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = QLabel("Log Console")
        title.setStyleSheet("font-weight: bold; color: #cccccc;")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 9))
        self._text.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #cccccc; "
            "border: 1px solid #333; }"
        )
        layout.addWidget(self._text)

    def log(self, direction, message):
        """Append a log entry.

        Args:
            direction: One of 'TX', 'RX', 'ERROR', 'INFO'
            message: The log message text
        """
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = self.COLORS.get(direction, self.COLORS["INFO"])

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontFamily("Consolas")
        fmt.setFontPointSize(9)

        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"[{ts}] {direction}: {message}\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self):
        self._text.clear()
