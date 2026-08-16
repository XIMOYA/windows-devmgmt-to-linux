# src/linux_device_manager/ui/properties_dialog.py
# 复刻 Windows 设备属性窗口，展示常规、驱动程序、详细信息和事件。

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

from linux_device_manager.qt_compat import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    Signal,
    QVBoxLayout,
    QWidget,
)

from linux_device_manager.models import Device, DeviceStatus


class DevicePropertiesDialog(QDialog):
    """Windows 风格的设备属性窗口。"""

    driver_update_requested = Signal(Device)
    copy_requested = Signal(str)

    def __init__(self, device: Device, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device = device
        self._detail_values = self._build_detail_values(device)
        self._build_ui()
        self._populate_device()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{self.device.name} 属性")
        self.setMinimumSize(650, 500)
        self.resize(700, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        icon_label = QLabel()
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        icon_label.setPixmap(icon.pixmap(32, 32))
        header.addWidget(icon_label)
        self.header_name = QLabel(self.device.name)
        self.header_name.setObjectName("propertyHeaderName")
        self.header_name.setWordWrap(True)
        header.addWidget(self.header_name, 1)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "常规")
        self.tabs.addTab(self._build_driver_tab(), "驱动程序")
        self.tabs.addTab(self._build_details_tab(), "详细信息")
        self.tabs.addTab(self._build_events_tab(), "事件")
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.copy_button = QPushButton("复制详情")
        self.copy_button.clicked.connect(lambda: self.copy_requested.emit(self.device.as_text()))
        footer.addWidget(self.copy_button)
        footer.addStretch(1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        layout.addLayout(footer)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 12, 10, 8)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.type_value = QLabel()
        self.vendor_value = QLabel()
        self.location_value = QLabel()
        for label in (self.type_value, self.vendor_value, self.location_value):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("设备类型：", self.type_value)
        form.addRow("制造商：", self.vendor_value)
        form.addRow("位置：", self.location_value)
        layout.addLayout(form)

        status_group = QGroupBox("设备状态")
        status_layout = QVBoxLayout(status_group)
        self.status_edit = QPlainTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMinimumHeight(120)
        status_layout.addWidget(self.status_edit)
        layout.addWidget(status_group)
        layout.addStretch(1)
        return tab

    def _build_driver_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 12, 10, 8)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.driver_provider_value = QLabel()
        self.driver_date_value = QLabel()
        self.driver_version_value = QLabel()
        self.driver_signer_value = QLabel()
        for label in (
            self.driver_provider_value,
            self.driver_date_value,
            self.driver_version_value,
            self.driver_signer_value,
        ):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setWordWrap(True)
        form.addRow("驱动程序提供商：", self.driver_provider_value)
        form.addRow("驱动程序日期：", self.driver_date_value)
        form.addRow("驱动程序版本：", self.driver_version_value)
        form.addRow("数字签名者：", self.driver_signer_value)
        layout.addLayout(form)

        action_group = QGroupBox("驱动程序操作")
        action_layout = QVBoxLayout(action_group)
        self.driver_details_button = QPushButton("驱动程序详细信息(D)")
        self.driver_update_button = QPushButton("更新驱动程序(P)")
        self.driver_rollback_button = QPushButton("回退驱动程序(R)")
        self.driver_disable_button = QPushButton("禁用设备(D)")
        self.driver_uninstall_button = QPushButton("卸载设备(U)")
        for button in (
            self.driver_rollback_button,
            self.driver_disable_button,
            self.driver_uninstall_button,
        ):
            button.setEnabled(False)
        self.driver_details_button.clicked.connect(self._show_driver_details)
        self.driver_update_button.clicked.connect(
            lambda: self.driver_update_requested.emit(self.device)
        )
        for button, description in (
            (self.driver_details_button, "查看当前只读驱动信息。"),
            (self.driver_update_button, "打开安全模拟的更新驱动向导。"),
            (self.driver_rollback_button, "当前版本不修改真实驱动。"),
            (self.driver_disable_button, "当前版本不禁用真实设备。"),
            (self.driver_uninstall_button, "当前版本不卸载真实设备。"),
        ):
            row = QHBoxLayout()
            row.addWidget(button)
            row.addWidget(QLabel(description), 1)
            action_layout.addLayout(row)
        layout.addWidget(action_group)
        layout.addStretch(1)
        return tab

    def _build_details_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 12, 10, 8)

        layout.addWidget(QLabel("属性(P)"))
        self.detail_selector = QComboBox()
        self.detail_selector.addItems(list(self._detail_values))
        self.detail_selector.currentTextChanged.connect(self._show_selected_detail)
        layout.addWidget(self.detail_selector)
        layout.addWidget(QLabel("值(V)"))
        self.detail_value = QPlainTextEdit()
        self.detail_value.setReadOnly(True)
        self.detail_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_value.setMinimumHeight(220)
        layout.addWidget(self.detail_value, 1)
        return tab

    def _build_events_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 12, 10, 8)
        self.events_table = QTableWidget(1, 3)
        self.events_table.setHorizontalHeaderLabels(["日期", "信息", "状态"])
        self.events_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.horizontalHeader().setStretchLastSection(True)
        self.events_table.setItem(0, 0, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.events_table.setItem(0, 1, QTableWidgetItem("设备信息已完成只读扫描"))
        self.events_table.setItem(0, 2, QTableWidgetItem("完成"))
        layout.addWidget(self.events_table)
        note = QLabel("此页记录当前应用扫描事件，不代表系统事件查看器中的完整历史。")
        note.setWordWrap(True)
        layout.addWidget(note)
        return tab

    def _populate_device(self) -> None:
        self.type_value.setText(self.device.category.label)
        self.vendor_value.setText(self.device.vendor or "信息不可用")
        self.location_value.setText(self.device.location or "信息不可用")
        status_text = self.device.summary
        if self.device.status is DeviceStatus.WARNING and self.device.driver_problem:
            status_text = f"{status_text}\n\n问题代码：当前版本仅展示状态，不会修改设备。"
        self.status_edit.setPlainText(status_text)
        self.driver_provider_value.setText(
            self._property_value("驱动程序提供商", "驱动提供商")
            or self.device.vendor
            or "Linux 内核/发行版"
        )
        self.driver_date_value.setText(
            self._property_value("驱动程序日期", "驱动日期") or "信息不可用"
        )
        self.driver_version_value.setText(
            self._property_value("驱动程序版本", "驱动版本")
            or self.device.driver
            or "信息不可用"
        )
        self.driver_signer_value.setText(
            self._property_value("数字签名者", "签名者") or "Linux 内核/发行版"
        )
        self._show_selected_detail(self.detail_selector.currentText())

    def _show_selected_detail(self, name: str) -> None:
        self.detail_value.setPlainText(self._detail_values.get(name, "信息不可用"))

    def _property_value(self, *names: str) -> str:
        for name in names:
            value = self.device.properties.get(name)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _build_detail_values(device: Device) -> OrderedDict[str, str]:
        properties: OrderedDict[str, str] = OrderedDict(
            (
                ("设备描述", device.name),
                ("设备实例路径", device.location or "信息不可用"),
                ("硬件 Id", device.properties.get("硬件 ID", "信息不可用")),
                ("兼容 Id", device.properties.get("兼容 ID", "信息不可用")),
                ("类", device.category.label),
                ("类 Guid", device.properties.get("类 Guid", "信息不可用")),
                ("厂商", device.vendor or "信息不可用"),
                ("驱动程序", device.driver or "信息不可用"),
                ("来源路径", device.source_path or "信息不可用"),
            )
        )
        for key, value in device.property_items():
            properties.setdefault(key, value)
        return properties

    def _show_driver_details(self) -> None:
        QMessageBox.information(
            self,
            "驱动程序详细信息",
            "当前版本只展示驱动字段，不会加载、安装或卸载真实驱动文件。",
        )
