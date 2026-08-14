# src/linux_device_manager/providers/linux.py
# 只读采集 Linux 的 /sys、/proc 以及可选 lspci/lsusb 硬件信息。

from __future__ import annotations

import os
import platform
import re
import socket
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from linux_device_manager.models import Device, DeviceCategory, DeviceStatus
from linux_device_manager.providers.base import DiscoveryResult
from linux_device_manager.providers.linux_tools import (
    CommandRunner,
    PciDeviceInfo,
    UsbDeviceInfo,
    parse_lspci_mm,
    parse_lsusb,
    pci_category,
    run_readonly_command,
)


_PCI_ADDRESS_RE = re.compile(r"^(?:[0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.\d$")


class LinuxDeviceProvider:
    """从 Linux 标准虚拟文件系统发现设备，并用系统工具补充可读名称。"""

    def __init__(
        self,
        *,
        sys_root: str | os.PathLike[str] = "/sys",
        proc_root: str | os.PathLike[str] = "/proc",
        command_runner: CommandRunner | None = None,
        use_external_tools: bool | None = None,
    ) -> None:
        self.sys_root = Path(sys_root)
        self.proc_root = Path(proc_root)
        self._host_scan = self.sys_root == Path("/sys") and self.proc_root == Path("/proc")
        self._use_external_tools = (
            self._host_scan if use_external_tools is None else use_external_tools
        )
        self._command_runner = command_runner or run_readonly_command
        self._pci_index: dict[str, PciDeviceInfo] = {}
        self._usb_index: dict[tuple[str, str], list[UsbDeviceInfo]] = defaultdict(list)

    def discover(self) -> DiscoveryResult:
        devices: list[Device] = []
        errors: list[str] = []
        self._load_optional_indexes()

        if not self.proc_root.exists():
            errors.append(f"/proc 根目录不可用：{self.proc_root}")
        if not self.sys_root.exists():
            errors.append(f"/sys 根目录不可用：{self.sys_root}")

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

    def _load_optional_indexes(self) -> None:
        self._pci_index = {}
        self._usb_index = defaultdict(list)
        if not self._use_external_tools:
            return
        try:
            pci_output = self._command_runner(("lspci", "-D", "-mm", "-nn"))
        except Exception:
            pci_output = ""
        for record in parse_lspci_mm(pci_output):
            self._pci_index[record.address.lower()] = record
        try:
            usb_output = self._command_runner(("lsusb",))
        except Exception:
            usb_output = ""
        for record in parse_lsusb(usb_output):
            self._usb_index[(record.vendor_id, record.product_id)].append(record)

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
                    properties={"架构": platform.machine()},
                )
            ]

        blocks = [block for block in cpuinfo.split("\n\n") if block.strip()]
        first_fields = self._key_values(blocks[0] if blocks else cpuinfo)
        model = (
            first_fields.get("model name")
            or first_fields.get("Hardware")
            or first_fields.get("Processor")
            or platform.processor()
            or "Linux 处理器"
        )
        vendor_id = first_fields.get("vendor_id", "")
        logical_count = sum(
            1 for line in cpuinfo.splitlines() if line.strip().startswith("processor")
        )
        physical_cores = first_fields.get("cpu cores", "")
        siblings = first_fields.get("siblings", "")
        frequencies = [
            float(value)
            for value in (
                fields.get("cpu MHz", "")
                for fields in (self._key_values(block) for block in blocks)
            )
            if self._is_number(value)
        ]
        cpufreq = self.sys_root / "devices" / "system" / "cpu" / "cpu0" / "cpufreq"
        current_frequency = self._read_frequency(cpufreq / "scaling_cur_freq")
        minimum_frequency = self._read_frequency(cpufreq / "cpuinfo_min_freq")
        maximum_frequency = self._read_frequency(cpufreq / "cpuinfo_max_freq")
        if not current_frequency and frequencies:
            current_frequency = f"{frequencies[0]:.0f} MHz"

        properties = {
            "逻辑处理器": str(logical_count or os.cpu_count() or "信息不可用"),
            "物理核心": physical_cores or "信息不可用",
            "每核心线程": self._threads_per_core(siblings, physical_cores),
            "架构": platform.machine() or "信息不可用",
            "当前频率": current_frequency or "信息不可用",
            "最低频率": minimum_frequency or "信息不可用",
            "最高频率": maximum_frequency or "信息不可用",
        }
        if vendor_id:
            properties["CPU 厂商 ID"] = vendor_id
        if first_fields.get("model"):
            properties["型号编号"] = first_fields["model"]
        if first_fields.get("stepping"):
            properties["步进"] = first_fields["stepping"]
        return [
            Device(
                device_id="linux:cpu:0",
                name=model,
                category=DeviceCategory.PROCESSORS,
                vendor=self._friendly_cpu_vendor(vendor_id),
                model=model,
                bus="处理器总线",
                driver="内核管理",
                location="CPU 0",
                source_path=str(cpuinfo_path),
                properties=properties,
            )
        ]

    def _collect_display(self) -> list[Device]:
        devices: list[Device] = []
        drm_root = self.sys_root / "class" / "drm"
        cards = {
            path.name: path
            for path in self._directories(drm_root)
            if path.name.startswith("card") and "-" not in path.name
        }
        connectors: dict[str, list[str]] = defaultdict(list)
        for path in self._directories(drm_root):
            if not path.name.startswith("card") or "-" not in path.name:
                continue
            card_name = path.name.split("-", 1)[0]
            connector_name = path.name.split("-", 1)[1]
            status = self._read_text(path / "status") or "未知"
            modes = self._read_text(path / "modes").splitlines()
            mode = modes[0] if modes else ""
            details = f"{connector_name}：{status}"
            if mode:
                details += f"（{mode}）"
            connectors[card_name].append(details)

        seen_addresses: set[str] = set()
        for card_name, path in cards.items():
            device_path = self._resolve_device_path(path / "device")
            record = self._pci_for_path(device_path)
            if record:
                seen_addresses.add(record.address.lower())
            vendor = record.vendor if record else self._read_text(device_path / "vendor") if device_path else ""
            model = record.device if record else self._read_text(device_path / "device") if device_path else ""
            driver = self._link_name(device_path / "driver") if device_path else ""
            properties = self._pci_properties(record)
            properties.update(
                {
                    "DRM 卡": card_name,
                    "连接器": "; ".join(connectors.get(card_name, [])) or "信息不可用",
                }
            )
            vram = self._first_text(
                device_path / "mem_info_vram_total" if device_path else None,
                device_path / "mem_info_vis_vram_total" if device_path else None,
            )
            if vram:
                properties["显存"] = self._bytes_to_size(vram)
            devices.append(
                Device(
                    device_id=f"linux:display:{record.address if record else card_name}",
                    name=record.display_name if record else self._display_name(vendor, model, card_name),
                    category=DeviceCategory.DISPLAY,
                    status=self._status_for_pci(record, driver),
                    vendor=vendor,
                    model=model or card_name,
                    bus="PCI Express" if record else "DRM",
                    driver=driver,
                    location=card_name,
                    source_path=str(path),
                    properties=properties,
                )
            )

        for record in self._pci_index.values():
            if pci_category(record.class_code) is not DeviceCategory.DISPLAY:
                continue
            if record.address.lower() in seen_addresses:
                continue
            devices.append(self._pci_device(record, DeviceCategory.DISPLAY))
        return devices

    def _collect_disks(self) -> list[Device]:
        devices: list[Device] = []
        for path in self._directories(self.sys_root / "block"):
            if path.name.startswith(("loop", "ram", "dm-", "zram")):
                continue
            device_path = self._resolve_device_path(path / "device")
            model = self._read_text(device_path / "model") if device_path else ""
            vendor = self._read_text(device_path / "vendor") if device_path else ""
            driver = self._link_name(path / "device" / "driver")
            size = self._read_text(path / "size")
            rotational = self._read_text(path / "queue" / "rotational")
            removable = self._read_text(path / "removable")
            read_only = self._read_text(path / "ro")
            transport = self._disk_bus(path, device_path)
            properties = {
                "设备节点": f"/dev/{path.name}",
                "容量": self._sectors_to_size(size),
                "传输协议": transport,
                "介质类型": self._media_type(rotational),
                "可移动": self._yes_no(removable),
                "只读": self._yes_no(read_only),
                "逻辑块大小": self._read_text(path / "queue" / "logical_block_size") or "信息不可用",
            }
            for label, filename in (
                ("序列号", "serial"),
                ("固件版本", "rev"),
                ("WWID", "wwid"),
            ):
                value = self._read_text(device_path / filename) if device_path else ""
                if value:
                    properties[label] = value
            devices.append(
                Device(
                    device_id=f"linux:disk:{path.name}",
                    name=model or f"Linux 磁盘 {path.name}",
                    category=DeviceCategory.DISKS,
                    vendor=vendor,
                    model=model or path.name,
                    bus=transport,
                    driver=driver,
                    location=f"/dev/{path.name}",
                    source_path=str(path),
                    properties=properties,
                )
            )
        return devices

    def _collect_network(self) -> list[Device]:
        devices: list[Device] = []
        seen_addresses: set[str] = set()
        for path in self._directories(self.sys_root / "class" / "net"):
            if path.name == "lo":
                continue
            device_path = self._resolve_device_path(path / "device")
            record = self._pci_for_path(device_path)
            if record:
                seen_addresses.add(record.address.lower())
            interface_type = "Wi-Fi" if (path / "wireless").exists() else "以太网/其他"
            driver = self._link_name(device_path / "driver") if device_path else ""
            speed = self._network_speed(self._read_text(path / "speed"))
            properties = self._pci_properties(record)
            properties.update(
                {
                    "接口名称": path.name,
                    "接口类型": interface_type,
                    "接口状态": self._read_text(path / "operstate") or "信息不可用",
                    "链路载波": self._yes_no(self._read_text(path / "carrier")),
                    "MAC 地址": self._read_text(path / "address") or "信息不可用",
                    "速率": speed,
                    "MTU": self._read_text(path / "mtu") or "信息不可用",
                }
            )
            base_name = record.display_name if record else "网络适配器"
            name = f"{base_name} ({path.name})" if record else self._network_name(path.name, "")
            devices.append(
                Device(
                    device_id=f"linux:network:{path.name}",
                    name=name,
                    category=DeviceCategory.NETWORK,
                    status=self._status_for_pci(record, driver),
                    vendor=record.vendor if record else self._read_text(device_path / "vendor") if device_path else "",
                    model=record.device if record else self._read_text(device_path / "device") if device_path else path.name,
                    bus="PCI Express" if record else "网络接口",
                    driver=driver,
                    location=path.name,
                    source_path=str(path),
                    properties=properties,
                )
            )
        for record in self._pci_index.values():
            if pci_category(record.class_code) is DeviceCategory.NETWORK:
                if record.address.lower() not in seen_addresses:
                    devices.append(self._pci_device(record, DeviceCategory.NETWORK))
        return devices

    def _collect_usb(self) -> list[Device]:
        devices: list[Device] = []
        for record in self._pci_index.values():
            if pci_category(record.class_code) is DeviceCategory.USB:
                devices.append(self._pci_device(record, DeviceCategory.USB))

        usb_root = self.sys_root / "bus" / "usb" / "devices"
        for path in self._directories(usb_root):
            if ":" in path.name or not (path / "idVendor").exists():
                continue
            vendor_id = self._read_text(path / "idVendor").lower()
            product_id = self._read_text(path / "idProduct").lower()
            lsusb_record = self._take_usb_record(vendor_id, product_id)
            vendor = self._read_text(path / "manufacturer")
            product = self._read_text(path / "product")
            if lsusb_record:
                vendor = vendor or lsusb_record.name.split(" ", 1)[0]
                product = product or lsusb_record.name
            driver = self._link_name(path / "driver")
            if not driver:
                driver = self._link_name(path / "1-0:1.0" / "driver")
            properties = {
                "硬件 ID": f"USB\\VID_{vendor_id.upper()}&PID_{product_id.upper()}",
                "厂商 ID": vendor_id or "信息不可用",
                "产品 ID": product_id or "信息不可用",
                "制造商": vendor or "信息不可用",
                "产品": product or "信息不可用",
                "USB 版本": self._read_text(path / "version") or "信息不可用",
                "速度": self._read_text(path / "speed") or "信息不可用",
                "总线号": self._read_text(path / "busnum") or "信息不可用",
                "设备号": self._read_text(path / "devnum") or "信息不可用",
                "最大功率": self._read_text(path / "bMaxPower") or "信息不可用",
            }
            serial = self._read_text(path / "serial")
            if serial:
                properties["序列号"] = serial
            name = product or (lsusb_record.name if lsusb_record else "") or f"USB 设备 {vendor_id}:{product_id}"
            location = lsusb_record.address if lsusb_record else path.name
            devices.append(
                Device(
                    device_id=f"linux:usb:{path.name}",
                    name=name,
                    category=DeviceCategory.USB,
                    vendor=vendor or vendor_id,
                    model=product or product_id,
                    bus="USB",
                    driver=driver,
                    location=location,
                    source_path=str(path),
                    properties=properties,
                )
            )
        return devices

    def _collect_audio(self) -> list[Device]:
        devices: list[Device] = []
        seen_addresses: set[str] = set()
        alsa_cards = self._alsa_cards()
        sound_root = self.sys_root / "class" / "sound"
        for path in self._directories(sound_root):
            if not path.name.startswith("card"):
                continue
            device_path = self._resolve_device_path(path / "device")
            record = self._pci_for_path(device_path)
            if record:
                seen_addresses.add(record.address.lower())
            card_number = path.name.removeprefix("card")
            alsa_description = alsa_cards.get(card_number, "")
            driver = self._link_name(device_path / "driver") if device_path else ""
            name = record.display_name if record else (alsa_description or self._read_text(path / "id") or path.name)
            properties = self._pci_properties(record)
            properties.update(
                {
                    "ALSA 卡": path.name,
                    "ALSA 描述": alsa_description or "信息不可用",
                    "设备名称": self._read_text(path / "id") or "信息不可用",
                    "Codec": self._alsa_codec(card_number) or "信息不可用",
                }
            )
            devices.append(
                Device(
                    device_id=f"linux:audio:{path.name}",
                    name=name,
                    category=DeviceCategory.AUDIO,
                    status=self._status_for_pci(record, driver),
                    vendor=record.vendor if record else "",
                    model=record.device if record else alsa_description,
                    bus="PCI Express" if record else "ALSA",
                    driver=driver or "ALSA",
                    location=path.name,
                    source_path=str(path),
                    properties=properties,
                )
            )
        for record in self._pci_index.values():
            if pci_category(record.class_code) is DeviceCategory.AUDIO:
                if record.address.lower() not in seen_addresses:
                    devices.append(self._pci_device(record, DeviceCategory.AUDIO))
        return devices

    def _collect_input(self) -> list[Device]:
        devices: list[Device] = []
        input_root = self.sys_root / "class" / "input"
        for path in self._directories(input_root):
            if not path.name.startswith("event"):
                continue
            device_path = self._resolve_device_path(path / "device")
            name = self._read_text(device_path / "name") if device_path else ""
            name = name or f"Linux 输入设备 {path.name}"
            capabilities = self._input_capabilities(device_path)
            bus_id = self._read_text(device_path / "id" / "bustype") if device_path else ""
            vendor_id = self._read_text(device_path / "id" / "vendor") if device_path else ""
            product_id = self._read_text(device_path / "id" / "product") if device_path else ""
            driver = self._link_name(device_path / "driver") if device_path else ""
            properties = {
                "输入节点": f"/dev/input/{path.name}",
                "设备类型": self._input_type(capabilities, name),
                "能力": ", ".join(capabilities) or "信息不可用",
                "总线 ID": bus_id or "信息不可用",
                "厂商 ID": vendor_id or "信息不可用",
                "产品 ID": product_id or "信息不可用",
            }
            phys = self._read_text(device_path / "phys") if device_path else ""
            if phys:
                properties["物理路径"] = phys
            devices.append(
                Device(
                    device_id=f"linux:input:{path.name}",
                    name=name,
                    category=DeviceCategory.INPUT,
                    bus="输入设备",
                    driver=driver,
                    location=f"/dev/input/{path.name}",
                    source_path=str(path),
                    properties=properties,
                )
            )
        return devices

    def _collect_system(self) -> list[Device]:
        devices: list[Device] = []
        if self._host_scan:
            devices.append(self._system_summary())
        for record in self._pci_index.values():
            category = pci_category(record.class_code)
            if category in {
                DeviceCategory.DISPLAY,
                DeviceCategory.NETWORK,
                DeviceCategory.USB,
                DeviceCategory.AUDIO,
            }:
                continue
            devices.append(self._pci_device(record, DeviceCategory.SYSTEM))
        if not self._pci_index:
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
        return devices[:96]

    def _system_summary(self) -> Device:
        os_release_path = Path("/etc/os-release")
        os_release = self._key_values(self._read_text(os_release_path), separator="=")
        pretty_name = os_release.get("PRETTY_NAME", "Linux")
        memory = self._memory_total()
        uptime = self._format_uptime(self._read_text(self.proc_root / "uptime"))
        properties = {
            "发行版": pretty_name.strip('"'),
            "内核": platform.release() or "信息不可用",
            "主机名": socket.gethostname() or "信息不可用",
            "架构": platform.machine() or "信息不可用",
            "内存": memory,
            "运行时间": uptime,
            "会话": os.environ.get("XDG_CURRENT_DESKTOP", "信息不可用"),
        }
        return Device(
            device_id="linux:system:summary",
            name="Linux 系统信息",
            category=DeviceCategory.SYSTEM,
            vendor=pretty_name.strip('"'),
            model=platform.machine(),
            bus="系统",
            driver=platform.release(),
            location=socket.gethostname(),
            source_path=str(os_release_path),
            properties=properties,
        )

    def _pci_device(self, record: PciDeviceInfo, category: DeviceCategory) -> Device:
        driver = self._pci_driver(record.address)
        properties = self._pci_properties(record)
        return Device(
            device_id=f"linux:pci:{record.address}",
            name=record.display_name,
            category=category,
            status=self._status_for_pci(record, driver),
            vendor=record.vendor,
            model=record.device,
            bus="PCI Express",
            driver=driver,
            location=record.address,
            source_path=str(self.sys_root / "bus" / "pci" / "devices" / record.address),
            properties=properties,
        )

    def _pci_properties(self, record: PciDeviceInfo | None) -> dict[str, str]:
        if record is None:
            return {}
        properties = {
            "PCI 地址": record.address,
            "硬件 ID": record.hardware_id or "信息不可用",
            "类别代码": record.class_code or "信息不可用",
            "类别": record.class_name or "信息不可用",
        }
        if record.subsystem:
            properties["子系统"] = record.subsystem
        if record.revision:
            properties["修订版本"] = record.revision
        if record.programming_interface:
            properties["编程接口"] = record.programming_interface
        return properties

    def _pci_for_path(self, path: Path | None) -> PciDeviceInfo | None:
        address = self._pci_address(path)
        return self._pci_index.get(address.lower()) if address else None

    def _pci_driver(self, address: str) -> str:
        path = self.sys_root / "bus" / "pci" / "devices" / address / "driver"
        return self._link_name(path)

    @staticmethod
    def _pci_address(path: Path | None) -> str:
        if path is None:
            return ""
        for part in reversed(path.parts):
            if _PCI_ADDRESS_RE.fullmatch(part):
                return part
        return ""

    @staticmethod
    def _status_for_pci(record: PciDeviceInfo | None, driver: str) -> DeviceStatus:
        if record is not None and not driver and record.class_code not in {"0600", "0601", "0604"}:
            return DeviceStatus.UNKNOWN
        return DeviceStatus.OK

    def _alsa_cards(self) -> dict[str, str]:
        cards: dict[str, str] = {}
        for line in self._read_text(self.proc_root / "asound" / "cards").splitlines():
            match = re.match(r"\s*(\d+)\s+\[([^]]+)\]:\s*(.*)", line)
            if match:
                cards[match.group(1)] = match.group(3).strip()
        return cards

    def _alsa_codec(self, card_number: str) -> str:
        card_root = self.proc_root / "asound" / f"card{card_number}"
        for path in sorted(card_root.glob("codec#*")) if card_root.exists() else ():
            for line in self._read_text(path).splitlines():
                if line.startswith("Codec:"):
                    return line.partition(":")[2].strip()
        return ""

    @staticmethod
    def _input_capabilities(path: Path | None) -> list[str]:
        if path is None:
            return []
        capabilities = []
        for filename, label in (("capabilities/key", "键盘"), ("capabilities/rel", "相对指针"), ("capabilities/abs", "绝对指针"), ("capabilities/sw", "开关")):
            try:
                if path.joinpath(filename).read_text(encoding="utf-8", errors="replace").strip("0\n"):
                    capabilities.append(label)
            except OSError:
                continue
        return capabilities

    @staticmethod
    def _input_type(capabilities: list[str], name: str) -> str:
        lowered = name.casefold()
        if "键盘" in capabilities or "keyboard" in lowered:
            return "键盘"
        if "相对指针" in capabilities or "mouse" in lowered:
            return "鼠标/指针"
        if "绝对指针" in capabilities or "touch" in lowered:
            return "触摸/绝对指针"
        return "其他输入设备"

    @staticmethod
    def _key_values(text: str, *, separator: str = ":") -> dict[str, str]:
        values: dict[str, str] = {}
        for line in text.splitlines():
            key, found, value = line.partition(separator)
            if found:
                values.setdefault(key.strip(), value.strip())
        return values

    @staticmethod
    def _threads_per_core(siblings: str, cores: str) -> str:
        try:
            if int(siblings) > 0 and int(cores) > 0:
                return str(max(1, int(siblings) // int(cores)))
        except ValueError:
            pass
        return "信息不可用"

    @staticmethod
    def _is_number(value: str) -> bool:
        try:
            float(value)
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def _friendly_cpu_vendor(value: str) -> str:
        return {
            "GenuineIntel": "Intel",
            "AuthenticAMD": "AMD",
            "ARM Limited": "ARM",
        }.get(value, value)

    @staticmethod
    def _read_frequency(path: Path) -> str:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").strip()
            value = int(raw)
        except (OSError, TypeError, ValueError):
            return ""
        if value <= 0:
            return ""
        return f"{value / 1_000_000:.2f} GHz"

    @staticmethod
    def _memory_total() -> str:
        try:
            for line in Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("MemTotal:"):
                    kib = int(line.split()[1])
                    return f"{kib / 1024 / 1024:.2f} GiB"
        except (OSError, ValueError, IndexError):
            pass
        return "信息不可用"

    @staticmethod
    def _format_uptime(value: str) -> str:
        try:
            seconds = int(float(value))
        except (TypeError, ValueError):
            return "信息不可用"
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes = seconds // 60
        if days:
            return f"{days} 天 {hours} 小时"
        return f"{hours} 小时 {minutes} 分钟"

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

    @staticmethod
    def _first_text(*paths: Path | None) -> str:
        for path in paths:
            if path is not None:
                value = LinuxDeviceProvider._read_text(path)
                if value:
                    return value
        return ""

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
            return f"{vendor} {model}"
        return model or vendor or f"显示适配器 {fallback}"

    @staticmethod
    def _network_name(interface: str, model: str) -> str:
        return f"{interface} 网络适配器" if not model else f"{interface} 网络适配器 ({model})"

    @staticmethod
    def _network_speed(value: str) -> str:
        try:
            speed = int(value)
        except (TypeError, ValueError):
            return "信息不可用"
        return "信息不可用" if speed <= 0 else f"{speed} Mb/s"

    @staticmethod
    def _sectors_to_size(sectors: str) -> str:
        try:
            value = int(sectors) * 512
        except (TypeError, ValueError):
            return "信息不可用"
        return LinuxDeviceProvider._bytes_to_size(str(value))

    @staticmethod
    def _bytes_to_size(value: str) -> str:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return "信息不可用"
        units = ("B", "KiB", "MiB", "GiB", "TiB")
        index = 0
        while amount >= 1024 and index < len(units) - 1:
            amount /= 1024
            index += 1
        return f"{amount:.2f} {units[index]}"

    def _disk_bus(self, path: Path, device_path: Path | None) -> str:
        text = f"{path} {device_path or ''}".casefold()
        subsystem = self._link_name(device_path / "subsystem") if device_path else ""
        text = f"{text} {subsystem}".casefold()
        if "nvme" in text:
            return "NVMe"
        if "mmc" in text:
            return "MMC"
        if "usb" in text:
            return "USB"
        if "ata" in text or "sata" in text:
            return "SATA"
        return "块设备"

    @staticmethod
    def _media_type(value: str) -> str:
        if value == "0":
            return "固态/非旋转介质"
        if value == "1":
            return "机械硬盘/旋转介质"
        return "信息不可用"

    @staticmethod
    def _yes_no(value: str) -> str:
        if value == "1":
            return "是"
        if value == "0":
            return "否"
        if value == "up":
            return "已连接"
        if value == "down":
            return "未连接"
        return "信息不可用"

    def _take_usb_record(self, vendor_id: str, product_id: str) -> UsbDeviceInfo | None:
        records = self._usb_index.get((vendor_id, product_id), [])
        return records[0] if records else None
