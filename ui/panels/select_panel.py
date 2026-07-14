from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QLineEdit, QComboBox, QFormLayout,
)
from PyQt6.QtCore import pyqtSignal

from ui.worker import Worker


class SelectPanel(QWidget):
    """Panel for getting/setting select parameters and select mode."""

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

        # Get select params
        get_group = QGroupBox("Current Select Parameters")
        get_group.setStyleSheet(self._group_style())
        gg_layout = QVBoxLayout(get_group)

        self._param_display = QLabel("Click 'Get' to query current parameters")
        self._param_display.setStyleSheet("color: #888;")
        self._param_display.setWordWrap(True)
        gg_layout.addWidget(self._param_display)

        get_row = QHBoxLayout()
        get_row.addStretch()
        get_btn = QPushButton("Get Select Params")
        get_btn.setFixedWidth(150)
        get_btn.clicked.connect(self._get_params)
        get_row.addWidget(get_btn)
        gg_layout.addLayout(get_row)
        layout.addWidget(get_group)

        # Set select params
        set_group = QGroupBox("Set Select Parameters")
        set_group.setStyleSheet(self._group_style())
        sg_layout = QFormLayout(set_group)

        self._mask_input = QLineEdit()
        self._mask_input.setPlaceholderText("Hex EPC/data, e.g. E20047055EE068232912010D")
        self._mask_input.setStyleSheet(self._input_style())
        sg_layout.addRow("Mask:", self._mask_input)

        self._membank_combo = QComboBox()
        self._membank_combo.addItems(["0 - RFU", "1 - EPC", "2 - TID", "3 - User"])
        self._membank_combo.setCurrentIndex(1)
        self._membank_combo.setStyleSheet(self._input_style())
        sg_layout.addRow("Memory Bank:", self._membank_combo)

        self._ptr_input = QLineEdit("00000020")
        self._ptr_input.setPlaceholderText("Hex pointer (default 0x20)")
        self._ptr_input.setStyleSheet(self._input_style())
        sg_layout.addRow("Pointer:", self._ptr_input)

        self._target_combo = QComboBox()
        self._target_combo.addItems([f"{i}" for i in range(8)])
        self._target_combo.setStyleSheet(self._input_style())
        sg_layout.addRow("Target:", self._target_combo)

        self._action_combo = QComboBox()
        self._action_combo.addItems([f"{i}" for i in range(8)])
        self._action_combo.setStyleSheet(self._input_style())
        sg_layout.addRow("Action:", self._action_combo)

        self._truncate_combo = QComboBox()
        self._truncate_combo.addItems(["0 - Disabled", "1 - Enabled"])
        self._truncate_combo.setStyleSheet(self._input_style())
        sg_layout.addRow("Truncate:", self._truncate_combo)

        set_btn = QPushButton("Apply Select Params")
        set_btn.clicked.connect(self._set_params)
        sg_layout.addRow(set_btn)

        layout.addWidget(set_group)

        # Select mode
        mode_group = QGroupBox("Select Mode")
        mode_group.setStyleSheet(self._group_style())
        mode_layout = QHBoxLayout(mode_group)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "0 - Send before every operation",
            "1 - Cancel select (no select)",
            "2 - Send before non-poll operations",
        ])
        self._mode_combo.setStyleSheet(self._input_style())
        mode_layout.addWidget(self._mode_combo, 1)

        mode_btn = QPushButton("Apply Mode")
        mode_btn.setFixedWidth(120)
        mode_btn.clicked.connect(self._set_mode)
        mode_layout.addWidget(mode_btn)
        layout.addWidget(mode_group)

        layout.addStretch()

    def _get_params(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        def do_get():
            return self._reader.getSelectParam()

        def on_result(result):
            if result:
                text = (
                    f"Target: {result['target']}  |  Action: {result['action']}  |  "
                    f"Bank: {result['membank']}  |  Ptr: 0x{result['ptr']:08X}  |  "
                    f"Mask len: {result['mask_len_bits']} bits  |  Truncate: {result['truncate']}  |  "
                    f"Mask: {result['mask']}"
                )
                self._param_display.setText(text)
                self._param_display.setStyleSheet("color: #4ec9b0;")
                self.log.emit("RX", f"SelectParams: {result}")
            else:
                self._param_display.setText("No response")
                self._param_display.setStyleSheet("color: #f44747;")

        def on_error(msg):
            self._param_display.setText(f"Error: {msg}")
            self._param_display.setStyleSheet("color: #f44747;")
            self.log.emit("ERROR", f"getSelectParam: {msg}")

        w = Worker(do_get)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _set_params(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        mask = self._mask_input.text().strip()
        if not mask:
            self.log.emit("ERROR", "Mask is required")
            return

        membank = self._membank_combo.currentIndex()
        try:
            ptr = int(self._ptr_input.text().strip(), 16)
        except ValueError:
            self.log.emit("ERROR", "Invalid pointer value")
            return
        target = self._target_combo.currentIndex()
        action = self._action_combo.currentIndex()
        truncate = 0x80 if self._truncate_combo.currentIndex() == 1 else 0x00

        def do_set():
            self._reader.setSelectParam(
                mask=mask, membank=membank, ptr=ptr,
                target=target, action=action, truncate=truncate,
            )

        def on_result(_):
            self.log.emit("TX", f"Select params set: mask={mask}, bank={membank}")

        def on_error(msg):
            self.log.emit("ERROR", f"setSelectParam: {msg}")

        w = Worker(do_set)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _set_mode(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        mode = self._mode_combo.currentIndex()

        def do_set():
            self._reader.setSelectMode(mode=mode)

        def on_result(_):
            self.log.emit("TX", f"Select mode set to {mode}")

        def on_error(msg):
            self.log.emit("ERROR", f"setSelectMode: {msg}")

        w = Worker(do_set)
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
