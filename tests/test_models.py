# tests/test_models.py
# 验证设备模型的状态摘要、详情文本和稳定排序。

from __future__ import annotations

import unittest

from linux_device_manager.models import Device, DeviceCategory, DeviceStatus, sort_devices


class DeviceModelTests(unittest.TestCase):
    def test_warning_device_uses_driver_problem_in_summary(self) -> None:
        device = Device(
            device_id="unknown-1",
            name="未知设备",
            category=DeviceCategory.UNKNOWN,
            status=DeviceStatus.WARNING,
            driver_problem="没有安装驱动程序。",
        )
        self.assertEqual(device.summary, "没有安装驱动程序。")

    def test_as_text_contains_common_fields_and_properties(self) -> None:
        device = Device(
            device_id="net-1",
            name="测试网卡",
            category=DeviceCategory.NETWORK,
            vendor="测试厂商",
            properties={"MAC 地址": "00:11:22:33:44:55"},
        )
        text = device.as_text()
        self.assertIn("设备名称：测试网卡", text)
        self.assertIn("设备类别：网络适配器", text)
        self.assertIn("MAC 地址：00:11:22:33:44:55", text)

    def test_sort_devices_uses_category_order_before_name(self) -> None:
        devices = [
            Device("network", "乙网卡", DeviceCategory.NETWORK),
            Device("cpu", "处理器", DeviceCategory.PROCESSORS),
            Device("display", "显卡", DeviceCategory.DISPLAY),
        ]
        sorted_devices = sort_devices(devices)
        self.assertEqual(
            [device.category for device in sorted_devices],
            [DeviceCategory.PROCESSORS, DeviceCategory.DISPLAY, DeviceCategory.NETWORK],
        )


if __name__ == "__main__":
    unittest.main()
