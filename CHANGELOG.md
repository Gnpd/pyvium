# Changelog

All notable changes to PYVIUM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

## [0.3.0] - 2026-08-30

First stable release of the 0.3 line, developed across five release candidates between
2026-06-19 and 2026-08-27 and folded together here. Against 0.2.2 it adds multi-instance and
multichannel control, a lifecycle manager for IviumSoft processes, and read-only readers for
IviumSoft's SQLite measurement files, and refreshes the bundled driver to IviumSoft 4.1247.

```
pip install pyvium==0.3.0
```

### Added

- **Thread-safe instance scoping.** `Pyvium.on_instance(n)` (context manager) and
  `Pyvium.instance(n)` (`PyviumInstance` handle) select an IviumSoft instance and run commands
  against it atomically under a process-wide driver lock, so calls from several threads never
  land on the wrong instance.

- **Multichannel (Ivium-n-Soft) control.** `Pyvium.on_channel(m)`,
  `Pyvium.instance(n).channel(m)` (`PyviumChannel` handle), `select_channel`,
  `get_channel_statuses` and `connect_device_to_channel`, which verifies the connection by
  reading the serial back, because `IV_connect` is asynchronous and takes the first available
  device rather than the one that was selected; a connection that lands on the wrong instrument
  is disconnected again rather than reported as success. It takes an optional `alias`, the
  IviumSoft dropdown token `IV_SelectSn` selects by, which equals the serial on single-channel
  devices but not on a multichannel frame, where each channel has its own token (`Oc-0-3`) and
  the serial alone selects nothing. Adds `ChannelStatus`.

- **`IviumsoftInstanceManager`**, a lifecycle manager for IviumSoft processes: `launch`,
  `close`, `terminate`, `adopt`, `discover`, `close_orphans` and `list_instances`, each
  process mapped to the driver instance number it registered with. Ships with
  `ManagedInstance`, `UntrackedProcess` and `DiscoveryReport`, plus native Win32 process
  helpers in `pyvium.util`. `Pyvium.open_driver(verify_iviumsoft=False)` opens the driver cold,
  with no IviumSoft running yet, so the manager can launch the first instance.

- **SQLite measurement readers** (`pyvium.tools`), pure file I/O with no DLL or hardware
  dependency. `MeasurementReader` reads one `DataServer_*.idf.sqlite` read-only and WAL-safe,
  so it can tail a measurement IviumSoft is still writing: incremental tailing through
  `after_point_id` / `latest_point_id`, task-level scoping through `measurementpart_id`,
  `cycle` and `limit`, per-task `part_summaries()` with a `from_part_id` tail bound, a
  whole-run preview through `read_overview_points()` built on IviumSoft's curated
  `point_small` index, and export through `to_csv` / `to_dataframe` (pandas imported lazily).
  `MeasurementIndex` reads the `index.sqlite` catalog. Queries are version-tolerant across
  DatabaseVersions 5-9. Adds `MeasurementInfo`, `MeasurementPart`, `MeasurementPartSummary`,
  `DataPoint`, `ImpedancePoint`, `IndexEntry` and `UnsupportedDatabaseVersionError`.

- **Full `IV_selectdevice_*` Core bindings.** All 39 scoped one-call functions introduced by
  IviumSoft 4.1242 are bound on `Core` for callers using the raw DLL layer. They have no
  `Pyvium` counterpart, since the high-level API scopes instances through `on_instance`, and
  they leave the selection parked on their target instance. A coverage test guards that `Core`
  binds every function declared in the bundled header.

- **Active-instance scan caching**, so a status poller does not repeat the 32-slot probe;
  invalidated by `open_driver` / `close_driver` and by the instance manager.

- **Public device-status labels**: `DEVICE_STATUS_LABELS` and `device_status_label(code)`, so
  consumers no longer reach into a private map.

- **`UnexpectedResultCodeError`** (`pyvium.errors`), carrying the offending value on a
  `result_code` attribute so callers can branch on it without parsing the message.

### Changed

Behaviour changes for anyone upgrading from 0.2.x:

- **Bundled DLL updated to IviumSoft 4.1247.** Both binaries were replaced;
  `IV_VersionDllFileStr()` reports `4.1247.10407`. The driver API version is unchanged
  (`IV_VersionDll()` still returns 203), so no `Core` or `Pyvium` signature changed.

- **The direct-mode trace getters return their samples.** `get_current_trace`,
  `get_current_we2_trace` and `get_potential_trace` return the list of samples instead of a raw
  `(result_code, values)` tuple. The DLL crash that made these calls unusable is fixed in
  4.1242.

- **The data point getters raise instead of returning a stale reading.** `get_data_point` and
  `get_data_point_from_scan` discarded the DLL result code and returned their output buffers
  whatever it said; the DLL leaves those buffers untouched on a failed read, so an index past
  the end returned the previous point verbatim and a polling loop duplicated points instead of
  failing. Both now raise `IndexError` past the end and `ValueError` below index 1. Both
  indices are 1-based, which was undocumented, and `get_data_point_from_scan` refuses a
  `scan_index` below 1 before the call reaches the DLL: on 4.1247 a `0` reports success and
  then terminates the IviumSoft process, and a `-1` never returns while IviumSoft allocates
  memory without bound. `get_available_data_points_number` checks its result code too.

- **A result code or device status outside the documented set is no longer reported as
  success.** An unrecognised DLL result code now raises `UnexpectedResultCodeError`, and an
  unmodelled device status no longer raises `KeyError`. Both affect values nobody has observed,
  so no existing path should change; if one does surface, that command was failing silently
  before.

### Fixed

- **Selection and cached state the library keeps outside the DLL.** The DLL exposes no getter
  for its selected instance or channel, so `Core` shadows both. A driver close/reopen left
  those shadows stale, an active-instance scan could park the selection on an instance that had
  gone, a scan already in flight could undo a cache invalidation, and the two `set_device_*`
  setpoints moved the global selection as a side effect without taking the driver lock, which
  could redirect a running `on_instance` block from another thread. All now hold the lock and
  restore or reset the selection as documented.

- **Closing an IviumSoft instance no longer leaks its instance number.** A measuring instance
  answers `WM_CLOSE` with a modal confirmation rather than closing, one per window messaged, so
  an unattended close timed out and escalated to `TerminateProcess`, and a terminated IviumSoft
  never deregisters. `close()` and `close_orphans()` now answer that dialog, with `on_measuring`
  choosing whether the measurement continues on the device, ends, or the close is refused;
  `force` gates only the `TerminateProcess` escalation. As a second line of defence the
  active-instance scan drops a slot whose host window is provably gone, which is the only way
  to spot one: a leaked slot answers every DLL call as though it were alive, with the status it
  last held, result code `0` throughout, and a point count aliased from the previous read on a
  live slot.

- **The instance manager no longer risks touching an unrelated process.** It records each
  process's OS start time (`ManagedInstance.started_at`) and checks the image path, so a pid
  Windows recycled is never messaged or terminated. `windows_process.is_process_running` no
  longer misreads a process that exits with code 259 (`STILL_ACTIVE`), `list_instances()` no
  longer forgets a process that is still running, and an IviumSoft that has already left the
  driver can now be cleaned up rather than stranded.

- **`MeasurementReader.open()` and `MeasurementIndex.open()` close a previous connection** when
  a reader is reopened, instead of leaking it.

- **CSV export no longer writes blank lines between rows on Windows** (`csv.writer` now
  controls the line endings).

### Compatibility

- Windows-only. Supports Python 3.13, cffi 2.x and pylint 3.x.
- Minimum IviumSoft release 4.1242, the release that introduced the scoped `IV_selectdevice_*`
  family and fixed the direct-mode trace calls. Adopting a measurement already running on the
  device requires 4.1247, whose driver-side fix means connecting no longer flushes and
  terminates an ongoing run; before it, only the IviumSoft **Connect** button adopted one.
- Most functionality needs IviumSoft installed and running, and for many calls connected
  hardware. The SQLite readers and the IDF/CSV tools are the exception: they run without the
  DLL or hardware.

### Note for users of the release candidates

`IviumsoftInstanceManager.close()` changed shape late in the cycle. `force` now gates only the
`TerminateProcess` escalation and not the busy check, so `close(n)` on a measuring instance
closes it gracefully with the run continuing on the device where it used to raise
`DeviceBusyError` (pass `on_measuring='cancel'` for the old refusal), and `close(n)` on a hung
instance raises `TimeoutError` instead of terminating it and leaking the number. The manager is
new in 0.3.0, so this affects only code written against rc1 through rc5.

[0.3.0]: https://github.com/Gnpd/pyvium/releases/tag/v0.3.0
