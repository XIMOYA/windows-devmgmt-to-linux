# tests/test_dialogs.py
# 验证经典属性页和更新驱动向导的页面结构与安全边界。

from __future__ import annotations

import unittest

from linux_device_manager.models import DeviceStatus
from linux_device_manager.providers.mock import MockDeviceProvider
from linux_device_manager.qt_compat import QApplication
from linux_device_manager.ui.device_tree import DeviceTree
from linux_device_manager.ui.driver_wizard import DriverUpdateWizard
from linux_device_manager.ui.properties_dialog import DevicePropertiesDialog


class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_device_tree_has_windows_style_root_and_host_nodes(self) -> None:
        tree = DeviceTree()
        devices = MockDeviceProvider().discover().devices
        tree.set_devices(devices, host_name="DEVMGMT-LINUX")

        self.assertEqual(tree.topLevelItemCount(), 1)
        self.assertEqual(tree.topLevelItem(0).text(0), "设备管理器")
        self.assertEqual(tree.topLevelItem(0).child(0).text(0), "DEVMGMT-LINUX")
        self.assertEqual(len(tree._device_items), 9)

    def test_properties_dialog_contains_four_tabs_and_driver_actions(self) -> None:
        device = MockDeviceProvider().discover().devices[0]
        dialog = DevicePropertiesDialog(device)

        self.assertEqual(dialog.tabs.count(), 4)
        self.assertEqual(
            [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())],
            ["常规", "驱动程序", "详细信息", "事件"],
        )
        self.assertGreaterEqual(dialog.detail_selector.count(), 9)
        dialog.detail_selector.setCurrentText("设备描述")
        self.assertEqual(dialog.detail_value.toPlainText(), device.name)
        self.assertTrue(dialog.driver_update_button.isEnabled())
        self.assertFalse(dialog.driver_disable_button.isEnabled())
        self.assertIn("设备运行正常", dialog.status_edit.toPlainText())

    def test_driver_wizard_reaches_simulated_result_without_installing(self) -> None:
        device = MockDeviceProvider().discover().devices[-1]
        self.assertIs(device.status, DeviceStatus.WARNING)
        wizard = DriverUpdateWizard(device)

        self.assertEqual(wizard.page_count, 5)
        wizard._set_page(0)
        wizard.auto_radio.setChecked(True)
        wizard._go_next()
        self.assertEqual(wizard.current_page, 3)
        wizard._timer.stop()
        wizard._set_page(4)
        self.assertIn("找不到更好的驱动程序", wizard.result_title.text())
        self.assertEqual(wizard.path_edit.text(), "C:\\Windows\\System32\\DriverStore")
        wizard.close()


if __name__ == "__main__":
    unittest.main()
