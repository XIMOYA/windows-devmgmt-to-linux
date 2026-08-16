# src/linux_device_manager/ui/device_tree.py
# 以 Windows 设备管理器的树形结构展示设备分类和设备状态。

from __future__ import annotations

from linux_device_manager.qt_compat import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
    QSize,
    QTreeWidget,
    QTreeWidgetItem,
    Qt,
    Signal,
)

from linux_device_manager.models import CATEGORY_ORDER, Device, DeviceCategory, DeviceStatus


_ROLE_DEVICE = Qt.ItemDataRole.UserRole


def _make_icon(color: str, label: str) -> QIcon:
    """绘制不依赖特殊 Unicode 字体的分类图标。"""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, 22, 22, 4, 4)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(7 if len(label) > 2 else 11)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label)
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
        self.setIconSize(QSize(24, 24))
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_activated)
        self._category_items: dict[DeviceCategory, QTreeWidgetItem] = {}
        self._device_items: dict[str, QTreeWidgetItem] = {}
        self._filter_text = ""
        self._root_item: QTreeWidgetItem | None = None
        self._host_item: QTreeWidgetItem | None = None
        icon_styles = {
            DeviceCategory.PROCESSORS: ("#4472c4", "CPU"),
            DeviceCategory.DISPLAY: ("#7654a6", "GPU"),
            DeviceCategory.DISKS: ("#5b7f95", "HDD"),
            DeviceCategory.NETWORK: ("#2e8b72", "NET"),
            DeviceCategory.USB: ("#a66a2c", "USB"),
            DeviceCategory.AUDIO: ("#9a4d72", "AUD"),
            DeviceCategory.INPUT: ("#68758a", "IN"),
            DeviceCategory.SYSTEM: ("#547080", "SYS"),
            DeviceCategory.UNKNOWN: ("#b47820", "!"),
        }
        self._category_icons = {
            category: _make_icon(*icon_styles[category]) for category in CATEGORY_ORDER
        }
        self._warning_icon = _make_icon("#c4771a", "!")
        self._unknown_icon = _make_icon("#7d8792", "?")

    def set_devices(self, devices: list[Device], host_name: str = "此电脑") -> None:
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

        self._root_item = QTreeWidgetItem(["设备管理器"])
        self._root_item.setIcon(0, self._category_icons[DeviceCategory.SYSTEM])
        self._root_item.setData(0, _ROLE_DEVICE, None)
        self._root_item.setExpanded(True)
        self.addTopLevelItem(self._root_item)

        self._host_item = QTreeWidgetItem([host_name or "此电脑"])
        self._host_item.setIcon(0, self._category_icons[DeviceCategory.SYSTEM])
        self._host_item.setData(0, _ROLE_DEVICE, None)
        self._host_item.setExpanded(True)
        self._root_item.addChild(self._host_item)

        for category in CATEGORY_ORDER:
            category_devices = grouped.get(category, [])
            category_item = QTreeWidgetItem([category.label])
            category_item.setIcon(0, self._category_icons[category])
            category_item.setData(0, _ROLE_DEVICE, None)
            category_item.setToolTip(0, f"{category.label}：{len(category_devices)} 个设备")
            category_item.setExpanded(expanded_categories.get(category, True))
            self._host_item.addChild(category_item)
            self._category_items[category] = category_item
            for device in category_devices:
                device_item = QTreeWidgetItem([device.display_name])
                device_item.setData(0, _ROLE_DEVICE, device)
                device_item.setToolTip(0, f"{device.summary}\n{device.vendor or '厂商信息不可用'}")
                if device.status is DeviceStatus.WARNING:
                    icon = self._warning_icon
                elif device.status is DeviceStatus.UNKNOWN:
                    icon = self._unknown_icon
                else:
                    icon = self._category_icons[category]
                device_item.setIcon(0, icon)
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
        self.set_filter_text(self._filter_text)

    def set_filter_text(self, text: str) -> None:
        """按设备常用字段过滤，隐藏不匹配设备和空分类。"""
        self._filter_text = text.casefold().strip()
        for category, category_item in self._category_items.items():
            visible_count = 0
            for row in range(category_item.childCount()):
                item = category_item.child(row)
                device = item.data(0, _ROLE_DEVICE)
                visible = isinstance(device, Device) and self._matches_filter(device)
                item.setHidden(not visible)
                visible_count += int(visible)
            category_item.setHidden(bool(self._filter_text) and visible_count == 0)
            if self._filter_text and visible_count:
                category_item.setExpanded(True)
        if self._host_item is not None and self._root_item is not None:
            visible_categories = sum(
                not self._category_items[category].isHidden() for category in CATEGORY_ORDER
            )
            hidden = bool(self._filter_text) and visible_categories == 0
            self._host_item.setHidden(hidden)
            self._root_item.setHidden(hidden)
        current = self.currentItem()
        if current is not None and not current.isHidden():
            return
        for item in self._device_items.values():
            if not item.isHidden():
                self.setCurrentItem(item)
                return
        self.clearSelection()

    def _matches_filter(self, device: Device) -> bool:
        if not self._filter_text:
            return True
        fields = [
            device.name,
            device.vendor,
            device.model,
            device.driver,
            device.location,
            device.source_path,
            device.category.label,
            device.summary,
            *(f"{key} {value}" for key, value in device.property_items()),
        ]
        return self._filter_text in " ".join(fields).casefold()

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
