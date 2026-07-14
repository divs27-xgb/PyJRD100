from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QStatusBar, QApplication,
)

from ui.connection import ConnectionBar
from ui.log_console import LogConsole
from ui.tag_table import TagTable
from ui.panels.version_panel import VersionPanel
from ui.panels.poll_panel import PollPanel
from ui.panels.power_panel import PowerPanel
from ui.panels.select_panel import SelectPanel
from ui.panels.read_panel import ReadPanel
from ui.panels.write_panel import WritePanel


DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
}
QTabWidget::pane {
    border: 1px solid #333;
    border-radius: 4px;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #cccccc;
    border: 1px solid #444;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #0e639c;
    font-weight: bold;
}
QTabBar::tab:hover {
    background-color: #383838;
}
QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:disabled {
    background-color: #333;
    color: #666;
}
QSplitter::handle {
    background-color: #333;
}
QStatusBar {
    background-color: #252525;
    color: #888;
}
"""


class MainWindow(QMainWindow):
    """Main application window for the JRD100 RFID Dashboard."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JRD100 RFID Manager")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)
        self.setStyleSheet(DARK_STYLESHEET)
        self._reader = None
        self._setup_ui()
        self._wire_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Connection toolbar
        self._conn_bar = ConnectionBar()
        main_layout.addWidget(self._conn_bar)

        # Main splitter: top (tabs + tag table) | bottom (log)
        outer_splitter = QSplitter(Qt.Orientation.Vertical)

        # Top area: tabs | tag table (horizontal split)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setMinimumWidth(380)

        self._version_panel = VersionPanel()
        self._poll_panel = PollPanel()
        self._power_panel = PowerPanel()
        self._select_panel = SelectPanel()
        self._read_panel = ReadPanel()
        self._write_panel = WritePanel()

        self._tabs.addTab(self._version_panel, "Version")
        self._tabs.addTab(self._poll_panel, "Poll")
        self._tabs.addTab(self._power_panel, "Power")
        self._tabs.addTab(self._select_panel, "Select")
        self._tabs.addTab(self._read_panel, "Read")
        self._tabs.addTab(self._write_panel, "Write")

        top_splitter.addWidget(self._tabs)

        # Tag table
        self._tag_table = TagTable()
        top_splitter.addWidget(self._tag_table)
        top_splitter.setStretchFactor(0, 3)
        top_splitter.setStretchFactor(1, 2)

        outer_splitter.addWidget(top_splitter)

        # Log console
        self._log_console = LogConsole()
        self._log_console.setMinimumHeight(120)
        outer_splitter.addWidget(self._log_console)

        outer_splitter.setStretchFactor(0, 3)
        outer_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(outer_splitter, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready -- connect to a reader to begin")

    def _wire_signals(self):
        # Connection bar -> all panels
        self._conn_bar.reader_connected.connect(self._on_reader_connected)
        self._conn_bar.reader_disconnected.connect(self._on_reader_disconnected)
        self._conn_bar.log_message.connect(self._log_console.log)

        # Poll panel -> tag table + log
        self._poll_panel.log.connect(self._log_console.log)
        self._poll_panel.tag_received.connect(self._tag_table.add_tag)

        # Version panel -> log
        self._version_panel.log.connect(self._log_console.log)

        # Power panel -> log
        self._power_panel.log.connect(self._log_console.log)

        # Select panel -> log
        self._select_panel.log.connect(self._log_console.log)

        # Read panel -> tag table + log
        self._read_panel.log.connect(self._log_console.log)
        self._read_panel.tag_received.connect(self._tag_table.add_tag)

        # Write panel -> log
        self._write_panel.log.connect(self._log_console.log)

    def _on_reader_connected(self, reader):
        self._reader = reader
        self._version_panel.set_reader(reader)
        self._poll_panel.set_reader(reader)
        self._power_panel.set_reader(reader)
        self._select_panel.set_reader(reader)
        self._read_panel.set_reader(reader)
        self._write_panel.set_reader(reader)
        self._status_bar.showMessage(f"Connected -- reader ready")

    def _on_reader_disconnected(self):
        self._reader = None
        self._version_panel.set_reader(None)
        self._poll_panel.set_reader(None)
        self._power_panel.set_reader(None)
        self._select_panel.set_reader(None)
        self._read_panel.set_reader(None)
        self._write_panel.set_reader(None)
        self._status_bar.showMessage("Disconnected")
