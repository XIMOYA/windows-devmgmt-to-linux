# src/linux_device_manager/models.py
# 设备管理器领域模型：设备分类、状态和统一设备对象。

"""设备管理器领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class DeviceCategory(str, Enum):
    """设备管理器左侧树中的分类。"""

    PROCESSORS = "处理器"
    DISPLAY = "显示适配器"
    DISKS = "磁盘驱动器"
    NETWORK = "网络适配器"
    USB = "通用串行总线控制器"
    AUDIO = "音频输入和输出"
    INPUT = "键盘、鼠标和其他指针设备"
    SYSTEM = "系统设备"
    UNKNOWN = "其他设备"

    @property
    def label(self) -> str:
        return self.value


class DeviceStatus(str, Enum):
    """设备在设备管理器中的展示状态。"""

    OK = "正常工作"
    WARNING = "需要注意"
    UNKNOWN = "状态未知"


@dataclass(frozen=True, slots=True)
class Device:
    """跨数据源使用的只读设备描述。"""

    device_id: str
    name: str
    category: DeviceCategory
    status: DeviceStatus = DeviceStatus.OK
    vendor: str = ""
    model: str = ""
    bus: str = ""
    driver: str = ""
    location: str = ""
    source_path: str = ""
    properties: Mapping[str, str] = field(default_factory=dict)
    driver_problem: str = ""

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def summary(self) -> str:
        if self.status is DeviceStatus.OK:
            return "设备运行正常"
        if self.driver_problem:
            return self.driver_problem
        return self.status.value

    def property_items(self) -> list[tuple[str, str]]:
        """返回稳定排序的属性项，供表格和复制功能复用。"""
        return sorted((str(key), str(value)) for key, value in self.properties.items())

    def as_text(self) -> str:
        """生成适合复制到剪贴板的设备详情。"""
        lines = [
            f"设备名称：{self.name}",
            f"设备类别：{self.category.label}",
            f"状态：{self.summary}",
            f"厂商：{self.vendor or '信息不可用'}",
            f"型号：{self.model or '信息不可用'}",
            f"总线：{self.bus or '信息不可用'}",
            f"驱动：{self.driver or '信息不可用'}",
            f"位置：{self.location or '信息不可用'}",
            f"来源：{self.source_path or '信息不可用'}",
        ]
        lines.extend(f"{key}：{value}" for key, value in self.property_items())
        return "\n".join(lines)


CATEGORY_ORDER: tuple[DeviceCategory, ...] = tuple(DeviceCategory)


def sort_devices(devices: list[Device]) -> list[Device]:
    """按设备管理器的分类顺序和显示名称排序。"""
    category_index = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    return sorted(
        devices,
        key=lambda device: (
            category_index.get(device.category, len(CATEGORY_ORDER)),
            device.name.casefold(),
            device.device_id,
        ),
    )
