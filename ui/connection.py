import serial.tools.list_ports

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QPushButton, QLabel, QCheckBox,
)


class ConnectionBar(QWidget):
    """Top toolbar for COM port selection, connect/disconnect, and auto-reconnect."""

    reader_connected = pyqtSignal(object)  # emits the reader instance
    reader_disconnected = pyqtSignal()
    log_message = pyqtSignal(str, str)  # direction, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._auto_reconnect_enabled = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._setup_ui()
        self._setup_auto_reconnect()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        port_label = QLabel("Port:")
        port_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(port_label)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(120)
        self._port_combo.setStyleSheet(
            "QComboBox { background-color: #2d2d2d; color: #cccccc; border: 1px solid #555; padding: 4px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #2d2d2d; color: #cccccc; }"
        )
        layout.addWidget(self._port_combo)

        refresh_btn = QPushButton("\u21bb")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Refresh ports")
        refresh_btn.clicked.connect(self._refresh_ports)
        layout.addWidget(refresh_btn)

        baud_label = QLabel("Baud:")
        baud_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(baud_label)

        self._baud_combo = QComboBox()
        self._baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self._baud_combo.setCurrentText("115200")
        self._baud_combo.setStyleSheet(self._port_combo.styleSheet())
        layout.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setStyleSheet(
            "QPushButton { background-color: #0e639c; color: white; border: none; "
            "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1177bb; }"
        )
        self._connect_btn.clicked.connect(self._toggle_connection)
        layout.addWidget(self._connect_btn)

        self._status_label = QLabel("\u25cf Disconnected")
        self._status_label.setStyleSheet("color: #f44747; font-weight: bold;")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._auto_reconnect_cb = QCheckBox("Auto-reconnect")
        self._auto_reconnect_cb.setChecked(True)
        self._auto_reconnect_cb.setStyleSheet("color: #cccccc;")
        self._auto_reconnect_cb.toggled.connect(self._on_auto_reconnect_toggled)
        layout.addWidget(self._auto_reconnect_cb)

        self._debug_cb = QCheckBox("Debug")
        self._debug_cb.setChecked(False)
        self._debug_cb.setStyleSheet("color: #cccccc;")
        self._debug_cb.toggled.connect(self._on_debug_toggled)
        layout.addWidget(self._debug_cb)

        self._refresh_ports()

    def _setup_auto_reconnect(self):
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.timeout.connect(self._check_connection)
        self._reconnect_timer.start(5000)

    def _refresh_ports(self):
        self._port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in sorted(ports):
            self._port_combo.addItem(p.device)

    def _toggle_connection(self):
        if self._reader is not None:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_combo.currentText()
        baud = int(self._baud_combo.currentText())
        if not port:
            self.log_message.emit("ERROR", "No port selected")
            return

        self.log_message.emit("INFO", f"Connecting to {port} @ {baud}...")
        try:
            from JRD100 import reader
            self._reader = reader(port=port, baud_rate=baud)
            self._reconnect_attempts = 0
            if self._debug_cb.isChecked():
                self._reader.debug = True
                self._reader.debug_callback = self._debug_log
            self._set_connected_state(True)
            self.log_message.emit("INFO", f"Connected to {port}")
            self.reader_connected.emit(self._reader)
        except Exception as e:
            self._reader = None
            self.log_message.emit("ERROR", f"Connection failed: {e}")

    def _disconnect(self):
        if self._reader is not None:
            try:
                self._reader._running = False
                self._reader.ser.close()
            except Exception:
                pass
            self._reader = None
        self._set_connected_state(False)
        self.log_message.emit("INFO", "Disconnected")
        self.reader_disconnected.emit()

    def _set_connected_state(self, connected):
        if connected:
            self._connect_btn.setText("Disconnect")
            self._connect_btn.setStyleSheet(
                "QPushButton { background-color: #d74747; color: white; border: none; "
                "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
                "QPushButton:hover { background-color: #e05555; }"
            )
            self._status_label.setText(f"\u25cf Connected to {self._port_combo.currentText()}")
            self._status_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
            self._port_combo.setEnabled(False)
            self._baud_combo.setEnabled(False)
        else:
            self._connect_btn.setText("Connect")
            self._connect_btn.setStyleSheet(
                "QPushButton { background-color: #0e639c; color: white; border: none; "
                "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
                "QPushButton:hover { background-color: #1177bb; }"
            )
            self._status_label.setText("\u25cf Disconnected")
            self._status_label.setStyleSheet("color: #f44747; font-weight: bold;")
            self._port_combo.setEnabled(True)
            self._baud_combo.setEnabled(True)

    def _on_auto_reconnect_toggled(self, checked):
        self._auto_reconnect_enabled = checked

    def _on_debug_toggled(self, checked):
        if self._reader is not None:
            self._reader.debug = checked
            self._reader.debug_callback = self._debug_log if checked else None

    def _debug_log(self, direction, message):
        self.log_message.emit(direction, message)

    def _check_connection(self):
        if not self._auto_reconnect_enabled or self._reader is None:
            return
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self.log_message.emit("ERROR", f"Auto-reconnect failed after {self._max_reconnect_attempts} attempts. Disconnecting.")
            self._disconnect()
            self._reconnect_attempts = 0
            return

        try:
            self._reader.getSoftwareversion()
            self._reconnect_attempts = 0
        except Exception:
            self._reconnect_attempts += 1
            self.log_message.emit("INFO",
                f"Module unresponsive. Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}...")
            self._disconnect()
            import time
            time.sleep(2)
            self._connect()

    @property
    def reader(self):
        return self._reader
