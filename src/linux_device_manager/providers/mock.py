# src/linux_device_manager/providers/mock.py
# 提供稳定的演示设备，方便在 Windows 开发机和录制视频时复现完整界面。

from __future__ import annotations

from linux_device_manager.models import Device, DeviceCategory, DeviceStatus
from linux_device_manager.providers.base import DiscoveryResult


class MockDeviceProvider:
    """返回不接触真实硬件的演示数据。"""

    def discover(self) -> DiscoveryResult:
        devices = [
            Device(
                device_id="mock:cpu:0",
                name="AMD Ryzen 7 7800X3D",
                category=DeviceCategory.PROCESSORS,
                vendor="Advanced Micro Devices, Inc.",
                model="Ryzen 7 7800X3D 8-Core Processor",
                bus="处理器总线",
                driver="未知（由内核管理）",
                location="CPU 0",
                source_path="演示数据",
                properties={
                    "逻辑处理器": "16",
                    "架构": "x86_64",
                    "频率": "4.20 GHz",
                },
            ),
            Device(
                device_id="mock:display:0",
                name="NVIDIA GeForce RTX 4070",
                category=DeviceCategory.DISPLAY,
                vendor="NVIDIA Corporation",
                model="GeForce RTX 4070",
                bus="PCI Express",
                driver="nvidia",
                location="PCI bus 1, device 0, function 0",
                source_path="演示数据",
                properties={
                    "显存": "12 GB",
                    "渲染接口": "Vulkan / OpenGL",
                    "显示器": "DEMO-4K @ 144Hz",
                },
            ),
            Device(
                device_id="mock:disk:0",
                name="Samsung SSD 980 PRO 1TB",
                category=DeviceCategory.DISKS,
                vendor="Samsung",
                model="SSD 980 PRO 1TB",
                bus="NVMe",
                driver="nvme",
                location="/dev/nvme0n1",
                source_path="演示数据",
                properties={"容量": "953.87 GiB", "介质类型": "固态硬盘"},
            ),
            Device(
                device_id="mock:network:0",
                name="Intel(R) Ethernet Controller",
                category=DeviceCategory.NETWORK,
                vendor="Intel Corporation",
                model="Ethernet Controller",
                bus="PCI Express",
                driver="igc",
                location="enp5s0",
                source_path="演示数据",
                properties={"接口状态": "已连接", "MAC 地址": "02:00:5e:10:00:01"},
            ),
            Device(
                device_id="mock:usb:0",
                name="USB Composite Device",
                category=DeviceCategory.USB,
                vendor="演示设备制造商",
                model="USB Composite Device",
                bus="USB 3.0",
                driver="usbhid",
                location="Bus 001, Port 2",
                source_path="演示数据",
                properties={"速度": "5000M", "电源": "100mA"},
            ),
            Device(
                device_id="mock:audio:0",
                name="High Definition Audio Controller",
                category=DeviceCategory.AUDIO,
                vendor="Realtek Semiconductor",
                model="High Definition Audio",
                bus="PCI Express",
                driver="snd_hda_intel",
                location="card 0",
                source_path="演示数据",
                properties={"编解码器": "Realtek ALC1220", "状态": "已启用"},
            ),
            Device(
                device_id="mock:input:0",
                name="Windows 风格机械键盘（演示）",
                category=DeviceCategory.INPUT,
                vendor="Demo Hardware",
                model="Mechanical Keyboard",
                bus="USB",
                driver="usbhid",
                location="/dev/input/event3",
                source_path="演示数据",
                properties={"输入节点": "/dev/input/event3", "按键数量": "104"},
            ),
            Device(
                device_id="mock:system:0",
                name="ACPI-Compliant System",
                category=DeviceCategory.SYSTEM,
                vendor="ACPI",
                model="ACPI-Compliant System",
                bus="ACPI",
                driver="acpi",
                location="ACPI 0",
                source_path="演示数据",
                properties={"电源管理": "已启用"},
            ),
            Device(
                device_id="mock:unknown:0",
                name="未知 PCI 设备",
                category=DeviceCategory.UNKNOWN,
                status=DeviceStatus.WARNING,
                vendor="未知",
                model="PCI device 1af4:1001",
                bus="PCI Express",
                location="PCI bus 4, device 0, function 0",
                source_path="演示数据",
                driver_problem="没有安装这个设备的驱动程序。",
                properties={
                    "硬件 ID": "PCI\\VEN_1AF4&DEV_1001",
                    "问题代码": "代码 28",
                },
            ),
        ]
        return DiscoveryResult(devices=devices)
