# src/linux_device_manager/providers/base.py
# 定义设备数据源接口，让真实 Linux 采集和演示数据共用同一套模型。

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from linux_device_manager.models import Device


@dataclass(slots=True)
class DiscoveryResult:
    """一次设备扫描的结果和可恢复错误。"""

    devices: list[Device] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DeviceProvider(Protocol):
    """设备数据源需要实现的最小接口。"""

    def discover(self) -> DiscoveryResult:
        """读取设备并返回统一结果。"""
        ...
