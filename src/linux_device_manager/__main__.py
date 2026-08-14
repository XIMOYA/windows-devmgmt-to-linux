# src/linux_device_manager/__main__.py
# 支持使用 python -m linux_device_manager 启动设备管理器。

from linux_device_manager.app import main


if __name__ == "__main__":
    raise SystemExit(main())
