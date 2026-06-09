# PYVIUM

[English](./README.md) · [中文](./README.zh.md)

Python wrapper for the IviumSoft driver DLL, enabling control of Ivium potentiostats and data processing directly from Python.

PYVIUM provides both:

- Direct access to the original IviumSoft Core functions
- Higher-level Pythonic interface with exception handling and extended utilities

---

## Features

- Full access to IviumSoft driver DLL functions
- Python-friendly interface
- Exception management
- Data processing tools
- Batch conversion utilities
- Batch mode synchronization

---

## Requirements

PYVIUM requires IviumSoft to be installed on a Windows machine, as it uses the official driver DLL.

Download IviumSoft here:

https://www.ivium.com/support/#Software%20update

This version of PYVIUM contains the DLL from IviumSoft release **4.1239**.

---

## Installation

Install PYVIUM easily with pip:

```
pip install pyvium
```

Or with poetry:

```
poetry add pyvium
```

## Quick Start
### Using Core functions (direct DLL access)

To use the same functions available in the "IviumSoft driver DLL" you can import the Core class as follows. All functions return a result code (integer) and a result value if available. For further information you can check the IviumSoft documentation.

```
from pyvium import Core

Core.IV_open()
Core.IV_getdevicestatus()
Core.IV_close()
```

## Using Pyvium high-level interface (recommended)

This is a wrapper around the Core functions that adds a few things:

- Exception management (you can find an example [here](https://github.com/Gnpd/pyvium/blob/main/docs/error_management.md))
- Cleaner syntax
- Additional functionality

```
from pyvium import Pyvium

Pyvium.open_driver()
Pyvium.get_device_status()
Pyvium.close_driver()

```
## Data processing tools

This offers further functionality in data processing:


```
from pyvium import Tools

Tools.convert_idf_dir_to_csv()

```

## Examples & Notebooks

A series of Jupyter notebooks covers the full API:

| Notebook | Topic |
|---|---|
| `01_getting_started` | Installation, driver lifecycle, error handling |
| `02_device_and_instance_management` | Connecting devices, switching instances |
| `03_direct_mode_basics` | Potential/current control, cell on/off |
| `04_direct_mode_signals` | DAC/ADC, digital I/O, AC signal |
| `05_bipotentiostat_and_we32` | BiStat WE2 and 32-channel WE32 array |
| `06_method_mode` | Load, run, monitor, and save experiments |
| `07_data_processing` | Parse IDF files, export to CSV (no hardware needed) |
| `08_batch_and_synchronization` | Multi-device setpoints and parallel runs |
| `09_trigger_reference` | Python–IviumSoft trigger mechanisms |

Browse them in the [`notebooks/`](https://github.com/Gnpd/pyvium/tree/main/notebooks) directory.

## Implemented functions

The list of currently implemented functions can be found [here](https://github.com/Gnpd/pyvium/blob/main/docs/method_list.md).

## Support and Consulting

If you need help implementing PYVIUM in your application, integrating Ivium instruments, or developing custom workflows, professional consulting is available.

Contact:

📧 a.gutierrez@g-npd.com

You can also support the project via GitHub Sponsors:

https://github.com/sponsors/Gnpd

Sponsors receive priority support and help drive future development.

## Links

- [See on GitHub](https://github.com/Gnpd/pyvium)
- [See on PyPI](https://pypi.org/project/pyvium)
