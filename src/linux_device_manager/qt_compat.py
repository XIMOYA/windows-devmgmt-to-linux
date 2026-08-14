# src/linux_device_manager/qt_compat.py
# 统一 PySide6/PyQt6 API，方便在不同 Linux 发行版和 Windows 开发环境运行。

from __future__ import annotations

try:  # 优先使用项目原先的 PySide6。
    from PySide6.QtCore import (
        QCoreApplication,
        QEventLoop,
        QObject,
        QRunnable,
        QSize,
        QThreadPool,
        QTimer,
        Qt,
        Signal,
        Slot,
    )
    from PySide6.QtGui import (
        QAction,
        QColor,
        QCloseEvent,
        QFont,
        QIcon,
        QKeySequence,
        QPainter,
        QPixmap,
    )
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSplitter,
        QStyle,
        QStyleFactory,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError as pyside_error:  # pragma: no cover - 取决于运行环境
    try:
        from PyQt6.QtCore import (
            QCoreApplication,
            QEventLoop,
            QObject,
            QRunnable,
            QSize,
            QThreadPool,
            QTimer,
            Qt,
            pyqtSignal as Signal,
            pyqtSlot as Slot,
        )
        from PyQt6.QtGui import (
            QAction,
            QColor,
            QCloseEvent,
            QFont,
            QIcon,
            QKeySequence,
            QPainter,
            QPixmap,
        )
        from PyQt6.QtWidgets import (
            QAbstractItemView,
            QApplication,
            QDialog,
            QDialogButtonBox,
            QFormLayout,
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSizePolicy,
            QSplitter,
            QStyle,
            QStyleFactory,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextEdit,
            QTreeWidget,
            QTreeWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        QT_BINDING = "PyQt6"
    except ImportError as pyqt_error:  # pragma: no cover - 取决于运行环境
        raise ImportError(
            "需要安装 PySide6 或 PyQt6 才能启动设备管理器。"
            "例如：python -m pip install PySide6，或使用发行版提供的 PyQt6。"
        ) from (pyqt_error if pyqt_error else pyside_error)


__all__ = [
    "QAbstractItemView",
    "QAction",
    "QApplication",
    "QCloseEvent",
    "QColor",
    "QCoreApplication",
    "QDialog",
    "QDialogButtonBox",
    "QEventLoop",
    "QFont",
    "QFormLayout",
    "QGroupBox",
    "QHBoxLayout",
    "QHeaderView",
    "QIcon",
    "QKeySequence",
    "QLabel",
    "QLineEdit",
    "QMainWindow",
    "QMessageBox",
    "QPainter",
    "QPixmap",
    "QPushButton",
    "QRunnable",
    "QSize",
    "QSizePolicy",
    "QSplitter",
    "QStyle",
    "QStyleFactory",
    "QTableWidget",
    "QTableWidgetItem",
    "QTabWidget",
    "QTextEdit",
    "QThreadPool",
    "QTimer",
    "QTreeWidget",
    "QTreeWidgetItem",
    "QVBoxLayout",
    "QWidget",
    "QObject",
    "Qt",
    "Signal",
    "Slot",
    "QT_BINDING",
]
