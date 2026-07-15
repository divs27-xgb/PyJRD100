from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QLineEdit, QComboBox, QFormLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.worker import Worker


class ReadPanel(QWidget):
    """Panel for reading tag memory areas."""

    log = pyqtSignal(str, str)
    tag_received = pyqtSignal(dict)

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

        group = QGroupBox("Read Tag Memory")
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

        self._length_input = QLineEdit("2")
        self._length_input.setPlaceholderText("Word count (default 2)")
        self._length_input.setStyleSheet(self._input_style())
        form.addRow("Data Length:", self._length_input)

        read_btn = QPushButton("Read Tag")
        read_btn.clicked.connect(self._read_tag)
        form.addRow(read_btn)

        layout.addWidget(group)

        # Result display
        result_group = QGroupBox("Result")
        result_group.setStyleSheet(self._group_style())
        rg_layout = QVBoxLayout(result_group)

        self._result_label = QLabel("No data yet")
        self._result_label.setStyleSheet("color: #888;")
        self._result_label.setWordWrap(True)
        self._result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rg_layout.addWidget(self._result_label)

        layout.addWidget(result_group)
        layout.addStretch()

    def _read_tag(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        epc = self._epc_input.text().strip()
        if not epc:
            self.log.emit("ERROR", "EPC is required")
            return

        membank = self._bank_combo.currentIndex()
        password = self._password_input.text().strip() or "00 00 00 00"
        try:
            offset = int(self._offset_input.text().strip() or "0")
            length = int(self._length_input.text().strip() or "2")
        except ValueError:
            self.log.emit("ERROR", "Offset and length must be integers")
            return

        def do_read():
            return self._reader.readTagMemoryArea(
                epc=epc, membank=membank,
                access_password=password,
                start_offset=offset, data_length=length,
            )

        def on_result(result):
            if result:
                text = (
                    f"PC: 0x{result['pc']:04X}  |  EPC: {result['EPC']}  |  "
                    f"Size: {result['EPCsize']} bytes  |  Data: {result['data']}"
                )
                self._result_label.setText(text)
                self._result_label.setStyleSheet("color: #4ec9b0;")
                self.log.emit("RX", f"Read OK: data={result['data']}")
                self.tag_received.emit({
                    "epc": result["EPC"].replace(" ", ""),
                    "pc": f"0x{result['pc']:04X}",
                    "data": result["data"],
                })
            else:
                self._result_label.setText("No response or error")
                self._result_label.setStyleSheet("color: #f44747;")
                self.log.emit("ERROR", "readTagMemoryArea: no response")

        def on_error(msg):
            self._result_label.setText(f"Error: {msg}")
            self._result_label.setStyleSheet("color: #f44747;")
            self.log.emit("ERROR", f"readTagMemoryArea: {msg}")

        self._result_label.setText("Reading...")
        self._result_label.setStyleSheet("color: #cccccc;")

        w = Worker(do_read)
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
