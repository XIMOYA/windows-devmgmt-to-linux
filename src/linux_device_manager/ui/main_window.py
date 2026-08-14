# src/linux_device_manager/ui/main_window.py
# 设备管理器主窗口：菜单、工具栏、设备树、详情面板和安全的驱动模拟。

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linux_device_manager.models import Device, DeviceStatus
from linux_device_manager.providers.base import DeviceProvider, DiscoveryResult
from linux_device_manager.services.device_service import DeviceRefreshService
from linux_device_manager.ui.details_panel import DetailsPanel
from linux_device_manager.ui.device_tree import DeviceTree
from linux_device_manager.ui.styles import WINDOW_STYLE


class MainWindow(QMainWindow):
    """Windows 风格的只读 Linux 设备管理器。"""

    request_quit = Signal()

    def __init__(self, provider: DeviceProvider, *, mock_mode: bool = False) -> None:
        super().__init__()
        self.provider = provider
        self.mock_mode = mock_mode
        self.service = DeviceRefreshService(provider, self)
        self.refresh_action: QAction
        self._build_ui()
        self._connect_signals()
        self._set_window_metadata()
        self.refresh_devices()

    def _set_window_metadata(self) -> None:
        self.setWindowTitle("设备管理器")
        self.setMinimumSize(900, 580)
        self.resize(1120, 700)
        self.setStyleSheet(WINDOW_STYLE)

    def _build_ui(self) -> None:
        self._build_actions()
        self._build_menus()
        self._build_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.device_tree = DeviceTree()
        self.details_panel = DetailsPanel()
        splitter.addWidget(self.device_tree)
        splitter.addWidget(self.details_panel)
        splitter.setSizes([370, 730])
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("正在读取设备信息…")

    def _build_actions(self) -> None:
        self.refresh_action = QAction("刷新", self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.refresh_action.setStatusTip("重新扫描硬件设备")

        self.properties_action = QAction("属性", self)
        self.properties_action.setStatusTip("查看选中设备的属性")

        self.driver_action = QAction("更新驱动", self)
        self.driver_action.setStatusTip("检查选中设备的驱动状态（仅模拟）")

        self.copy_action = QAction("复制详情", self)
        self.copy_action.setStatusTip("复制选中设备的详细信息")

        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self.exit_action.setStatusTip("退出设备管理器")

        self.about_action = QAction("关于设备管理器", self)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.refresh_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = self.menuBar().addMenu("查看")
        view_menu.addAction(self.properties_action)
        view_menu.addAction(self.copy_action)

        tools_menu = self.menuBar().addMenu("工具")
        tools_menu.addAction(self.driver_action)
        tools_menu.addAction(self.refresh_action)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction(self.about_action)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("设备管理器工具栏")
        toolbar.setMovable(False)
        toolbar.addAction(self.refresh_action)
        toolbar.addSeparator()
        toolbar.addAction(self.properties_action)
        toolbar.addAction(self.driver_action)
        toolbar.addAction(self.copy_action)

    def _connect_signals(self) -> None:
        self.refresh_action.triggered.connect(self.refresh_devices)
        self.properties_action.triggered.connect(self._show_selected_properties)
        self.driver_action.triggered.connect(self._update_selected_driver)
        self.copy_action.triggered.connect(self._copy_selected_details)
        self.exit_action.triggered.connect(self.close)
        self.about_action.triggered.connect(self._show_about)
        self.device_tree.device_selected.connect(self.details_panel.set_device)
        self.device_tree.device_activated.connect(self._show_properties)
        self.details_panel.copy_requested.connect(self._copy_text)
        self.details_panel.driver_update_requested.connect(self._show_driver_result)
        self.details_panel.properties_requested.connect(self._show_properties)
        self.service.started.connect(self._on_refresh_started)
        self.service.completed.connect(self._on_refresh_completed)

    @Slot()
    def refresh_devices(self) -> None:
        if not self.service.refresh():
            self.statusBar().showMessage("设备扫描正在进行中…")

    @Slot()
    def _on_refresh_started(self) -> None:
        self.refresh_action.setEnabled(False)
        self.statusBar().showMessage("正在扫描设备…")

    @Slot(object)
    def _on_refresh_completed(self, result: DiscoveryResult) -> None:
        self.refresh_action.setEnabled(True)
        self.device_tree.set_devices(result.devices)
        if result.errors:
            self.statusBar().showMessage(
                f"已发现 {len(result.devices)} 个设备；{len(result.errors)} 项信息读取失败。"
            )
        else:
            mode = "演示数据" if self.mock_mode else "Linux 硬件"
            self.statusBar().showMessage(f"已发现 {len(result.devices)} 个设备（{mode}）。")

    def _selected_device(self) -> Device | None:
        return self.device_tree.selected_device

    @Slot()
    def _show_selected_properties(self) -> None:
        device = self._selected_device()
        if device is None:
            self._show_no_selection()
            return
        self._show_properties(device)

    @Slot(object)
    def _show_properties(self, device: Device) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{device.name} 属性")
        dialog.setMinimumSize(610, 430)
        layout = QVBoxLayout(dialog)

        tabs = QTabWidget()
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.addRow("设备类型：", QLabel(device.category.label))
        general_layout.addRow("制造商：", QLabel(device.vendor or "信息不可用"))
        general_layout.addRow("位置：", QLabel(device.location or "信息不可用"))
        general_layout.addRow("设备状态：", QLabel(device.summary))
        tabs.addTab(general_tab, "常规")

        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setPlainText(device.as_text())
        details_layout.addWidget(details_text)
        tabs.addTab(details_tab, "详细信息")

        driver_tab = QWidget()
        driver_layout = QVBoxLayout(driver_tab)
        driver_group = QGroupBox("驱动程序信息")
        driver_form = QFormLayout(driver_group)
        driver_form.addRow("提供商：", QLabel(device.vendor or "Linux 内核/发行版"))
        driver_form.addRow("驱动程序：", QLabel(device.driver or "信息不可用"))
        driver_form.addRow("状态：", QLabel("只读展示，未执行驱动操作"))
        driver_layout.addWidget(driver_group)
        driver_layout.addStretch(1)
        tabs.addTab(driver_tab, "驱动程序")

        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    @Slot()
    def _update_selected_driver(self) -> None:
        device = self._selected_device()
        if device is None:
            self._show_no_selection()
            return
        self._show_driver_result(device)

    @Slot(object)
    def _show_driver_result(self, device: Device) -> None:
        if device.status is DeviceStatus.WARNING:
            title = "更新驱动程序"
            message = (
                f"Windows 设备管理器已完成搜索。\n\n"
                f"找不到设备“{device.name}”的驱动程序。\n"
                "Linux 下的驱动由内核或发行版软件包管理器负责。"
            )
            icon = QMessageBox.Icon.Warning
        else:
            title = "更新驱动程序"
            message = (
                f"已是最佳驱动程序。\n\n"
                f"设备“{device.name}”当前使用：{device.driver or '内核默认驱动'}\n"
                "本次操作为安全模拟，不会安装、卸载或修改真实驱动。"
            )
            icon = QMessageBox.Icon.Information
        QMessageBox(icon, title, message, QMessageBox.StandardButton.Ok, self).exec()

    @Slot()
    def _copy_selected_details(self) -> None:
        device = self._selected_device()
        if device is None:
            self._show_no_selection()
            return
        self._copy_text(device.as_text())

    @Slot(str)
    def _copy_text(self, text: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("设备详情已复制到剪贴板。", 3000)

    def _show_no_selection(self) -> None:
        QMessageBox.information(self, "设备管理器", "请先从左侧选择一个设备。")

    @Slot()
    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "关于设备管理器",
            "设备管理器 0.1.0\n\n"
            "一个给 Linux 用户补上的 Windows 风格硬件查看工具。\n"
            "当前版本只读展示设备信息，不会修改真实驱动或系统配置。",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.service.thread_pool.waitForDone(1000)
        event.accept()
