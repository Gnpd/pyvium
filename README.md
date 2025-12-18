# PYVIUM

Tiny Python wrapper around the "Software development driver DLL" for IviumSoft.

# Important:

This module uses a dll from the IviumSoft application. You need to have this software installed on a Windows machine. The IviumSoft application can be downloaded from here: https://www.ivium.com/support/#Software%20update

This version of Pyvium contains the DLL from IviumSoft release 4.1221.

## Installation

Install PYVIUM easily with pip:

```
pip install pyvium
```

Or with poetry:

```
poetry add pyvium
```

## Usage Example (Using IviumSoft Core functions)

To use the same functions available in the "IviumSoft driver DLL" you can import the Core class as follows. All functions return a result code (integer) and a result value if available. For further information you can check the IviumSoft documentation.

```
from pyvium import Core

Core.IV_open()
Core.IV_getdevicestatus()
Core.IV_close()
```

## Usage Example (Using Pyvium methods)

This is a wrapper around the Core functions that adds a few things:

- Exception management (you can find an example [here](https://github.com/SF-Tec/pyvium/blob/main/docs/error_management.md))
- New functionalities

```
from pyvium import Pyvium

Pyvium.open_driver()
Pyvium.get_device_status()
Pyvium.close_driver()

```
## Usage Example (Using Tools methods)

This offers further functionality in data processing:


```
from pyvium import Tools

Tools.convert_idf_dir_to_csv()

```

## Supported functions

The list of currently supported and implemented functions can be found [here](https://github.com/SF-Tec/pyvium/blob/main/docs/method_list.md).

## Links

- [See on GitHub](https://github.com/sf-tec/pyvium)
- [See on PyPI](https://pypi.org/project/pyvium)
