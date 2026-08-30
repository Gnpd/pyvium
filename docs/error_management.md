```
from pyvium import Pyvium
from pyvium.errors import DeviceNotConnectedToIviumSoftError, IviumSoftNotRunningError

try:
    Pyvium.open_driver()
    Pyvium.get_potential()
except IviumSoftNotRunningError:
    print('Tell the user the software is not running')
except DeviceNotConnectedToIviumSoftError:
    raise

```

| Available errors                   | Raised when                                            |
| ---------------------------------- | ------------------------------------------------------ |
| DeviceBusyError                    | The selected device is measuring                       |
| DeviceNotConnectedToIviumSoftError | No device is connected in IviumSoft                    |
| DriverNotOpenError                 | `open_driver()` has not been called                    |
| NoDeviceDetectedError              | No device is detected (DLL result code `-1`)           |
| IviumSoftNotRunningError           | No IviumSoft instance is running                       |
| CellOffError                       | The cell is off                                        |
| IllegalCommandError                | The command is invalid for this device (code `1`)      |
| InvalidStateError                  | The device state forbids the command (code `3`)        |
| UnexpectedResultCodeError          | The DLL returned a code PYVIUM does not model          |

A DLL setter returning `0` means success. `-1`, `1`, `2` and `3` map to the typed errors
above (`2` raises the builtin `ValueError`, for an argument out of range). Any other
non-zero value raises `UnexpectedResultCodeError`, which carries the offending value on
its `result_code` attribute:

```python
from pyvium.errors import UnexpectedResultCodeError

try:
    Pyvium.set_potential(0.5)
except UnexpectedResultCodeError as error:
    print(error.result_code)
```
