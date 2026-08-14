# src/linux_device_manager/ui/device_tree.py
# 以 Windows 设备管理器的树形结构展示设备分类和设备状态。

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from linux_device_manager.models import CATEGORY_ORDER, Device, DeviceCategory, DeviceStatus


_ROLE_DEVICE = Qt.ItemDataRole.UserRole


def _make_icon(color: str, symbol: str) -> QIcon:
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, 18, 18, 3, 3)
    painter.setPen(QColor("white"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol)
    painter.end()
    return QIcon(pixmap)


class DeviceTree(QTreeWidget):
    """设备分类树。"""

    device_selected = Signal(object)
    device_activated = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setAnimated(True)
        self.setUniformRowHeights(True)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_activated)
        self._category_items: dict[DeviceCategory, QTreeWidgetItem] = {}
        self._device_items: dict[str, QTreeWidgetItem] = {}
        self._category_icon = _make_icon("#3c78b4", "▦")
        self._device_icon = _make_icon("#6d9fca", "•")
        self._warning_icon = _make_icon("#e6a21a", "!")

    def set_devices(self, devices: list[Device]) -> None:
        expanded_categories = {
            category: item.isExpanded() for category, item in self._category_items.items()
        }
        selected_id = self.selected_device.device_id if self.selected_device else None
        self.clear()
        self._category_items.clear()
        self._device_items.clear()
        grouped: dict[DeviceCategory, list[Device]] = {category: [] for category in CATEGORY_ORDER}
        for device in devices:
            grouped.setdefault(device.category, []).append(device)

        for category in CATEGORY_ORDER:
            category_devices = grouped.get(category, [])
            category_item = QTreeWidgetItem([f"{category.label} ({len(category_devices)})"])
            category_item.setIcon(0, self._category_icon)
            category_item.setData(0, _ROLE_DEVICE, None)
            category_item.setExpanded(expanded_categories.get(category, True))
            self.addTopLevelItem(category_item)
            self._category_items[category] = category_item
            for device in category_devices:
                device_item = QTreeWidgetItem([device.display_name])
                device_item.setData(0, _ROLE_DEVICE, device)
                device_item.setToolTip(0, device.summary)
                device_item.setIcon(
                    0,
                    self._warning_icon if device.status is DeviceStatus.WARNING else self._device_icon,
                )
                category_item.addChild(device_item)
                self._device_items[device.device_id] = device_item

        if selected_id and selected_id in self._device_items:
            self.setCurrentItem(self._device_items[selected_id])
        elif devices:
            first_category = next(
                (self._category_items[category] for category in CATEGORY_ORDER if grouped.get(category)),
                None,
            )
            if first_category is not None and first_category.childCount():
                self.setCurrentItem(first_category.child(0))

    @property
    def selected_device(self) -> Device | None:
        item = self.currentItem()
        if item is None:
            return None
        device = item.data(0, _ROLE_DEVICE)
        return device if isinstance(device, Device) else None

    def _on_selection_changed(self) -> None:
        self.device_selected.emit(self.selected_device)

    def _on_item_activated(self, item: QTreeWidgetItem, _column: int) -> None:
        device = item.data(0, _ROLE_DEVICE)
        if isinstance(device, Device):
            self.device_activated.emit(device)
