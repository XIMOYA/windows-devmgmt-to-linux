# tests/test_ui.py
# 验证 Qt 绑定兼容、设备树筛选和详情面板长字段布局。

from __future__ import annotations

import unittest

from linux_device_manager.models import Device, DeviceCategory
from linux_device_manager.providers.mock import MockDeviceProvider
from linux_device_manager.qt_compat import QApplication, QCoreApplication
from linux_device_manager.ui.details_panel import DetailsPanel
from linux_device_manager.ui.device_tree import DeviceTree


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_device_tree_filters_by_hardware_fields(self) -> None:
        tree = DeviceTree()
        devices = MockDeviceProvider().discover().devices
        tree.set_devices(devices)
        tree.set_filter_text("NVIDIA")
        visible = [item for item in tree._device_items.values() if not item.isHidden()]
        self.assertEqual(len(visible), 1)
        self.assertIn("NVIDIA", visible[0].text(0))
        tree.set_filter_text("")
        self.assertEqual(len([item for item in tree._device_items.values() if not item.isHidden()]), 9)

    def test_details_panel_keeps_device_id_and_long_values_readable(self) -> None:
        panel = DetailsPanel()
        device = Device(
            device_id="linux:pci:0000:01:00.0",
            name="Advanced Micro Devices, Inc. [AMD/ATI] Ellesmere Radeon RX 590",
            category=DeviceCategory.DISPLAY,
            vendor="Advanced Micro Devices, Inc. [AMD/ATI]",
            model="Ellesmere [Radeon RX 470/480/570/580/590]",
            bus="PCI Express",
            driver="amdgpu",
            location="0000:01:00.0",
            source_path="/sys/class/drm/card0",
            properties={"硬件 ID": "PCI\\VEN_1002&DEV_67DF"},
        )
        panel.set_device(device)
        self.assertEqual(panel.device_id_value.text(), device.device_id)
        self.assertEqual(panel.source_value.text(), device.source_path)
        self.assertEqual(panel.properties_table.rowCount(), 3)
        self.assertEqual(
            panel.vendor_value.sizePolicy().horizontalPolicy().name,
            "Expanding",
        )


if __name__ == "__main__":
    unittest.main()
