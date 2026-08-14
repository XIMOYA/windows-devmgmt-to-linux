# src/linux_device_manager/ui/styles.py
# 设备管理器的 Qt 样式，保留 Windows 工具窗口的浅色、紧凑视觉。

WINDOW_STYLE = """
QMainWindow {
    background: #f3f3f3;
}
QMenuBar {
    background: #f5f5f5;
    border-bottom: 1px solid #d4d4d4;
    padding: 2px 0;
}
QMenuBar::item {
    padding: 4px 9px;
}
QMenuBar::item:selected {
    background: #e5f1fb;
}
QToolBar {
    background: #f7f7f7;
    border-bottom: 1px solid #d6d6d6;
    spacing: 4px;
    padding: 3px 6px;
}
QToolButton {
    padding: 4px 8px;
    border: 1px solid transparent;
}
QToolButton:hover {
    background: #e5f1fb;
    border: 1px solid #b7d7f2;
}
QSplitter::handle {
    background: #d2d2d2;
}
QTreeWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #bdbdbd;
    selection-background-color: #cce8ff;
    selection-color: #111111;
    alternate-background-color: #fafafa;
}
QTreeWidget {
    padding: 3px;
}
QTreeWidget::item {
    min-height: 24px;
    padding: 2px 3px;
}
QTreeWidget::item:hover {
    background: #eef7ff;
}
QGroupBox {
    font-weight: 600;
    border: 1px solid #d0d0d0;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QLabel#emptyHint {
    color: #666666;
    font-size: 14px;
}
QLabel#deviceName {
    font-size: 17px;
    font-weight: 600;
    color: #1d1d1d;
}
QLabel#deviceStatusOk {
    color: #167c32;
}
QLabel#deviceStatusWarning {
    color: #b75d00;
    font-weight: 600;
}
QPushButton {
    padding: 5px 12px;
}
QStatusBar {
    background: #f5f5f5;
    border-top: 1px solid #d4d4d4;
}
"""
