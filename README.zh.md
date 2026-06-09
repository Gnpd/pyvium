# PYVIUM

[English](./README.md) · [中文](./README.zh.md)

IviumSoft 驱动 DLL 的 Python 封装，支持直接通过 Python 控制 Ivium 恒电位仪并处理实验数据。

PYVIUM 提供：

- 对原始 IviumSoft Core 函数的直接访问
- 更高层次的 Pythonic 接口，包含异常处理和扩展工具

---

## 功能特性

- 完整访问 IviumSoft 驱动 DLL 函数
- Python 友好接口
- 异常管理
- 数据处理工具
- 批量转换工具
- 批处理模式同步

---

## 环境要求

PYVIUM 需要在 Windows 机器上安装 IviumSoft，因为它依赖官方驱动 DLL。

IviumSoft 下载地址：

https://www.ivium.com/support/#Software%20update

当前版本的 PYVIUM 包含 IviumSoft **4.1239** 版本的 DLL。

---

## 安装

使用 pip 安装：

```
pip install pyvium
```

或使用 poetry：

```
poetry add pyvium
```

## 快速开始

### 使用 Core 函数（直接访问 DLL）

如需使用与「IviumSoft 驱动 DLL」相同的函数，可按如下方式导入 Core 类。所有函数返回结果码（整数），以及可用时的返回值。详情请参阅 IviumSoft 文档。

```
from pyvium import Core

Core.IV_open()
Core.IV_getdevicestatus()
Core.IV_close()
```

## 使用 Pyvium 高级接口（推荐）

这是对 Core 函数的封装，额外提供：

- 异常管理（示例见[此处](https://github.com/Gnpd/pyvium/blob/main/docs/error_management.md)）
- 更简洁的语法
- 扩展功能

```
from pyvium import Pyvium

Pyvium.open_driver()
Pyvium.get_device_status()
Pyvium.close_driver()
```

## 数据处理工具

提供额外的数据处理功能：

```
from pyvium import Tools

Tools.convert_idf_dir_to_csv()
```

## 示例与笔记本

一系列 Jupyter 笔记本覆盖完整 API：

| 笔记本 | 主题 |
|---|---|
| `01_getting_started` | 安装、驱动生命周期、错误处理 |
| `02_device_and_instance_management` | 连接设备、切换实例 |
| `03_direct_mode_basics` | 电位/电流控制、电池开关 |
| `04_direct_mode_signals` | DAC/ADC、数字 I/O、交流信号 |
| `05_bipotentiostat_and_we32` | BiStat WE2 与 32 通道 WE32 阵列 |
| `06_method_mode` | 加载、运行、监控和保存实验 |
| `07_data_processing` | 解析 IDF 文件、导出为 CSV（无需硬件） |
| `08_batch_and_synchronization` | 多设备设定点与并行运行 |
| `09_trigger_reference` | Python–IviumSoft 触发机制 |

中文笔记本位于 [`notebooks/zh/`](https://github.com/Gnpd/pyvium/tree/main/notebooks/zh) 目录。

## 已实现函数

已实现函数列表见[此处](https://github.com/Gnpd/pyvium/blob/main/docs/method_list.md)。

## 支持与咨询

如需将 PYVIUM 集成到您的应用、接入 Ivium 仪器或开发自定义工作流，欢迎联系专业咨询服务。

联系方式：

📧 a.gutierrez@g-npd.com

您也可以通过 GitHub Sponsors 支持本项目：

https://github.com/sponsors/Gnpd

赞助者享有优先支持，并推动项目持续发展。

## 链接

- [GitHub 主页](https://github.com/Gnpd/pyvium)
- [PyPI 页面](https://pypi.org/project/pyvium)
