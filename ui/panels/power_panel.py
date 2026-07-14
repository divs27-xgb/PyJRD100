from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QSlider, QSpinBox, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.worker import Worker


class PowerPanel(QWidget):
    """Panel for getting and setting the module's transmit power."""

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

        group = QGroupBox("Transmit Power")
        group.setStyleSheet(self._group_style())
        g_layout = QVBoxLayout(group)

        # Get power row
        get_row = QHBoxLayout()
        self._current_power = QLabel("-- dBm")
        self._current_power.setStyleSheet("color: #4ec9b0; font-size: 14px; font-weight: bold;")
        get_row.addWidget(self._current_power)

        get_btn = QPushButton("Get Current Power")
        get_btn.setFixedWidth(140)
        get_btn.clicked.connect(self._get_power)
        get_row.addWidget(get_btn)
        get_row.addStretch()
        g_layout.addLayout(get_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        g_layout.addWidget(sep)

        # Set power row
        set_row = QHBoxLayout()
        set_lbl = QLabel("Set Power:")
        set_lbl.setStyleSheet("color: #cccccc; font-weight: bold;")
        set_row.addWidget(set_lbl)

        self._power_slider = QSlider(Qt.Orientation.Horizontal)
        self._power_slider.setRange(0, 2600)
        self._power_slider.setValue(2500)
        self._power_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #444; height: 6px; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #0e639c; width: 16px; margin: -5px 0; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: #0e639c; border-radius: 3px; }"
        )
        set_row.addWidget(self._power_slider, 1)

        self._power_spin = QSpinBox()
        self._power_spin.setRange(0, 2600)
        self._power_spin.setValue(2500)
        self._power_spin.setSuffix(" dBm")
        self._power_spin.setFixedWidth(100)
        self._power_spin.setStyleSheet(
            "QSpinBox { background-color: #2d2d2d; color: #cccccc; border: 1px solid #555; padding: 4px; }"
        )
        set_row.addWidget(self._power_spin)
        self._power_slider.valueChanged.connect(self._power_spin.setValue)
        self._power_spin.valueChanged.connect(self._power_slider.setValue)

        set_btn = QPushButton("Set Power")
        set_btn.setFixedWidth(100)
        set_btn.clicked.connect(self._set_power)
        set_row.addWidget(set_btn)
        g_layout.addLayout(set_row)

        layout.addWidget(group)
        layout.addStretch()

    def _get_power(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        def do_get():
            return self._reader.getTransmitPower()

        def on_result(result):
            if result is not None:
                self._current_power.setText(f"{result} dBm")
                self.log.emit("RX", f"TX Power = {result} dBm")
            else:
                self._current_power.setText("No response")
                self.log.emit("ERROR", "getTransmitPower: no response")

        def on_error(msg):
            self._current_power.setText("Error")
            self.log.emit("ERROR", f"getTransmitPower: {msg}")

        w = Worker(do_get)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _set_power(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        power = self._power_spin.value()

        def do_set():
            self._reader.setTransmitPower(power=power)

        def on_result(_):
            self.log.emit("TX", f"TX Power set to {power} dBm")
            self._current_power.setText(f"{power} dBm")

        def on_error(msg):
            self.log.emit("ERROR", f"setTransmitPower: {msg}")

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
