import csv
import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QFileDialog, QHeaderView,
)


class TagTable(QWidget):
    """Displays scanned RFID tags with deduplication by EPC."""

    HEADERS = ["#", "EPC", "RSSI", "PC", "CRC", "Bank Data", "Seen", "Last Seen"]
    MAX_VISIBLE_ROWS = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = {}  # epc -> row_data dict
        self._row_counter = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        title = QLabel("Tag Data")
        title.setStyleSheet("font-weight: bold; color: #cccccc;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._count_label = QLabel("0 tags")
        self._count_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self._count_label)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self.clear)
        header_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.setFixedWidth(80)
        export_btn.clicked.connect(self._export_csv)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            "QTableWidget { background-color: #1e1e1e; color: #cccccc; "
            "gridline-color: #333; alternate-background-color: #252525; }"
            "QHeaderView::section { background-color: #2d2d2d; color: #cccccc; "
            "border: 1px solid #333; padding: 4px; }"
        )
        self._table.setRowCount(0)
        layout.addWidget(self._table)

    def add_tag(self, tag_data):
        """Add or update a tag. tag_data must contain at least 'epc' and 'rssi'.

        Args:
            tag_data: dict with keys epc, rssi, pc, crc, EPCsize, and optionally 'data'
        """
        epc = tag_data.get("epc", "??")
        now = datetime.now().strftime("%H:%M:%S")

        if epc in self._tags:
            row_info = self._tags[epc]
            row_info["count"] += 1
            row_info["rssi"] = tag_data.get("rssi", row_info["rssi"])
            row_info["last_seen"] = now
            row_idx = row_info["row"]
            self._table.item(row_idx, 2).setText(str(tag_data.get("rssi", "")))
            self._table.item(row_idx, 6).setText(str(row_info["count"]))
            self._table.item(row_idx, 7).setText(now)
            if "data" in tag_data and tag_data["data"]:
                self._table.item(row_idx, 5).setText(str(tag_data["data"]))
        else:
            self._row_counter += 1
            row_idx = self._table.rowCount()
            self._table.insertRow(row_idx)

            self._table.setItem(row_idx, 0, QTableWidgetItem(str(self._row_counter)))
            self._table.setItem(row_idx, 1, QTableWidgetItem(epc))
            self._table.setItem(row_idx, 2, QTableWidgetItem(str(tag_data.get("rssi", ""))))
            self._table.setItem(row_idx, 3, QTableWidgetItem(str(tag_data.get("pc", ""))))
            self._table.setItem(row_idx, 4, QTableWidgetItem(str(tag_data.get("crc", ""))))
            self._table.setItem(row_idx, 5, QTableWidgetItem(str(tag_data.get("data", ""))))
            self._table.setItem(row_idx, 6, QTableWidgetItem("1"))
            self._table.setItem(row_idx, 7, QTableWidgetItem(now))

            self._tags[epc] = {
                "row": row_idx,
                "rssi": tag_data.get("rssi", ""),
                "pc": tag_data.get("pc", ""),
                "crc": tag_data.get("crc", ""),
                "data": tag_data.get("data", ""),
                "count": 1,
                "last_seen": now,
            }

        self._count_label.setText(f"{len(self._tags)} tag(s)")

    def clear(self):
        self._table.setRowCount(0)
        self._tags.clear()
        self._row_counter = 0
        self._count_label.setText("0 tags")

    def _export_csv(self):
        if not self._tags:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Tags", f"tags_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.HEADERS)
            for epc, info in self._tags.items():
                writer.writerow([
                    "", epc, info["rssi"], info["pc"], info["crc"],
                    info["data"], info["count"], info["last_seen"]
                ])
