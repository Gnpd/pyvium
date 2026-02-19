# PYVIUM

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

---

## Requirements

PYVIUM requires IviumSoft to be installed on a Windows machine, as it uses the official driver DLL.

Download IviumSoft here:

https://www.ivium.com/support/#Software%20update

This version of PYVIUM contains the DLL from IviumSoft release **4.1221**.

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

- Exception management (you can find an example [here](https://github.com/SF-Tec/pyvium/blob/main/docs/error_management.md))
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

## Implemented functions

The list of currently implemented functions can be found [here](https://github.com/SF-Tec/pyvium/blob/main/docs/method_list.md).

## Support and Consulting

If you need help implementing PYVIUM in your application, integrating Ivium instruments, or developing custom workflows, professional consulting is available.

Contact:

📧 a.gutierrez@g-npd.com

You can also support the project via GitHub Sponsors:

https://github.com/sponsors/Gnpd

Sponsors receive priority support and help drive future development.

## Links

- [See on GitHub](https://github.com/sf-tec/pyvium)
- [See on PyPI](https://pypi.org/project/pyvium)
