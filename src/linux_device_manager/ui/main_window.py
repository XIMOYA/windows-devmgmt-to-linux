# src/linux_device_manager/ui/main_window.py
# 设备管理器主窗口：经典设备树、菜单、工具栏和可选详情面板。

from __future__ import annotations

import platform

from linux_device_manager.qt_compat import (
    QAction,
    QApplication,
    QCloseEvent,
    QHBoxLayout,
    QLabel,
    QKeySequence,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QT_BINDING,
    Qt,
    Signal,
    Slot,
    QVBoxLayout,
    QWidget,
)

from linux_device_manager.models import Device, DeviceStatus
from linux_device_manager.providers.base import DeviceProvider, DiscoveryResult
from linux_device_manager.services.device_service import DeviceRefreshService
from linux_device_manager.ui.details_panel import DetailsPanel
from linux_device_manager.ui.device_tree import DeviceTree
from linux_device_manager.ui.driver_wizard import DriverUpdateWizard
from linux_device_manager.ui.properties_dialog import DevicePropertiesDialog
from linux_device_manager.ui.styles import WINDOW_STYLE


class MainWindow(QMainWindow):
    """Windows 风格的只读 Linux 设备管理器。"""

    request_quit = Signal()

    def __init__(self, provider: DeviceProvider, *, mock_mode: bool = False) -> None:
        super().__init__()
        self.provider = provider
        self.mock_mode = mock_mode
        self._host_name = "DEVMGMT-LINUX" if mock_mode else platform.node() or "此电脑"
        self.service = DeviceRefreshService(provider, self)
        self.refresh_action: QAction
        self._build_ui()
        self._connect_signals()
        self._set_window_metadata()
        self.refresh_devices()

    def _set_window_metadata(self) -> None:
        self.setWindowTitle("设备管理器")
        self.setMinimumSize(760, 520)
        self.resize(980, 680)
        self.setStyleSheet(WINDOW_STYLE)

    def _build_ui(self) -> None:
        self._build_actions()
        self._build_menus()
        self._build_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(3)
        self.tree_title = QLabel("设备管理器")
        self.tree_title.setObjectName("treeTitle")
        left_layout.addWidget(self.tree_title)

        self.search_row_widget = QWidget()
        search_row = QHBoxLayout(self.search_row_widget)
        search_row.setContentsMargins(0, 0, 0, 2)
        search_row.setSpacing(4)
        search_row.addWidget(QLabel("筛选："))
        self.search_box = QLineEdit()
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setPlaceholderText("名称、厂商、驱动或硬件 ID")
        self.search_box.setToolTip("按设备名称、厂商、型号、驱动、位置或属性筛选")
        search_row.addWidget(self.search_box, 1)
        left_layout.addWidget(self.search_row_widget)

        self.device_tree = DeviceTree()
        left_layout.addWidget(self.device_tree, 1)

        self.details_panel = DetailsPanel()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.details_panel)
        splitter.setSizes([980, 420])

        self.scan_summary = QLabel("正在读取设备信息…")
        self.scan_summary.setObjectName("scanSummary")
        self.scan_summary.setWordWrap(True)
        self.scan_summary.setContentsMargins(8, 4, 8, 4)

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.scan_summary)
        central_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.search_row_widget.hide()
        self.scan_summary.hide()
        self.details_panel.hide()
        self.statusBar().showMessage("正在读取设备信息…")

    def _build_actions(self) -> None:
        self.refresh_action = QAction("刷新", self)
        self.refresh_action.setShortcut(QKeySequence("F5"))
        self.refresh_action.setStatusTip("重新扫描硬件设备")

        self.properties_action = QAction("属性", self)
        self.properties_action.setStatusTip("查看选中设备的属性")

        self.driver_action = QAction("更新驱动", self)
        self.driver_action.setStatusTip("打开安全模拟的更新驱动向导")

        self.copy_action = QAction("复制详情", self)
        self.copy_action.setStatusTip("复制选中设备的详细信息")

        self.details_action = QAction("详细信息面板", self)
        self.details_action.setCheckable(True)
        self.details_action.setStatusTip("显示或隐藏辅助详情面板")

        self.filter_action = QAction("设备筛选", self)
        self.filter_action.setCheckable(True)
        self.filter_action.setStatusTip("显示或隐藏设备筛选框")

        self.summary_action = QAction("扫描摘要", self)
        self.summary_action.setCheckable(True)
        self.summary_action.setStatusTip("显示或隐藏扫描摘要")

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
        view_menu.addSeparator()
        view_menu.addAction(self.details_action)
        view_menu.addAction(self.filter_action)
        view_menu.addAction(self.summary_action)

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
        self.details_action.toggled.connect(self.details_panel.setVisible)
        self.filter_action.toggled.connect(self.search_row_widget.setVisible)
        self.summary_action.toggled.connect(self.scan_summary.setVisible)
        self.search_box.textChanged.connect(self.device_tree.set_filter_text)
        self.device_tree.device_selected.connect(self.details_panel.set_device)
        self.device_tree.device_activated.connect(self._show_properties)
        self.details_panel.copy_requested.connect(self._copy_text)
        self.details_panel.driver_update_requested.connect(self._show_driver_wizard)
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
        self.scan_summary.setObjectName("scanSummary")
        self.scan_summary.setText("正在扫描 Linux 硬件…")
        self.scan_summary.setToolTip("")
        self._refresh_scan_summary_style()
        self.statusBar().showMessage("正在扫描设备…")

    @Slot(object)
    def _on_refresh_completed(self, result: DiscoveryResult) -> None:
        self.refresh_action.setEnabled(True)
        self.device_tree.set_devices(result.devices, host_name=self._host_name)
        warning_count = sum(1 for device in result.devices if device.status is not DeviceStatus.OK)
        mode = "演示数据" if self.mock_mode else "Linux 真机"
        if result.errors:
            self.scan_summary.setObjectName("scanSummaryWarning")
            self.scan_summary.setText(
                f"扫描完成：{len(result.devices)} 个设备 · {warning_count} 个警告 · "
                f"{len(result.errors)} 项读取提示"
            )
            self.scan_summary.setToolTip("\n".join(result.errors))
            self.statusBar().showMessage(
                f"已发现 {len(result.devices)} 个设备；{len(result.errors)} 项信息读取失败。"
            )
        else:
            self.scan_summary.setObjectName("scanSummaryOk")
            self.scan_summary.setText(
                f"扫描完成：{len(result.devices)} 个设备 · {warning_count} 个警告 · {mode}"
            )
            self.scan_summary.setToolTip("所有设备类别均完成读取。")
            self.statusBar().showMessage(f"已发现 {len(result.devices)} 个设备（{mode}）。")
        self._refresh_scan_summary_style()

    def _refresh_scan_summary_style(self) -> None:
        style = self.scan_summary.style()
        style.unpolish(self.scan_summary)
        style.polish(self.scan_summary)
        self.scan_summary.update()

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
        dialog = DevicePropertiesDialog(device, self)
        dialog.copy_requested.connect(self._copy_text)
        dialog.driver_update_requested.connect(self._show_driver_wizard)
        dialog.exec()

    @Slot()
    def _update_selected_driver(self) -> None:
        device = self._selected_device()
        if device is None:
            self._show_no_selection()
            return
        self._show_driver_wizard(device)

    @Slot(object)
    def _show_driver_wizard(self, device: Device) -> None:
        DriverUpdateWizard(device, self).exec()

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
            "设备管理器 0.2.0\n\n"
            "一个给 Linux 用户补上的 Windows 风格硬件查看工具。\n"
            f"当前 Qt 绑定：{QT_BINDING}\n"
            "当前版本只读展示设备信息，不会修改真实驱动或系统配置。",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.service.thread_pool.waitForDone(1000)
        event.accept()
