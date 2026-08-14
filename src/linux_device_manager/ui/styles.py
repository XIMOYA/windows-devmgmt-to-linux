# src/linux_device_manager/ui/styles.py
# 设备管理器的 Qt 样式，保留 Windows 工具窗口的浅色、紧凑视觉。

WINDOW_STYLE = """
QMainWindow {
    background: #f1f3f5;
    color: #202124;
    font-size: 13px;
}
QMenuBar {
    background: #f7f8fa;
    border-bottom: 1px solid #cfd4da;
    padding: 2px 0;
}
QMenuBar::item {
    padding: 5px 10px;
}
QMenuBar::item:selected {
    background: #dceeff;
}
QToolBar {
    background: #f8f9fb;
    border-bottom: 1px solid #cfd4da;
    spacing: 5px;
    padding: 4px 7px;
}
QToolButton {
    padding: 5px 10px;
    border: 1px solid transparent;
    border-radius: 3px;
}
QToolButton:hover {
    background: #e4f1fd;
    border: 1px solid #a9cbe9;
}
QSplitter::handle {
    background: #cbd1d8;
}
QSplitter::handle:hover {
    background: #8eb6d8;
}
QLineEdit {
    min-height: 27px;
    padding: 3px 8px;
    background: #ffffff;
    border: 1px solid #aeb7c1;
    border-radius: 3px;
}
QLineEdit:focus {
    border: 1px solid #4f9bd5;
}
QLabel#treeTitle {
    color: #36414c;
    font-size: 15px;
    font-weight: 600;
    padding-left: 2px;
}
QLabel#scanSummary,
QLabel#scanSummaryOk,
QLabel#scanSummaryWarning {
    padding: 7px 10px;
    border-bottom: 1px solid #cfd4da;
}
QLabel#scanSummary {
    background: #edf1f5;
    color: #53616e;
}
QLabel#scanSummaryOk {
    background: #e7f4ea;
    color: #216e39;
}
QLabel#scanSummaryWarning {
    background: #fff3d9;
    color: #8a5700;
}
QTreeWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #b5bec8;
    selection-background-color: #c9e5fb;
    selection-color: #17212b;
    alternate-background-color: #f7f9fb;
}
QTreeWidget {
    padding: 4px;
    outline: 0;
}
QTreeWidget::item {
    min-height: 26px;
    padding: 3px 5px;
}
QTreeWidget::item:hover {
    background: #eef7ff;
}
QTreeWidget::item:selected {
    border: 1px solid #9bc7e8;
}
QHeaderView::section {
    background: #eef2f6;
    color: #35424e;
    padding: 6px 8px;
    border: 0;
    border-right: 1px solid #d2d8de;
    border-bottom: 1px solid #c3cbd3;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #e0e4e8;
}
QTableWidget::item {
    padding: 4px 6px;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #cbd2d9;
    border-radius: 3px;
    margin-top: 10px;
    padding: 12px 9px 8px 9px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 5px;
    color: #3d4a56;
    background: #f1f3f5;
}
QLabel#emptyHint {
    color: #697680;
    font-size: 14px;
}
QLabel#deviceName {
    font-size: 18px;
    font-weight: 600;
    color: #1e2a34;
    padding: 2px 0;
}
QLabel#deviceStatusOk {
    color: #167c32;
    font-weight: 600;
}
QLabel#deviceStatusWarning {
    color: #b45f00;
    font-weight: 600;
}
QLabel#deviceStatusUnknown {
    color: #687581;
    font-weight: 600;
}
QPushButton {
    min-height: 28px;
    padding: 5px 13px;
}
QPushButton:hover {
    background: #e3f1fd;
}
QStatusBar {
    background: #f7f8fa;
    border-top: 1px solid #cfd4da;
    color: #53616e;
}
"""
