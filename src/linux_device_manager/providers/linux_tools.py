# src/linux_device_manager/providers/linux_tools.py
# 可选的 lspci/lsusb 解析与只读命令执行，缺少工具时安全降级。

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from linux_device_manager.models import DeviceCategory


CommandRunner = Callable[[Sequence[str]], str]


@dataclass(frozen=True, slots=True)
class PciDeviceInfo:
    address: str
    class_code: str
    class_name: str
    vendor_id: str
    vendor: str
    device_id: str
    device: str
    revision: str = ""
    programming_interface: str = ""
    subsystem_vendor_id: str = ""
    subsystem_vendor: str = ""
    subsystem_device_id: str = ""
    subsystem_device: str = ""

    @property
    def display_name(self) -> str:
        if not self.vendor:
            return self.device or self.class_name or self.address
        if not self.device:
            return self.vendor
        if self.vendor.casefold() in self.device.casefold():
            return self.device
        return f"{self.vendor} {self.device}"

    @property
    def hardware_id(self) -> str:
        if not self.vendor_id or not self.device_id:
            return ""
        return f"PCI\\VEN_{self.vendor_id.upper()}&DEV_{self.device_id.upper()}"

    @property
    def subsystem(self) -> str:
        if not self.subsystem_vendor and not self.subsystem_device:
            return ""
        return " ".join(part for part in (self.subsystem_vendor, self.subsystem_device) if part)


@dataclass(frozen=True, slots=True)
class UsbDeviceInfo:
    bus: str
    device: str
    vendor_id: str
    product_id: str
    name: str

    @property
    def hardware_id(self) -> str:
        return f"USB\\VID_{self.vendor_id.upper()}&PID_{self.product_id.upper()}"

    @property
    def address(self) -> str:
        return f"Bus {self.bus}, Device {self.device}"


def run_readonly_command(command: Sequence[str], *, timeout: float = 2.5) -> str:
    """执行无 shell 的只读命令；工具不可用或失败时返回空字符串。"""
    if not command:
        return ""
    executable = shutil.which(command[0])
    if executable is None:
        return ""
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0 and not completed.stdout:
        return ""
    return completed.stdout


def parse_lspci_mm(output: str) -> list[PciDeviceInfo]:
    """解析 `lspci -D -mm -nn` 的一行一设备输出。"""
    records: list[PciDeviceInfo] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            fields = shlex.split(line, comments=False, posix=True)
        except ValueError:
            continue
        if len(fields) < 4:
            continue
        class_name, class_code = _split_hex_id(fields[1], 4)
        vendor, vendor_id = _split_hex_id(fields[2], 4)
        device, device_id = _split_hex_id(fields[3], 4)
        revision = ""
        programming_interface = ""
        for field in fields[4:]:
            if field.startswith("-r"):
                revision = field[2:]
            elif field.startswith("-p"):
                programming_interface = field[2:]
        subsystem_vendor = ""
        subsystem_vendor_id = ""
        subsystem_device = ""
        subsystem_device_id = ""
        if len(fields) >= 6:
            subsystem_vendor, subsystem_vendor_id = _split_hex_id(fields[-2], 4)
            subsystem_device, subsystem_device_id = _split_hex_id(fields[-1], 4)
        if not fields[0]:
            continue
        records.append(
            PciDeviceInfo(
                address=fields[0],
                class_code=class_code.lower(),
                class_name=_clean_revision(class_name),
                vendor_id=vendor_id.lower(),
                vendor=_clean_revision(vendor),
                device_id=device_id.lower(),
                device=_clean_revision(device),
                revision=revision,
                programming_interface=programming_interface,
                subsystem_vendor_id=subsystem_vendor_id.lower(),
                subsystem_vendor=_clean_revision(subsystem_vendor),
                subsystem_device_id=subsystem_device_id.lower(),
                subsystem_device=_clean_revision(subsystem_device),
            )
        )
    return records


def parse_lsusb(output: str) -> list[UsbDeviceInfo]:
    """解析 `lsusb` 的简洁输出。"""
    records: list[UsbDeviceInfo] = []
    pattern = re.compile(
        r"^Bus\s+(?P<bus>\d{1,3})\s+Device\s+(?P<device>\d{1,3}):\s+"
        r"ID\s+(?P<vendor>[0-9a-fA-F]{4}):(?P<product>[0-9a-fA-F]{4})\s*(?P<name>.*)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match is None:
            continue
        records.append(
            UsbDeviceInfo(
                bus=match.group("bus").zfill(3),
                device=match.group("device").zfill(3),
                vendor_id=match.group("vendor").lower(),
                product_id=match.group("product").lower(),
                name=match.group("name").strip(),
            )
        )
    return records


def pci_category(class_code: str) -> DeviceCategory:
    """把 PCI 类别代码映射为设备管理器分类。"""
    normalized = class_code.lower()
    if normalized.startswith("03"):
        return DeviceCategory.DISPLAY
    if normalized.startswith("02"):
        return DeviceCategory.NETWORK
    if normalized == "0c03":
        return DeviceCategory.USB
    if normalized.startswith("04"):
        return DeviceCategory.AUDIO
    return DeviceCategory.SYSTEM


def _split_hex_id(value: str, width: int) -> tuple[str, str]:
    match = re.search(rf"\s*\[([0-9a-fA-F]{{{width}}})\]\s*$", value)
    if match is None:
        return _clean_revision(value), ""
    text = value[: match.start()].strip()
    return text, match.group(1)


def _clean_revision(value: str) -> str:
    return re.sub(r"\s+\(rev\s+[^)]+\)\s*$", "", value).strip()
