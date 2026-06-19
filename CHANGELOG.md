# Changelog

All notable changes to PYVIUM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

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
- **Terminology glossary** (`docs/terminology.md`) for *device* vs *instance* vs
  *channel*.

### Changed

- Renamed the device handle to an instance handle (`PyviumInstance`) to match the
  DLL's actual semantics (`IV_selectdevice` selects an instance, not hardware).
- Documentation: documented the SQLite readers, confirmed driver instance numbering
  is stable after a close, and corrected the terminology source reference.

### Fixed

- CSV export no longer writes blank lines between rows on Windows
  (`csv.writer` now controls the line endings).

### Compatibility

- Now supports Python 3.13, cffi 2.x, and pylint 3.x.
- Windows-only, and most functionality still requires IviumSoft installed/running
  (and, for many calls, connected hardware). The SQLite readers and IDF/CSV tools
  are the exception: they run without the DLL or hardware.

[0.3.0rc1]: https://github.com/SF-Tec/pyvium/releases/tag/v0.3.0rc1
