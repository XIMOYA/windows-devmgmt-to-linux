# src/linux_device_manager/ui/driver_wizard.py
# 复刻 Windows 更新驱动向导的页面流程，但所有操作均为只读模拟。

from __future__ import annotations

from linux_device_manager.qt_compat import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from linux_device_manager.models import Device, DeviceStatus


class DriverUpdateWizard(QDialog):
    """安全模拟 Windows 更新驱动程序向导。"""

    def __init__(self, device: Device, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device = device
        self.current_page = 0
        self._progress_value = 0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._advance_progress)
        self._build_ui()
        self._set_page(0)

    @property
    def page_count(self) -> int:
        return self.pages.count()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"更新驱动程序 - {self.device.name}")
        self.setMinimumSize(700, 470)
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setObjectName("wizardTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        self.subtitle_label = QLabel(f"设备：{self.device.name}")
        self.subtitle_label.setObjectName("wizardSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_choice_page())
        self.pages.addWidget(self._build_browse_page())
        self.pages.addWidget(self._build_driver_list_page())
        self.pages.addWidget(self._build_progress_page())
        self.pages.addWidget(self._build_result_page())
        layout.addWidget(self.pages, 1)

        line = QWidget()
        line.setObjectName("wizardSeparator")
        line.setFixedHeight(1)
        layout.addWidget(line)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.back_button = QPushButton("上一步(B)")
        self.next_button = QPushButton("下一步(N)")
        self.cancel_button = QPushButton("取消")
        self.back_button.clicked.connect(self._go_back)
        self.next_button.clicked.connect(self._go_next)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

    def _build_choice_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        question = QLabel("你要如何搜索驱动程序？")
        question.setObjectName("wizardQuestion")
        layout.addWidget(question)

        self.auto_radio = QRadioButton("自动搜索驱动程序(S)")
        auto_description = QLabel(
            "Windows 将在你的计算机中搜索最佳可用驱动程序，并将其安装在你的设备上。"
        )
        auto_description.setWordWrap(True)
        auto_panel = QVBoxLayout()
        auto_panel.addWidget(self.auto_radio)
        auto_panel.addWidget(auto_description)
        layout.addLayout(auto_panel)

        self.browse_radio = QRadioButton("浏览我的电脑以查找驱动程序(R)")
        browse_description = QLabel("手动查找并安装驱动程序。")
        browse_description.setWordWrap(True)
        browse_panel = QVBoxLayout()
        browse_panel.addWidget(self.browse_radio)
        browse_panel.addWidget(browse_description)
        layout.addLayout(browse_panel)
        self.auto_radio.setChecked(True)
        layout.addStretch(1)
        return page

    def _build_browse_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        title = QLabel("浏览计算机上的驱动程序")
        title.setObjectName("wizardQuestion")
        layout.addWidget(title)
        layout.addWidget(QLabel("在以下位置搜索驱动程序："))
        row = QHBoxLayout()
        self.path_edit = QLineEdit("C:\\Windows\\System32\\DriverStore")
        self.browse_button = QPushButton("浏览(R)…")
        self.browse_button.clicked.connect(self._browse_directory)
        row.addWidget(self.path_edit, 1)
        row.addWidget(self.browse_button)
        layout.addLayout(row)
        self.include_subfolders = QCheckBox("包括子文件夹(I)")
        self.include_subfolders.setChecked(True)
        layout.addWidget(self.include_subfolders)
        self.manual_select_button = QPushButton(
            "让我从计算机上的可用驱动程序列表中选取(L)"
        )
        self.manual_select_button.clicked.connect(lambda: self._set_page(2))
        layout.addWidget(self.manual_select_button)
        layout.addStretch(1)
        return page

    def _build_driver_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        title = QLabel("选择要为此硬件安装的设备驱动程序")
        title.setObjectName("wizardQuestion")
        layout.addWidget(title)
        layout.addWidget(QLabel("请选择硬件设备的厂商和型号，然后单击“下一步”。"))
        self.driver_list = QListWidget()
        self.driver_list.addItem(self.device.driver or "Linux 内核默认驱动")
        self.driver_list.addItem(f"{self.device.category.label}（兼容驱动）")
        self.driver_list.setCurrentRow(0)
        layout.addWidget(self.driver_list, 1)
        self.disk_install_button = QPushButton("从磁盘安装(H)…")
        self.disk_install_button.clicked.connect(self._show_safe_notice)
        layout.addWidget(self.disk_install_button)
        return page

    def _build_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        self.progress_label = QLabel("正在搜索驱动程序…")
        self.progress_label.setObjectName("wizardQuestion")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        note = QLabel("此过程为 Windows 风格的安全模拟，不会访问或修改真实驱动文件。")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 12, 0, 0)
        self.result_title = QLabel()
        self.result_title.setObjectName("wizardQuestion")
        self.result_title.setWordWrap(True)
        layout.addWidget(self.result_title)
        self.result_detail = QLabel()
        self.result_detail.setWordWrap(True)
        layout.addWidget(self.result_detail)
        layout.addStretch(1)
        return page

    def _set_page(self, page_index: int) -> None:
        page_index = max(0, min(page_index, self.page_count - 1))
        self.current_page = page_index
        self.pages.setCurrentIndex(page_index)
        self.back_button.setEnabled(page_index in {1, 2})
        if page_index == 4:
            self.title_label.setText("驱动程序更新完成")
            self.next_button.setText("关闭(C)")
            self.next_button.setEnabled(True)
            self.cancel_button.setVisible(False)
        elif page_index == 3:
            self.title_label.setText("正在搜索驱动程序")
            self.next_button.setEnabled(False)
            self.cancel_button.setVisible(True)
        else:
            self.title_label.setText("你要如何搜索驱动程序？")
            self.next_button.setText("下一步(N)")
            self.next_button.setEnabled(True)
            self.cancel_button.setVisible(True)
        if page_index == 4:
            self._populate_result()

    def _go_next(self) -> None:
        if self.current_page == 0:
            self._set_page(1 if self.browse_radio.isChecked() else 3)
            if self.current_page == 3:
                self._start_search()
        elif self.current_page == 1:
            self._set_page(2)
        elif self.current_page == 2:
            self._start_search()
        elif self.current_page == 4:
            self.accept()

    def _go_back(self) -> None:
        if self.current_page == 1:
            self._set_page(0)
        elif self.current_page == 2:
            self._set_page(1)

    def _start_search(self) -> None:
        self._progress_value = 0
        self.progress_bar.setValue(0)
        self._set_page(3)
        self._timer.start()

    def _advance_progress(self) -> None:
        self._progress_value = min(100, self._progress_value + 10)
        self.progress_bar.setValue(self._progress_value)
        if self._progress_value >= 100:
            self._timer.stop()
            self._set_page(4)

    def _populate_result(self) -> None:
        if self.device.status in {DeviceStatus.WARNING, DeviceStatus.UNKNOWN}:
            self.result_title.setText("找不到更好的驱动程序")
            self.result_detail.setText(
                "当前设备没有可由此安全模拟向导安装的更好驱动程序。\n"
                "Linux 驱动由内核和发行版软件包管理器负责。"
            )
        else:
            self.result_title.setText("你的设备的最佳驱动程序已安装")
            self.result_detail.setText(
                "Windows 风格的搜索流程已完成。\n"
                "本次操作没有安装、卸载或修改任何真实驱动文件。"
            )

    def _browse_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择驱动程序目录")
        if directory:
            self.path_edit.setText(directory)

    def _show_safe_notice(self) -> None:
        QMessageBox.information(
            self,
            "从磁盘安装",
            "当前版本只模拟 Windows 界面，不会读取或安装真实驱动程序。",
        )

    def closeEvent(self, event) -> None:
        self._timer.stop()
        event.accept()
