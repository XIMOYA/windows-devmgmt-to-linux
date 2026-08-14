# tests/test_linux_tools.py
# 验证可选 lspci/lsusb 工具的纯文本解析和 PCI 分类映射。

from __future__ import annotations

import unittest

from linux_device_manager.models import DeviceCategory
from linux_device_manager.providers.linux_tools import (
    parse_lspci_mm,
    parse_lsusb,
    pci_category,
)


class LinuxToolParserTests(unittest.TestCase):
    def test_parse_lspci_mm_keeps_readable_names_and_ids(self) -> None:
        output = (
            '0000:01:00.0 "VGA compatible controller [0300]" '
            '"Advanced Micro Devices, Inc. [AMD/ATI] [1002]" '
            '"Ellesmere [Radeon RX 590] [67df]" -re1 -p00 '
            '"Sapphire Technology Limited [1da2]" "Nitro+ Radeon RX 590 [e366]"\n'
        )
        records = parse_lspci_mm(output)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.address, "0000:01:00.0")
        self.assertEqual(record.class_code, "0300")
        self.assertEqual(record.vendor_id, "1002")
        self.assertEqual(record.device_id, "67df")
        self.assertIn("Radeon RX 590", record.display_name)
        self.assertEqual(record.hardware_id, "PCI\\VEN_1002&DEV_67DF")

    def test_parse_lsusb_keeps_bus_address_and_hardware_id(self) -> None:
        records = parse_lsusb("Bus 001 Device 004: ID 1c4f:5cb2 SiGma Micro GAME KEYBOARD\n")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].address, "Bus 001, Device 004")
        self.assertEqual(records[0].hardware_id, "USB\\VID_1C4F&PID_5CB2")
        self.assertEqual(records[0].name, "SiGma Micro GAME KEYBOARD")

    def test_pci_category_maps_common_real_machine_classes(self) -> None:
        self.assertIs(pci_category("0300"), DeviceCategory.DISPLAY)
        self.assertIs(pci_category("0200"), DeviceCategory.NETWORK)
        self.assertIs(pci_category("0c03"), DeviceCategory.USB)
        self.assertIs(pci_category("0403"), DeviceCategory.AUDIO)
        self.assertIs(pci_category("0600"), DeviceCategory.SYSTEM)


if __name__ == "__main__":
    unittest.main()
