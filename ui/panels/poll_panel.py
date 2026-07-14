from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QSpinBox, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ui.worker import Worker, StreamWorker


class PollPanel(QWidget):
    """Panel for SinglePoll, MultiPoll, StopPoll, and tag streaming."""

    log = pyqtSignal(str, str)
    tag_received = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._stream_worker = None
        self._workers = []
        self._setup_ui()

    def set_reader(self, reader):
        self._reader = reader

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        single_group = QGroupBox("Single Poll")
        single_group.setStyleSheet(self._group_style())
        sg_layout = QVBoxLayout(single_group)

        single_row = QHBoxLayout()
        self._single_result = QLabel("--")
        self._single_result.setStyleSheet("color: #4ec9b0;")
        self._single_result.setWordWrap(True)
        single_row.addWidget(self._single_result, 1)

        single_btn = QPushButton("Poll Once")
        single_btn.setFixedWidth(100)
        single_btn.clicked.connect(self._single_poll)
        single_row.addWidget(single_btn)
        sg_layout.addLayout(single_row)
        layout.addWidget(single_group)

        multi_group = QGroupBox("Multi Poll / Continuous Scan")
        multi_group.setStyleSheet(self._group_style())
        mg_layout = QVBoxLayout(multi_group)

        poll_count_row = QHBoxLayout()
        poll_lbl = QLabel("Poll count:")
        poll_lbl.setStyleSheet("color: #cccccc;")
        poll_count_row.addWidget(poll_lbl)

        self._poll_count = QSpinBox()
        self._poll_count.setRange(1, 65535)
        self._poll_count.setValue(100)
        self._poll_count.setStyleSheet(
            "QSpinBox { background-color: #2d2d2d; color: #cccccc; border: 1px solid #555; padding: 4px; }"
        )
        poll_count_row.addWidget(self._poll_count)
        poll_count_row.addStretch()
        mg_layout.addLayout(poll_count_row)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Start Multi Poll")
        self._start_btn.setFixedWidth(130)
        self._start_btn.clicked.connect(self._multi_poll)
        btn_row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop Poll")
        self._stop_btn.setFixedWidth(100)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_poll)
        btn_row.addWidget(self._stop_btn)

        self._stream_btn = QPushButton("Start Stream")
        self._stream_btn.setFixedWidth(120)
        self._stream_btn.setCheckable(True)
        self._stream_btn.clicked.connect(self._toggle_stream)
        btn_row.addWidget(self._stream_btn)

        btn_row.addStretch()
        mg_layout.addLayout(btn_row)

        self._stream_status = QLabel("Stream: stopped")
        self._stream_status.setStyleSheet("color: #888;")
        mg_layout.addWidget(self._stream_status)

        layout.addWidget(multi_group)
        layout.addStretch()

    def _single_poll(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        def do_poll():
            return self._reader.SinglePoll()

        def on_result(result):
            if result:
                self._single_result.setText(
                    f"EPC: {result.get('epc', '?')}  |  RSSI: {result.get('rssi', '?')}  |  "
                    f"PC: {result.get('pc', '?')}  |  CRC: {result.get('crc', '?')}"
                )
                self.tag_received.emit(result)
                self.log.emit("RX", f"SinglePoll: EPC={result.get('epc')}")
            else:
                self._single_result.setText("No tag found")
                self.log.emit("INFO", "SinglePoll: no tag in field")

        def on_error(msg):
            self._single_result.setText(f"Error: {msg}")
            self.log.emit("ERROR", f"SinglePoll: {msg}")

        w = Worker(do_poll)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _multi_poll(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            return

        polls = self._poll_count.value()

        def do_poll():
            self._reader.MultiPoll(polls=polls)

        def on_result(_):
            self.log.emit("TX", f"MultiPoll started ({polls} polls)")
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)

        def on_error(msg):
            self.log.emit("ERROR", f"MultiPoll: {msg}")

        w = Worker(do_poll)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _stop_poll(self):
        if not self._reader:
            return

        def do_stop():
            self._reader.StopPoll()

        def on_result(_):
            self.log.emit("TX", "StopPoll sent")
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

        def on_error(msg):
            self.log.emit("ERROR", f"StopPoll: {msg}")

        w = Worker(do_stop)
        w.result_ready.connect(on_result)
        w.error.connect(on_error)
        self._workers.append(w)
        w.start()

    def _toggle_stream(self, checked):
        if checked:
            self._start_stream()
        else:
            self._stop_stream()

    def _start_stream(self):
        if not self._reader:
            self.log.emit("ERROR", "Not connected")
            self._stream_btn.setChecked(False)
            return

        self._stream_worker = StreamWorker(self._reader)
        self._stream_worker.tag_received.connect(self._on_stream_tag)
        self._stream_worker.error.connect(lambda msg: self.log.emit("ERROR", f"Stream: {msg}"))
        self._stream_worker.stopped.connect(self._on_stream_stopped)
        self._stream_worker.start()
        self._stream_status.setText("Stream: running")
        self._stream_status.setStyleSheet("color: #4ec9b0;")
        self.log.emit("TX", "Tag stream started")

    def _stop_stream(self):
        if self._stream_worker:
            self._stream_worker.stop()
            self._stream_worker = None

    def _on_stream_tag(self, tag_data):
        self.tag_received.emit(tag_data)

    def _on_stream_stopped(self):
        self._stream_btn.setChecked(False)
        self._stream_status.setText("Stream: stopped")
        self._stream_status.setStyleSheet("color: #888;")
        self.log.emit("TX", "Tag stream stopped")

    def _group_style(self):
        return (
            "QGroupBox { color: #cccccc; border: 1px solid #444; border-radius: 6px; "
            "margin-top: 10px; padding-top: 16px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }"
        )
