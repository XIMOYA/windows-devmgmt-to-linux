# src/linux_device_manager/providers/linux.py
# 只读采集 Linux 的 /sys 和 /proc 硬件信息，并转换成统一设备模型。

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Iterable

from linux_device_manager.models import Device, DeviceCategory
from linux_device_manager.providers.base import DiscoveryResult


class LinuxDeviceProvider:
    """从 Linux 标准虚拟文件系统发现设备。"""

    def __init__(
        self,
        *,
        sys_root: str | os.PathLike[str] = "/sys",
        proc_root: str | os.PathLike[str] = "/proc",
    ) -> None:
        self.sys_root = Path(sys_root)
        self.proc_root = Path(proc_root)

    def discover(self) -> DiscoveryResult:
        devices: list[Device] = []
        errors: list[str] = []
        collectors = (
            ("处理器", self._collect_processors),
            ("显示适配器", self._collect_display),
            ("磁盘驱动器", self._collect_disks),
            ("网络适配器", self._collect_network),
            ("通用串行总线控制器", self._collect_usb),
            ("音频输入和输出", self._collect_audio),
            ("键盘、鼠标和其他指针设备", self._collect_input),
            ("系统设备", self._collect_system),
        )
        for label, collector in collectors:
            try:
                devices.extend(collector())
            except OSError as exc:
                errors.append(f"{label}读取失败：{exc}")
            except Exception as exc:  # 保护 UI 不被单类硬件异常拖垮
                errors.append(f"{label}读取失败：{type(exc).__name__}: {exc}")

        if not devices:
            errors.append("未发现可读取的 Linux 设备信息。")
        return DiscoveryResult(devices=devices, errors=errors)

    def _collect_processors(self) -> list[Device]:
        cpuinfo_path = self.proc_root / "cpuinfo"
        if not self.proc_root.exists():
            return []
        cpuinfo = self._read_text(cpuinfo_path)
        if not cpuinfo:
            return [
                Device(
                    device_id="linux:cpu:0",
                    name=platform.processor() or "Linux 处理器",
                    category=DeviceCategory.PROCESSORS,
                    driver="内核管理",
                    source_path=str(cpuinfo_path),
                )
            ]

        fields: dict[str, str] = {}
        for line in cpuinfo.splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() in {"model name", "Hardware", "vendor_id", "cpu MHz"}:
                fields.setdefault(key.strip(), value.strip())
        model = fields.get("model name") or fields.get("Hardware") or platform.processor() or "Linux 处理器"
        logical_count = sum(1 for line in cpuinfo.splitlines() if line.startswith("processor"))
        return [
            Device(
                device_id="linux:cpu:0",
                name=model,
                category=DeviceCategory.PROCESSORS,
                vendor=fields.get("vendor_id", ""),
                model=model,
                bus="处理器总线",
                driver="内核管理",
                location="CPU 0",
                source_path=str(self.proc_root / "cpuinfo"),
                properties={
                    "逻辑处理器": str(logical_count or os.cpu_count() or "信息不可用"),
                    "架构": platform.machine(),
                    "频率": f"{fields['cpu MHz']} MHz" if fields.get("cpu MHz") else "信息不可用",
                },
            )
        ]

    def _collect_display(self) -> list[Device]:
        devices: list[Device] = []
        drm_root = self.sys_root / "class" / "drm"
        for path in self._directories(drm_root):
            if not path.name.startswith("card") or "-" in path.name:
                continue
            device_path = self._resolve_device_path(path / "device")
            vendor = self._read_text(device_path / "vendor") if device_path else ""
            model = self._read_text(device_path / "device") if device_path else ""
            driver = self._link_name(device_path / "driver") if device_path else ""
            properties = self._read_properties(device_path) if device_path else {}
            devices.append(
                Device(
                    device_id=f"linux:display:{path.name}",
                    name=self._display_name(vendor, model, path.name),
                    category=DeviceCategory.DISPLAY,
                    vendor=vendor,
                    model=model or path.name,
                    bus="PCI / DRM",
                    driver=driver,
                    location=str(path),
                    source_path=str(path),
                    properties=properties,
                )
            )
        return devices

    def _collect_disks(self) -> list[Device]:
        devices: list[Device] = []
        for path in self._directories(self.sys_root / "block"):
            if path.name.startswith(("loop", "ram", "dm-")):
                continue
            device_path = self._resolve_device_path(path / "device")
            model = self._read_text(device_path / "model") if device_path else ""
            vendor = self._read_text(device_path / "vendor") if device_path else ""
            driver = self._link_name(path / "device" / "driver")
            size = self._read_text(path / "size")
            size_text = self._sectors_to_size(size)
            devices.append(
                Device(
                    device_id=f"linux:disk:{path.name}",
                    name=model or f"Linux 磁盘 {path.name}",
                    category=DeviceCategory.DISKS,
                    vendor=vendor,
                    model=model or path.name,
                    bus=self._disk_bus(path),
                    driver=driver,
                    location=f"/dev/{path.name}",
                    source_path=str(path),
                    properties={
                        "设备节点": f"/dev/{path.name}",
                        "容量": size_text,
                        "可移动": self._read_text(path / "removable") or "信息不可用",
                    },
                )
            )
        return devices

    def _collect_network(self) -> list[Device]:
        devices: list[Device] = []
        for path in self._directories(self.sys_root / "class" / "net"):
            if path.name == "lo":
                continue
            device_path = self._resolve_device_path(path / "device")
            vendor = self._read_text(device_path / "vendor") if device_path else ""
            model = self._read_text(device_path / "device") if device_path else ""
            driver = self._link_name(device_path / "driver") if device_path else ""
            devices.append(
                Device(
                    device_id=f"linux:network:{path.name}",
                    name=self._network_name(path.name, model),
                    category=DeviceCategory.NETWORK,
                    vendor=vendor,
                    model=model or path.name,
                    bus="网络接口",
                    driver=driver,
                    location=path.name,
                    source_path=str(path),
                    properties={
                        "接口状态": self._read_text(path / "operstate") or "信息不可用",
                        "MAC 地址": self._read_text(path / "address") or "信息不可用",
                        "速率": f"{self._read_text(path / 'speed')} Mb/s" if self._read_text(path / "speed") else "信息不可用",
                    },
                )
            )
        return devices

    def _collect_usb(self) -> list[Device]:
        devices: list[Device] = []
        usb_root = self.sys_root / "bus" / "usb" / "devices"
        for path in self._directories(usb_root):
            if ":" in path.name or not (path / "idVendor").exists():
                continue
            vendor_id = self._read_text(path / "idVendor")
            product_id = self._read_text(path / "idProduct")
            vendor = self._read_text(path / "manufacturer")
            product = self._read_text(path / "product")
            driver = self._link_name(path / "driver")
            devices.append(
                Device(
                    device_id=f"linux:usb:{path.name}",
                    name=product or f"USB 设备 {vendor_id}:{product_id}",
                    category=DeviceCategory.USB,
                    vendor=vendor or vendor_id,
                    model=product or product_id,
                    bus="USB",
                    driver=driver,
                    location=path.name,
                    source_path=str(path),
                    properties={
                        "厂商 ID": vendor_id,
                        "产品 ID": product_id,
                        "速度": self._read_text(path / "speed") or "信息不可用",
                    },
                )
            )
        return devices

    def _collect_audio(self) -> list[Device]:
        devices: list[Device] = []
        sound_root = self.sys_root / "class" / "sound"
        for path in self._directories(sound_root):
            if not path.name.startswith("card"):
                continue
            device_path = self._resolve_device_path(path / "device")
            driver = self._link_name(device_path / "driver") if device_path else ""
            name = self._read_text(path / "id") or path.name
            devices.append(
                Device(
                    device_id=f"linux:audio:{path.name}",
                    name=f"{name} 音频设备",
                    category=DeviceCategory.AUDIO,
                    model=name,
                    bus="ALSA",
                    driver=driver or "ALSA",
                    location=path.name,
                    source_path=str(path),
                    properties={"ALSA 卡": path.name, "设备名称": name},
                )
            )
        return devices

    def _collect_input(self) -> list[Device]:
        devices: list[Device] = []
        input_root = self.sys_root / "class" / "input"
        for path in self._directories(input_root):
            if not path.name.startswith("event"):
                continue
            device_path = self._resolve_device_path(path / "device")
            name = self._read_text(device_path / "name") if device_path else ""
            if not name:
                name = f"Linux 输入设备 {path.name}"
            category = DeviceCategory.INPUT
            driver = self._link_name(device_path / "driver") if device_path else ""
            devices.append(
                Device(
                    device_id=f"linux:input:{path.name}",
                    name=name,
                    category=category,
                    bus="输入设备",
                    driver=driver,
                    location=f"/dev/input/{path.name}",
                    source_path=str(path),
                    properties={"输入节点": f"/dev/input/{path.name}"},
                )
            )
        return devices

    def _collect_system(self) -> list[Device]:
        devices: list[Device] = []
        for bus_path in self._directories(self.sys_root / "bus"):
            if bus_path.name in {"usb", "input", "block"}:
                continue
            devices.append(
                Device(
                    device_id=f"linux:system:{bus_path.name}",
                    name=f"{bus_path.name.upper()} 系统总线",
                    category=DeviceCategory.SYSTEM,
                    bus=bus_path.name.upper(),
                    driver="内核管理",
                    location=str(bus_path),
                    source_path=str(bus_path),
                    properties={"总线路径": str(bus_path)},
                )
            )
        return devices[:32]

    @staticmethod
    def _directories(path: Path) -> Iterable[Path]:
        try:
            return sorted((item for item in path.iterdir() if item.is_dir()), key=lambda item: item.name)
        except OSError:
            return ()

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace").strip()
        except (OSError, UnicodeError):
            return ""

    def _read_properties(self, path: Path | None) -> dict[str, str]:
        if path is None:
            return {}
        properties: dict[str, str] = {}
        for name in ("modalias", "uevent", "subsystem"):
            value = self._read_text(path / name)
            if value:
                properties[name] = value.replace("\n", "; ")
        return properties

    @staticmethod
    def _resolve_device_path(path: Path) -> Path | None:
        try:
            return path.resolve(strict=True)
        except OSError:
            return None

    @staticmethod
    def _link_name(path: Path) -> str:
        try:
            return path.resolve(strict=True).name
        except OSError:
            return ""

    @staticmethod
    def _display_name(vendor: str, model: str, fallback: str) -> str:
        if vendor and model:
            return f"显示适配器 {vendor} ({model})"
        return f"显示适配器 {fallback}"

    @staticmethod
    def _network_name(interface: str, model: str) -> str:
        return f"{interface} 网络适配器" if not model else f"{interface} 网络适配器 ({model})"

    @staticmethod
    def _sectors_to_size(sectors: str) -> str:
        try:
            value = int(sectors) * 512
        except (TypeError, ValueError):
            return "信息不可用"
        units = ("B", "KiB", "MiB", "GiB", "TiB")
        index = 0
        amount = float(value)
        while amount >= 1024 and index < len(units) - 1:
            amount /= 1024
            index += 1
        return f"{amount:.2f} {units[index]}"

    @staticmethod
    def _disk_bus(path: Path) -> str:
        text = str(path)
        if "nvme" in text:
            return "NVMe"
        if "mmc" in text:
            return "MMC"
        if "usb" in text:
            return "USB"
        return "块设备"
