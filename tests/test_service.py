# tests/test_service.py
# 验证后台设备刷新服务的并发保护、排序和异常隔离。

from __future__ import annotations

import threading
import unittest

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from linux_device_manager.models import Device, DeviceCategory
from linux_device_manager.providers.base import DiscoveryResult
from linux_device_manager.services.device_service import DeviceRefreshService


class _BlockingProvider:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def discover(self) -> DiscoveryResult:
        self.started.set()
        self.release.wait(timeout=2)
        return DiscoveryResult(
            devices=[
                Device("network", "网卡", DeviceCategory.NETWORK),
                Device("cpu", "处理器", DeviceCategory.PROCESSORS),
            ]
        )


class _FailingProvider:
    def discover(self) -> DiscoveryResult:
        raise RuntimeError("fixture failure")


class DeviceRefreshServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QCoreApplication.instance() or QCoreApplication([])

    def test_refresh_rejects_concurrent_request_and_sorts_result(self) -> None:
        provider = _BlockingProvider()
        service = DeviceRefreshService(provider)
        completed: list[DiscoveryResult] = []
        loop = QEventLoop()
        service.completed.connect(lambda result: (completed.append(result), loop.quit()))

        self.assertTrue(service.refresh())
        self.assertTrue(provider.started.wait(timeout=1))
        self.assertFalse(service.refresh())
        provider.release.set()
        QTimer.singleShot(2500, loop.quit)
        loop.exec()

        self.assertEqual(len(completed), 1)
        self.assertFalse(service.running)
        self.assertEqual(
            [device.category for device in completed[0].devices],
            [DeviceCategory.PROCESSORS, DeviceCategory.NETWORK],
        )

    def test_provider_exception_is_reported_as_discovery_error(self) -> None:
        service = DeviceRefreshService(_FailingProvider())
        completed: list[DiscoveryResult] = []
        loop = QEventLoop()
        service.completed.connect(lambda result: (completed.append(result), loop.quit()))

        self.assertTrue(service.refresh())
        QTimer.singleShot(2500, loop.quit)
        loop.exec()

        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].devices, [])
        self.assertIn("设备扫描失败：RuntimeError: fixture failure", completed[0].errors)


if __name__ == "__main__":
    unittest.main()
