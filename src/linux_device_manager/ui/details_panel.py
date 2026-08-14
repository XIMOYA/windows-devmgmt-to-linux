# src/linux_device_manager/ui/details_panel.py
# 展示选中设备的 Windows 风格属性摘要和只读硬件详情。

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_device_manager.models import Device, DeviceStatus


class DetailsPanel(QWidget):
    """设备详情面板。"""

    copy_requested = Signal(str)
    driver_update_requested = Signal(Device)
    properties_requested = Signal(Device)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._device: Device | None = None
        self._build_ui()
        self.set_device(None)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self.device_name = QLabel()
        self.device_name.setObjectName("deviceName")
        self.device_name.setWordWrap(True)
        layout.addWidget(self.device_name)

        self.device_status = QLabel()
        layout.addWidget(self.device_status)

        self.summary_group = QGroupBox("常规")
        summary_layout = QFormLayout(self.summary_group)
        summary_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.category_value = QLabel()
        self.vendor_value = QLabel()
        self.model_value = QLabel()
        self.bus_value = QLabel()
        self.driver_value = QLabel()
        self.location_value = QLabel()
        for label in (
            self.category_value,
            self.vendor_value,
            self.model_value,
            self.bus_value,
            self.driver_value,
            self.location_value,
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setWordWrap(True)
        summary_layout.addRow("设备类别：", self.category_value)
        summary_layout.addRow("厂商：", self.vendor_value)
        summary_layout.addRow("型号：", self.model_value)
        summary_layout.addRow("总线：", self.bus_value)
        summary_layout.addRow("驱动：", self.driver_value)
        summary_layout.addRow("位置：", self.location_value)
        layout.addWidget(self.summary_group)

        properties_group = QGroupBox("详细信息")
        properties_layout = QVBoxLayout(properties_group)
        self.properties_table = QTableWidget(0, 2)
        self.properties_table.setHorizontalHeaderLabels(["属性", "值"])
        self.properties_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.properties_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.properties_table.setAlternatingRowColors(True)
        self.properties_table.horizontalHeader().setStretchLastSection(True)
        self.properties_table.verticalHeader().setVisible(False)
        properties_layout.addWidget(self.properties_table)
        layout.addWidget(properties_group, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.properties_button = QPushButton("属性")
        self.properties_button.clicked.connect(self._show_properties)
        self.copy_button = QPushButton("复制详情")
        self.copy_button.clicked.connect(self._copy_details)
        self.driver_button = QPushButton("更新驱动")
        self.driver_button.clicked.connect(self._request_driver_update)
        buttons.addWidget(self.properties_button)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.driver_button)
        layout.addLayout(buttons)

    def set_device(self, device: Device | None) -> None:
        self._device = device
        enabled = device is not None
        for widget in (
            self.summary_group,
            self.properties_table,
            self.properties_button,
            self.copy_button,
            self.driver_button,
        ):
            widget.setEnabled(enabled)

        if device is None:
            self.device_name.setText("请选择一个设备")
            self.device_status.setText("左侧列表会显示当前系统发现的硬件设备。")
            self.device_status.setObjectName("emptyHint")
            self._refresh_status_style()
            for label in (
                self.category_value,
                self.vendor_value,
                self.model_value,
                self.bus_value,
                self.driver_value,
                self.location_value,
            ):
                label.setText("—")
            self.properties_table.setRowCount(0)
            return

        self.device_name.setText(device.display_name)
        self.device_status.setText(f"状态：{device.summary}")
        self.device_status.setObjectName(
            "deviceStatusWarning" if device.status is DeviceStatus.WARNING else "deviceStatusOk"
        )
        self._refresh_status_style()
        self.category_value.setText(device.category.label)
        self.vendor_value.setText(device.vendor or "信息不可用")
        self.model_value.setText(device.model or "信息不可用")
        self.bus_value.setText(device.bus or "信息不可用")
        self.driver_value.setText(device.driver or "信息不可用")
        self.location_value.setText(device.location or "信息不可用")
        items = [("来源路径", device.source_path or "信息不可用"), *device.property_items()]
        self.properties_table.setRowCount(len(items))
        for row, (key, value) in enumerate(items):
            self.properties_table.setItem(row, 0, QTableWidgetItem(key))
            self.properties_table.setItem(row, 1, QTableWidgetItem(value))
        self.properties_table.resizeColumnsToContents()

    def _refresh_status_style(self) -> None:
        style = self.device_status.style()
        style.unpolish(self.device_status)
        style.polish(self.device_status)
        self.device_status.update()

    def _copy_details(self) -> None:
        if self._device is not None:
            self.copy_requested.emit(self._device.as_text())

    def _request_driver_update(self) -> None:
        if self._device is not None:
            self.driver_update_requested.emit(self._device)

    def _show_properties(self) -> None:
        if self._device is not None:
            self.properties_requested.emit(self._device)
