# tests/test_providers.py
# 验证 Mock 数据和 Linux Provider 在缺失路径/临时 sysfs 下的容错行为。

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from linux_device_manager.models import DeviceCategory, DeviceStatus
from linux_device_manager.providers.linux import LinuxDeviceProvider
from linux_device_manager.providers.mock import MockDeviceProvider


class ProviderTests(unittest.TestCase):
    def test_mock_provider_covers_categories_and_warning_device(self) -> None:
        result = MockDeviceProvider().discover()
        categories = {device.category for device in result.devices}
        self.assertIn(DeviceCategory.DISPLAY, categories)
        self.assertIn(DeviceCategory.UNKNOWN, categories)
        self.assertTrue(any(device.status is DeviceStatus.WARNING for device in result.devices))
        self.assertEqual(result.errors, [])

    def test_linux_provider_handles_missing_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = LinuxDeviceProvider(
                sys_root=Path(directory) / "missing-sys",
                proc_root=Path(directory) / "missing-proc",
            ).discover()
        self.assertEqual(result.devices, [])
        self.assertTrue(result.errors)

    def test_linux_provider_reads_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc"
            sys = root / "sys"
            (proc).mkdir()
            (sys / "class" / "net" / "eth0" / "device").mkdir(parents=True)
            (sys / "block" / "sda" / "device").mkdir(parents=True)
            (proc / "cpuinfo").write_text(
                "processor\t: 0\nmodel name\t: Fixture CPU\nvendor_id\t: FixtureVendor\ncpu MHz\t: 2400.000\n",
                encoding="utf-8",
            )
            (sys / "class" / "net" / "eth0" / "operstate").write_text("up\n", encoding="utf-8")
            (sys / "class" / "net" / "eth0" / "address").write_text("00:11:22:33:44:55\n", encoding="utf-8")
            (sys / "block" / "sda" / "size").write_text("2097152\n", encoding="utf-8")
            result = LinuxDeviceProvider(sys_root=sys, proc_root=proc).discover()

        self.assertFalse(result.errors)
        self.assertTrue(any(device.name == "Fixture CPU" for device in result.devices))
        network = next(device for device in result.devices if device.category is DeviceCategory.NETWORK)
        self.assertEqual(network.properties["接口状态"], "up")
        disk = next(device for device in result.devices if device.category is DeviceCategory.DISKS)
        self.assertEqual(disk.properties["容量"], "1.00 GiB")

    def test_linux_provider_can_use_injected_pci_command_without_host_leakage(self) -> None:
        lspci_output = (
            '0000:02:00.0 "Ethernet controller [0200]" "Fixture Vendor [1234]" '
            '"Fixture Ethernet [5678]" -p00 "Fixture Board [4321]" "Device [8765]"\n'
        )

        def runner(command: tuple[str, ...]) -> str:
            return lspci_output if command[0] == "lspci" else ""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc"
            sys = root / "sys"
            proc.mkdir()
            sys.mkdir()
            result = LinuxDeviceProvider(
                sys_root=sys,
                proc_root=proc,
                command_runner=runner,
                use_external_tools=True,
            ).discover()

        fixture_devices = [device for device in result.devices if "Fixture Ethernet" in device.name]
        self.assertEqual(len(fixture_devices), 1)
        self.assertEqual(fixture_devices[0].category, DeviceCategory.NETWORK)
        self.assertEqual(fixture_devices[0].properties["硬件 ID"], "PCI\\VEN_1234&DEV_5678")


if __name__ == "__main__":
    unittest.main()
