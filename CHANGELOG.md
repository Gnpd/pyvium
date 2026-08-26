# Changelog

All notable changes to PYVIUM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

## [Unreleased]

### Fixed

- **A driver close/reopen no longer leaves a stale instance or channel selection.**
  `Core` shadows the driver's selected instance and channel, because the DLL keeps both
  as global state with no getter, and every scoping helper (`on_instance`, `on_channel`,
  `get_active_iviumsoft_instances`, `get_channel_statuses`, `set_device_current` /
  `set_device_potential`) reads the shadow to know what to restore afterwards. The
  shadows were never reset when the driver was closed and reopened, although the driver
  itself starts again on instance 1. After `select_iviumsoft_instance(3)` followed by
  `close_driver()` and `open_driver()`, the driver was on instance 1 while the shadow
  still said 3, so the first `with Pyvium.on_instance(n):` block restored to 3 on exit
  and silently moved the working instance: every later unscoped call went to the wrong
  IviumSoft instance and still reported success. `IV_open` and `IV_close` now reset both
  shadows to 1, matching the state the driver starts from. The stale channel case had a
  second edge, since `IV_SelectChannel` treats its argument as a tab count: restoring a
  stale channel 3 against a freshly restarted IviumSoft opened three tabs rather than
  switching to one.

## [0.3.0rc4] - 2026-08-21

Fourth release candidate for 0.3.0. Refreshes the bundled IviumSoft driver DLL to
release 4.1247, whose main change is that connecting through the DLL no longer kills
a measurement that is already running on the device. Also fixes an instance-selection
leak in the two `set_device_*` setpoint methods. Install it explicitly (pip ignores
pre-releases by default):

```
pip install pyvium==0.3.0rc4
```

### Changed

- **Bundled DLL updated to IviumSoft release 4.1247.** Both binaries were replaced
  (`IVIUM_remdriver.dll` for 32-bit Python, `Ivium_remdriver64.dll` for 64-bit);
  `IV_VersionDllFileStr()` now reports `4.1247.10407`. The driver API version is
  unchanged (`IV_VersionDll()` still returns 203), and the header coverage test
  confirms every function declared in the bundled header is still bound on `Core`,
  so no `Core` or `Pyvium` signature changed.

### Fixed

- **Connecting via the DLL now adopts a measurement already running on the device**
  (driver-side fix in 4.1247; no PYVIUM code change). When a device is left running a
  method on its own (IviumSoft closed with *Close and continue*, so the run keeps going
  on the device / DataSecure) and a fresh IviumSoft instance is started, `IV_connect()`
  (and therefore `Pyvium.connect_device()`) used to flush the buffered points and then
  terminate the run at about the moment the call returned, leaving the device idle
  shortly after. Only the IviumSoft **Connect** button adopted the ongoing measurement.
  The DLL path now matches the button: the run is adopted, data resumes, and the method
  continues to its end.
- **`set_device_current` / `set_device_potential` no longer leave the selected instance
  parked on their target.** Both call a fused `IV_selectdevice_*` function, which selects
  the instance and runs the command in one go but never restores the previous selection,
  and neither took the driver lock. A setpoint therefore moved the global selection as a
  side effect: subsequent unscoped calls silently acted on the wrong instance, and a
  setpoint issued from another thread could redirect a running `Pyvium.on_instance(n)`
  block, breaking the atomicity that context manager documents. Both methods now hold the
  lock and restore the previous selection, so they behave as documented and apply a
  setpoint without changing the caller's selected instance.
- **`connect_device_to_channel` now verifies which device it actually connected.**
  It selected the serial and issued the connect, but never checked the result.
  `IV_connect` is asynchronous and connects the first available device (which
  `IV_SelectSn` steers by putting the requested serial at the top of the list), so a
  connect issued before a previous one had settled could land on a different
  instrument and still be reported as success, silently attributing a measurement to
  the wrong device. The driver lock is now held until the connection has come up and
  the serial has been read back. A connection that lands on a different device is
  disconnected again and raises `DeviceNotConnectedToIviumSoftError`, as does a
  connect that never comes up within the settle timeout.

### Added

- **`connect_device_to_channel` takes an optional `alias`**, the IviumSoft dropdown
  token `IV_SelectSn` selects by. It equals the serial on single-channel devices, but
  on a multichannel frame each channel has its own token (e.g. `Oc-0-3`) distinct from
  that channel's serial, so the serial alone selects nothing. `alias` selects and
  `serial_number` is what the connection is verified against. Resolving one to the
  other stays with the caller: the mapping comes from the hardware configuration and
  is not discoverable through the DLL. Omitting it keeps the previous behaviour.
- **`MeasurementPartSummary` is now exported from the package root.** It is the return
  type of `MeasurementReader.part_summaries()` and was already exported from
  `pyvium.tools`, but `from pyvium import MeasurementPartSummary` raised `ImportError`
  while every sibling dataclass imported fine.

### Compatibility

- The minimum supported IviumSoft release is still 4.1242 (the release that introduced
  the scoped `IV_selectdevice_*` family and fixed the direct-mode trace calls). Adopting
  a measurement that is already running on the device requires 4.1247.

## [0.3.0rc3] - 2026-07-20

Third release candidate for 0.3.0. Adds a whole-run overview and tail-scoped task
summaries to `MeasurementReader`, so a still-growing measurement can be previewed
and polled without re-reading the whole run. Install it explicitly (pip ignores
pre-releases by default):

```
pip install pyvium==0.3.0rc3
```

### Added

- **Whole-run overview via `point_small`.** `MeasurementReader.read_overview_points()`
  returns IviumSoft's curated whole-run subset (~2-3% of points, spanning the entire
  run) as full `DataPoint`s, giving a shape-representative preview instead of
  `read_points(limit=N)`'s earliest-N slice. `MeasurementReader.has_overview()`
  reports whether the file carries the index; `read_overview_points` raises when it
  is absent (a missing curation index is not the same as an empty point set).
- **Tail-scoped `part_summaries`.** `MeasurementReader.part_summaries()` gains a
  `from_part_id` parameter, an inclusive `measurementpart_id` lower bound that seeks
  via the existing index so a live poller refreshes only the still-growing tail
  instead of re-scanning the whole run.

All additive and backward compatible: existing `part_summaries()` calls behave
exactly as before. Read-only and hardware-free.

## [0.3.0rc2] - 2026-07-10

Second release candidate for 0.3.0. Extends the SQLite measurement readers with
task-level (measurementpart) scoping so a large cycliscan (thousands of parts,
millions of points) can be read one task at a time instead of whole. Install it
explicitly (pip ignores pre-releases by default):

```
pip install pyvium==0.3.0rc2
```

### Added

- **Part/cycle scoping and a point cap on `MeasurementReader`.** `read_points` and
  `read_impedance` gain `measurementpart_id`, `cycle`, and `limit` parameters, all
  pushed into the SQL query, so the reader never materialises more rows than asked;
  `limit` combines with `after_point_id` to page a bounded window.
- **`MeasurementReader.part_summaries()`** returns one `MeasurementPartSummary` per
  non-empty part (its `point_count` and `t` range), for building a task picker
  without touching point data.
- **`MeasurementReader.latest_part_id()`** returns the highest part id that has
  points (the current task), for following a live run.
- New dataclass `MeasurementPartSummary`, exported from `pyvium.tools`.

All additive and backward compatible: existing `read_points()` / `read_impedance()`
calls behave exactly as before. Read-only and hardware-free.

## [0.3.0rc1] - 2026-06-19

Release candidate for 0.3.0. It bundles multi-instance and multichannel control,
an IviumSoft process lifecycle manager, and read-only readers for IviumSoft's
SQLite measurement files. Install it explicitly (pip ignores pre-releases by
default):

```
pip install pyvium==0.3.0rc1
```

### Added

- **Thread-safe instance scoping.** `Pyvium.on_instance(n)` (context manager) and
  `Pyvium.instance(n)` (`PyviumInstance` handle) select an IviumSoft instance and
  run commands against it atomically under the process-wide driver lock, so calls
  from several threads never land on the wrong instance.
- **Multichannel (Ivium-n-Soft) control.** `Pyvium.on_channel(m)`,
  `Pyvium.instance(n).channel(m)` (`PyviumChannel` handle), `select_channel`,
  `get_channel_statuses`, and `connect_device_to_channel` for driving channel tabs
  within an instance. Adds `ChannelStatus` and a `CoreBase` selected-channel shadow
  (the DLL has no getter for the active channel).
- **`IviumsoftInstanceManager`** for IviumSoft process lifecycle: `launch`, `close`,
  `adopt`, `discover`, `close_orphans`, and `list_instances`, mapping each process
  to its driver instance number. Ships with `ManagedInstance`, `UntrackedProcess`,
  and `DiscoveryReport`, plus native Win32 process helpers in `pyvium.util`.
- **Cold-start driver open.** `Pyvium.open_driver(verify_iviumsoft=False)` opens the
  driver with no IviumSoft instance running yet, so the manager can launch instances
  afterwards.
- **SQLite measurement readers** (`pyvium.tools`), pure file I/O with no DLL
  dependency:
  - `MeasurementReader` reads one `DataServer_*.idf.sqlite` file read-only and
    WAL-safe, so it can tail a measurement IviumSoft is still writing. Supports
    incremental tailing via `after_point_id` / `latest_point_id`, version-tolerant
    queries across DatabaseVersions 5-9, and export through `to_csv` / `to_dataframe`
    (pandas imported lazily).
  - `MeasurementIndex` reads the `index.sqlite` catalog.
  - New dataclasses `MeasurementInfo`, `MeasurementPart`, `DataPoint`,
    `ImpedancePoint`, and `IndexEntry`, plus `UnsupportedDatabaseVersionError`.
- **Active-instance scan caching** to avoid repeated 32-slot probes; the cache is
  invalidated by `open_driver` / `close_driver` and the instance manager.
- **Public device-status labels.** `DEVICE_STATUS_LABELS` (read-only code -> label
  map) and `device_status_label(code)` are now exported from `pyvium`, so consumers
  no longer need to reach into the private `_STATUS_LABELS`.
- **Full `IV_selectdevice_*` Core bindings.** Every scoped one-call function from
  IviumSoft 4.1242 (39 in total, across generic/direct/WE32/method-mode) is now
  bound on `Core` for callers who use the raw DLL layer directly. These have no
  `Pyvium` counterpart (the high-level API scopes instances via `on_instance`);
  they are `IV_selectdevice` + the base call fused and leave the selection parked
  on the target instance. A coverage test guards that `Core` binds every function
  declared in the bundled header.

### Changed

- Renamed the device handle to an instance handle (`PyviumInstance`) to match the
  DLL's actual semantics (`IV_selectdevice` selects an instance, not hardware).
- Bundled DLL updated to IviumSoft release 4.1242 (DLL version 203). This release
  removed `IV_selectdevicesetvalue(int, int, double)`, so `set_device_current` /
  `set_device_potential` now call the dedicated `IV_selectdevice_setcurrent` /
  `IV_selectdevice_setpotential` functions instead (public signatures unchanged).

### Fixed

- CSV export no longer writes blank lines between rows on Windows
  (`csv.writer` now controls the line endings).
- `get_current_trace`, `get_current_we2_trace`, and `get_potential_trace` now return
  the list of samples instead of the raw `(result_code, values)` tuple. The DLL crash
  that previously made these calls unusable is fixed in IviumSoft 4.1242.
- `tools.column_labels()` now defaults to the hardware-confirmed mapping
  (`y=potential, z=current`); it previously shipped the opposite provisional labels.
  The readers already expose the raw `x/y/z/q` columns on `DataPoint`, so this only
  affects the optional label helper.

### Compatibility

- Now supports Python 3.13, cffi 2.x, and pylint 3.x.
- Windows-only, and most functionality still requires IviumSoft installed/running
  (and, for many calls, connected hardware). The SQLite readers and IDF/CSV tools
  are the exception: they run without the DLL or hardware.

[0.3.0rc4]: https://github.com/Gnpd/pyvium/releases/tag/v0.3.0rc4
[0.3.0rc3]: https://github.com/Gnpd/pyvium/releases/tag/v0.3.0rc3
[0.3.0rc2]: https://github.com/Gnpd/pyvium/releases/tag/v0.3.0rc2
[0.3.0rc1]: https://github.com/Gnpd/pyvium/releases/tag/v0.3.0rc1
