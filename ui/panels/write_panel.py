from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QLineEdit, QComboBox, QFormLayout, QPlainTextEdit,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.worker import Worker


class WritePanel(QWidget):
    """Panel for writing data to tag memory areas."""

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

        group = QGroupBox("Write Tag Memory")
        group.setStyleSheet(self._group_style())
        form = QFormLayout(group)

        self._epc_input = QLineEdit()
        self._epc_input.setPlaceholderText("Hex EPC, e.g. E20047055EE068232912010D")
        self._epc_input.setStyleSheet(self._input_style())
        form.addRow("EPC:", self._epc_input)

        self._bank_combo = QComboBox()
        self._bank_combo.addItems(["0 - RFU", "1 - EPC", "2 - TID", "3 - User"])
        self._bank_combo.setCurrentIndex(1)
        self._bank_combo.setStyleSheet(self._input_style())
        form.addRow("Memory Bank:", self._bank_combo)

        self._password_input = QLineEdit("00 00 00 00")
        self._password_input.setPlaceholderText("Hex password (default 00 00 00 00)")
        self._password_input.setStyleSheet(self._input_style())
        form.addRow("Access Password:", self._password_input)

        self._offset_input = QLineEdit("0")
        self._offset_input.setPlaceholderText("Word offset (default 0)")
        self._offset_input.setStyleSheet(self._input_style())
        form.addRow("Start Offset:", self._offset_input)

        self._data_input = QPlainTextEdit()
        self._data_input.setPlaceholderText("Hex data (spaces optional), e.g. A002 or A0 02")
        self._data_input.setMaximumHeight(80)
        self._data_input.setStyleSheet(
            "QPlainTextEdit { background-color: #2d2d2d; color: #cccccc; "
            "border: 1px solid #555; padding: 4px; font-family: Consolas; }"
        )
        form.addRow("Data:", self._data_input)

        write_btn = QPushButton("Write Tag")
        write_btn.clicked.connect(self._write_tag)
        form.addRow(write_btn)

        layout.addWidget(group)

        # Status
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _write_tag(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        epc = self._epc_input.text().strip()
        data = self._data_input.toPlainText().strip()
        if not epc or not data:
            self.log.emit("ERROR", "EPC and data are required")
            return

        membank = self._bank_combo.currentIndex()
        password = self._password_input.text().strip() or "00 00 00 00"
        try:
            offset = int(self._offset_input.text().strip() or "0")
        except ValueError:
            self.log.emit("ERROR", "Offset must be an integer")
            return

        def do_write():
            return self._reader.writeTagMemoryArea(
                epc=epc, data=data, membank=membank,
                access_password=password, start_offset=offset,
            )

        def on_result(result):
            if result:
                self._status_label.setText("Write successful!")
                self._status_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
                self.log.emit("TX", f"Write OK to EPC={epc}, bank={membank}")
            else:
                self._status_label.setText("Write failed (no response)")
                self._status_label.setStyleSheet("color: #f44747;")
                self.log.emit("ERROR", "writeTagMemoryArea: no response")

        def on_error(msg):
            self._status_label.setText(f"Error: {msg}")
            self._status_label.setStyleSheet("color: #f44747;")
            self.log.emit("ERROR", f"writeTagMemoryArea: {msg}")

        self._status_label.setText("Writing...")
        self._status_label.setStyleSheet("color: #cccccc;")

        w = Worker(do_write)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _group_style(self):
        return (
            "QGroupBox { color: #cccccc; border: 1px solid #444; border-radius: 6px; "
            "margin-top: 10px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }"
        )

    def _input_style(self):
        return (
            "QLineEdit, QComboBox { background-color: #2d2d2d; color: #cccccc; "
            "border: 1px solid #555; padding: 4px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #2d2d2d; color: #cccccc; }"
        )
