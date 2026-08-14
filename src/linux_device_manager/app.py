# src/linux_device_manager/app.py
# 创建 QApplication，解析启动参数并选择真实或演示设备数据源。

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from linux_device_manager.providers.linux import LinuxDeviceProvider
from linux_device_manager.providers.mock import MockDeviceProvider
from linux_device_manager.ui.main_window import MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="device-manager",
        description="一个 Windows 风格的 Linux 设备管理器（只读展示）。",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用稳定的演示设备数据，不读取真实硬件。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    application = QApplication.instance() or QApplication(sys.argv)
    provider = MockDeviceProvider() if args.mock else LinuxDeviceProvider()
    window = MainWindow(provider, mock_mode=args.mock)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
