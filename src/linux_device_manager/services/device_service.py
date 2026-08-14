# src/linux_device_manager/services/device_service.py
# 管理设备扫描线程，把 Provider 的结果安全地交给 Qt 界面。

from __future__ import annotations

from linux_device_manager.qt_compat import QObject, QRunnable, QThreadPool, Signal, Slot

from linux_device_manager.models import Device, sort_devices
from linux_device_manager.providers.base import DeviceProvider, DiscoveryResult


class _RefreshSignals(QObject):
    finished = Signal(object)


class _RefreshTask(QRunnable):
    def __init__(self, provider: DeviceProvider) -> None:
        super().__init__()
        self.provider = provider
        self.signals = _RefreshSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.provider.discover()
        except Exception as exc:  # 最后一道边界，避免后台线程异常终止应用
            result = DiscoveryResult(errors=[f"设备扫描失败：{type(exc).__name__}: {exc}"])
        self.signals.finished.emit(result)


class DeviceRefreshService(QObject):
    """在 Qt 线程池中执行设备扫描。"""

    started = Signal()
    completed = Signal(object)

    def __init__(self, provider: DeviceProvider, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.provider = provider
        self.thread_pool = QThreadPool.globalInstance()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def refresh(self) -> bool:
        if self._running:
            return False
        self._running = True
        self.started.emit()
        task = _RefreshTask(self.provider)
        task.signals.finished.connect(self._on_finished)
        self.thread_pool.start(task)
        return True

    @Slot(object)
    def _on_finished(self, result: DiscoveryResult) -> None:
        self._running = False
        result.devices = sort_devices(result.devices)
        self.completed.emit(result)
