from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.worker import Worker


class VersionPanel(QWidget):
    """Panel for querying module version and manufacturer info."""

    log = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._workers = []
        self._setup_ui()

    def set_reader(self, reader):
        self._reader = reader

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        group = QGroupBox("Module Information")
        group.setStyleSheet(
            "QGroupBox { color: #cccccc; border: 1px solid #444; border-radius: 6px; "
            "margin-top: 10px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }"
        )
        group_layout = QVBoxLayout(group)

        for label, method_name in [
            ("Software Version", "getSoftwareversion"),
            ("Hardware Version", "getHardwareversion"),
            ("Manufacturer", "getManufacturer"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(140)
            lbl.setStyleSheet("color: #cccccc; font-weight: bold;")
            row.addWidget(lbl)

            val_label = QLabel("--")
            val_label.setStyleSheet("color: #4ec9b0;")
            val_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(val_label)

            btn = QPushButton(f"Get {label.split()[0]}")
            btn.setFixedWidth(120)
            btn.clicked.connect(lambda _, m=method_name, v=val_label: self._fetch(m, v))
            row.addWidget(btn)

            group_layout.addLayout(row)

        layout.addWidget(group)
        layout.addStretch()

    def _fetch(self, method_name, value_label):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        def do_fetch():
            return getattr(self._reader, method_name)()

        def on_result(result):
            if result:
                value_label.setText(str(result))
                self.log.emit("RX", f"{method_name} = {result}")
            else:
                value_label.setText("No response")
                self.log.emit("ERROR", f"{method_name}: no response")

        def on_error(msg):
            value_label.setText("Error")
            self.log.emit("ERROR", f"{method_name}: {msg}")

        w = Worker(do_fetch)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()
