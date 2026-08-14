# windows-devmgmt-to-linux

一个 Windows 风格的 Linux 设备管理器。

> 我修复了 Linux 上没有设备管理器的 Bug。

项目当前是一个只读展示工具：它读取 Linux 的 `/sys` 和 `/proc`，把处理器、显卡、磁盘、网卡、USB、音频和输入设备整理成类似 Windows 设备管理器的树形界面。

## 项目状态

当前版本：`0.1.0`

已完成：

- Windows 风格的设备分类树
- 处理器、显示适配器、磁盘驱动器、网络适配器、USB、音频、输入设备和系统总线采集
- 设备详情和属性窗口
- F5 刷新设备列表
- 复制设备详情
- 黄色警告状态和“未知 PCI 设备”演示数据
- “更新驱动”安全模拟对话框
- Mock 演示模式
- Linux Provider、Mock Provider 和后台刷新服务测试

## 截图

<!-- 截图占位：后续上传 screenshot/device-manager.png 后，在这里补充实际截图。 -->

设备管理器主界面截图待补充。

## 环境要求

- Python `>= 3.11`
- PySide6 `>= 6.7`
- Linux 环境用于读取真实硬件信息

项目可以在 Windows 上使用 `--mock` 模式进行界面开发和演示。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

如果只想运行 Mock 界面，也需要安装 PySide6，因为图形界面基于 Qt 构建。

## 运行

### 读取真实 Linux 硬件

安装项目后运行：

```bash
device-manager
```

也可以不安装为命令，直接从源码运行：

```bash
PYTHONPATH=src python -m linux_device_manager
```

程序默认只读取设备信息，不需要 root 权限。

### Mock 演示模式

Mock 模式不读取真实硬件，适合在 Windows 上开发界面、录制视频或调试布局：

```bash
device-manager --mock
```

从源码运行：

```bash
PYTHONPATH=src python -m linux_device_manager --mock
```

Mock 模式包含固定的演示设备，其中包括一个带黄色警告图标的“未知 PCI 设备”。

## 功能说明

### 设备分类

左侧设备树目前包含：

- 处理器
- 显示适配器
- 磁盘驱动器
- 网络适配器
- 通用串行总线控制器
- 音频输入和输出
- 键盘、鼠标和其他指针设备
- 系统设备
- 其他设备

### 设备详情

选中设备后，右侧面板会展示：

- 设备类别
- 厂商和型号
- 总线
- 内核驱动
- 设备位置
- `/sys` 或 `/proc` 来源路径
- 设备采集到的其他属性

双击设备或点击“属性”可以打开属性窗口。

### 更新驱动

当前版本的“更新驱动”是安全模拟功能：

- 不会安装驱动；
- 不会卸载驱动；
- 不会禁用设备；
- 不会写入 `/sys`；
- 不会修改系统配置。

它只展示 Windows 风格的驱动检查结果，并说明 Linux 驱动由内核或发行版软件包管理器负责。

## 数据来源

真实 Linux 模式主要读取以下系统信息：

- `/proc/cpuinfo`
- `/sys/class/drm`
- `/sys/block`
- `/sys/class/net`
- `/sys/bus/usb/devices`
- `/sys/class/sound`
- `/sys/class/input`
- `/sys/bus`

程序会尽量读取可用字段。单个设备或单类设备读取失败时，会保留其他结果，并在状态栏提示错误数量。

## 测试

项目测试使用 Python 内置 `unittest`：

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

测试覆盖：

- 设备模型状态和详情文本；
- 设备分类排序；
- Mock Provider；
- Linux Provider 的临时 `/sys`、`/proc` fixture；
- 缺失路径和异常 Provider；
- 后台刷新并发保护和结果排序。

如果安装了测试依赖，也可以使用：

```bash
python -m pytest -q
```

## 项目结构

```text
.
├── pyproject.toml
├── README.md
├── src/
│   └── linux_device_manager/
│       ├── app.py
│       ├── models.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── linux.py
│       │   └── mock.py
│       ├── services/
│       │   └── device_service.py
│       └── ui/
│           ├── device_tree.py
│           ├── details_panel.py
│           ├── main_window.py
│           └── styles.py
└── tests/
    ├── test_models.py
    ├── test_providers.py
    └── test_service.py
```

## 后续计划

- 补充真实 Linux 硬件截图；
- 改进 PCI 厂商和设备型号的可读名称；
- 增加更多 USB、PCI 和音频设备属性；
- 将键盘、鼠标等输入设备拆分成更细的 Windows 风格分类；
- 增加安全的演示操作，例如在 Mock 模式中模拟禁用设备和驱动更新；
- 增加 Linux 打包方式，方便直接安装和启动；
- 在更多发行版和桌面环境中进行实机测试。

## 安全边界

这是一个只读硬件查看工具。请不要把它当作真正的驱动管理器使用，也不要直接根据界面信息执行未经确认的系统级操作。

真实设备采集不需要 root 权限。项目不会主动执行驱动安装、设备卸载、设备禁用、服务修改或系统重启。
