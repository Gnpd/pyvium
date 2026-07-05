## Pyvium and Core methods

:heavy_check_mark: ready
:small_orange_diamond: under development
:x: not working

### General

| Pyvium Methods                                          | Core Methods                               |
| ------------------------------------------------------- | ------------------------------------------ |
| :heavy_check_mark: open_driver()                        | :heavy_check_mark: IV_open()               |
| :heavy_check_mark: close_driver()                       | :heavy_check_mark: IV_close()              |
| :heavy_check_mark: get_max_device_number()              | :heavy_check_mark: IV_MaxDevices()         |
| :heavy_check_mark: get_active_iviumsoft_instances()     |                                            |
| :heavy_check_mark: select_iviumsoft_instance(int)       | :heavy_check_mark: IV_selectdevice(int)    |
| :heavy_check_mark: get_device_status()                  | :heavy_check_mark: IV_getdevicestatus()    |
| :heavy_check_mark: is_iviumsoft_running()               |                                            |
| :heavy_check_mark: get_device_serial_number()           | :heavy_check_mark: IV_readSN()             |
| :heavy_check_mark: select_serial_number(str)            | :heavy_check_mark: IV_SelectSn(str)        |
| :heavy_check_mark: connect_device()                     | :heavy_check_mark: IV_connect(int)         |
| :heavy_check_mark: disconnect_device()                  |                                            |
| :heavy_check_mark: get_version_host()                   | :heavy_check_mark: IV_VersionHost(version) |
| :heavy_check_mark: get_dll_version()                    | :heavy_check_mark: IV_VersionDll()         |
| :heavy_check_mark: check_dll_version()                  | :heavy_check_mark: IV_VersionCheck()       |
| :heavy_check_mark: get_host_handle()                    | :heavy_check_mark: IV_HostHandle()         |
| :heavy_check_mark: get_iviumsoft_version()              | :heavy_check_mark: IV_VersionDllFile()     |
| :heavy_check_mark: get_dll_version_string()             | :heavy_check_mark: IV_VersionDllFileStr()  |
| :heavy_check_mark: select_channel(int)                  | :heavy_check_mark: IV_SelectChannel(int)   |
| :heavy_check_mark: get_channel_statuses(int)            |                                            |
| :heavy_check_mark: connect_device_to_channel(str, int)  |                                            |

### Direct Mode

| Pyvium Methods                                          | Core Methods                                                    |
| ------------------------------------------------------- | --------------------------------------------------------------- |
| :heavy_check_mark: get_cell_status()                    | :heavy_check_mark: IV_getcellstatus()                           |
| :heavy_check_mark: set_connection_mode(int)             | :heavy_check_mark: IV_setconnectionmode(int)                    |
| :heavy_check_mark: set_cell_on()                        | :heavy_check_mark: IV_setcellon(int)                            |
| :heavy_check_mark: set_cell_off()                       |                                                                 |
| :heavy_check_mark: set_potential(float)                 | :heavy_check_mark: IV_setpotential(float)                       |
| :heavy_check_mark: set_we2_potential(float)             | :heavy_check_mark: IV_setpotentialWE2(float)                    |
| :heavy_check_mark: set_current(float)                   | :heavy_check_mark: IV_setcurrent(float)                         |
| :heavy_check_mark: get_potential()                      | :heavy_check_mark: IV_getpotential()                            |
| :heavy_check_mark: set_current_range(int)               | :heavy_check_mark: IV_setcurrentrange(int)                      |
| :heavy_check_mark: set_we2_current_range(int)           | :heavy_check_mark: IV_setcurrentrangeWE2(int)                   |
| :heavy_check_mark: get_current()                        | :heavy_check_mark: IV_getcurrent()                              |
| :heavy_check_mark: get_we2_current()                    | :heavy_check_mark: IV_getcurrentWE2()                           |
| :heavy_check_mark: set_filter(int)                      | :heavy_check_mark: IV_setfilter(int)                            |
| :heavy_check_mark: set_stability(int)                   | :heavy_check_mark: IV_setstability(int)                         |
| :heavy_check_mark: set_bistat_mode(int)                 | :heavy_check_mark: IV_setbistatmode(int)                        |
| :heavy_check_mark: set_dac(int, float)                  | :heavy_check_mark: IV_setdac(int, float)                        |
| :heavy_check_mark: get_adc(int)                         | :heavy_check_mark: IV_getadc(int, float)                        |
| :heavy_check_mark: set_mux_channel(int)                 | :heavy_check_mark: IV_setmuxchannel(int)                        |
| :heavy_check_mark: set_digital_output(int)              | :heavy_check_mark: IV_setdigout(int)                            |
| :heavy_check_mark: get_digital_input()                  | :heavy_check_mark: IV_getdigin(int)                             |
| :heavy_check_mark: set_ac_frequency(float)              | :heavy_check_mark: IV_setfrequency(float)                       |
| :heavy_check_mark: set_ac_amplitude(float)              | :heavy_check_mark: IV_setamplitude(float)                       |
| :heavy_check_mark: get_current_trace(int, float)        | :heavy_check_mark: IV_getcurrenttrace(npoints, rate, values)        |
| :heavy_check_mark: get_current_we2_trace(int, float)    | :heavy_check_mark: IV_getcurrentWE2trace(npoints, rate, values)     |
| :heavy_check_mark: get_potential_trace(int, float)      | :heavy_check_mark: IV_getpotentialtrace(npoints, rate, values)      |
| :heavy_check_mark: set_device_current(int, float)       | :heavy_check_mark: IV_selectdevice_setcurrent(int, float)       |
| :heavy_check_mark: set_device_potential(int, float)     | :heavy_check_mark: IV_selectdevice_setpotential(int, float)     |
| :small_orange_diamond: set_we32_channel(int)            | :small_orange_diamond: IV_we32setchannel(index)                 |
| :small_orange_diamond: set_we32_offset(int, float)      | :small_orange_diamond: IV_we32setoffset(index, value)           |
| :small_orange_diamond: set_we32_offsets(int, list)      | :small_orange_diamond: IV_we32setoffsets(nval, values)          |
| :small_orange_diamond: get_we32_offsets(int)            | :small_orange_diamond: IV_we32getoffsets(nval, values)          |
| :small_orange_diamond: read_we32_currents()             | :small_orange_diamond: IV_we32readcurrents(values)              |

### Method Mode

| Pyvium Methods                                          | Core Methods                                                    |
| ------------------------------------------------------- | --------------------------------------------------------------- |
| :heavy_check_mark: load_method(str)                     | :heavy_check_mark: IV_readmethod(fname)                         |
| :heavy_check_mark: save_method(str)                     | :heavy_check_mark: IV_savemethod(fname)                         |
| :heavy_check_mark: start_method(str)                    | :heavy_check_mark: IV_startmethod(fname)                        |
| :heavy_check_mark: abort_method()                       | :heavy_check_mark: IV_abort()                                   |
| :heavy_check_mark: save_data(str)                       | :heavy_check_mark: IV_savedata(fname)                           |
| :heavy_check_mark: save_dataset(str)                    | :heavy_check_mark: IV_savedataset(fname)                        |
| :heavy_check_mark: set_method_parameter(str, str)       | :heavy_check_mark: IV_setmethodparameter(parname, parvalue)     |
| :heavy_check_mark: get_available_data_points_number()   | :heavy_check_mark: IV_Ndatapoints(value)                        |
| :heavy_check_mark: get_data_point(int)                  | :heavy_check_mark: IV_getdata(pointnr, x, y, z)                 |
| :heavy_check_mark: get_data_point_from_scan(int, int)   | :heavy_check_mark: IV_getdatafromline(pointnr, scannr, x, y, z) |
| :heavy_check_mark: get_db_file_name()                   | :heavy_check_mark: IV_getDbFileName(fname)                      |
| :heavy_check_mark: update_temperature(float)            | :heavy_check_mark: IV_UpdateTemperature(value)                  |

### Batch Mode

| Pyvium Methods                                          | Core Methods                               |
| ------------------------------------------------------- | ------------------------------------------ |
| :heavy_check_mark: set_status_par(int)                  | :heavy_check_mark: IV_StatusParSet(value)  |
| :heavy_check_mark: get_status_par()                     | :heavy_check_mark: IV_StatusParGet(value)  |

### Instance and channel scoping

Thread-safe selection of an IviumSoft instance (and Multichannel-control channel tab). The
context managers hold the driver lock across the selection and the commands that follow it; the
handles expose the full Pyvium API scoped to an instance (and channel). These orchestrate the
`IV_selectdevice` / `IV_SelectChannel` calls rather than mapping 1:1 to a DLL function. See
`docs/terminology.md` for device/instance/channel terms.

| Pyvium API | Description |
| --- | --- |
| :heavy_check_mark: `Pyvium.on_instance(n)` | Context manager: select instance `n`, run the block under the driver lock, restore the previous selection (even on error) |
| :heavy_check_mark: `Pyvium.instance(n)` -> `PyviumInstance` | Handle bound to instance `n`; every Pyvium call on it runs inside `on_instance(n)` |
| :heavy_check_mark: `Pyvium.on_channel(m)` | Context manager: select channel tab `m` atomically; nest inside `on_instance` |
| :heavy_check_mark: `Pyvium.instance(n).channel(m)` -> `PyviumChannel` | Handle bound to instance `n` + channel `m`; every call scopes both selections |

### Instance lifecycle management

`IviumsoftInstanceManager` launches, tracks, adopts and closes IviumSoft processes, mapping each
to its driver instance number. Windows-only (uses native Win32 process helpers). Pair with the
cold-start `open_driver(verify_iviumsoft=False)`.

| Class / method | Description |
| --- | --- |
| :heavy_check_mark: `IviumsoftInstanceManager(exe_path=..., ...)` | Manager over IviumSoft processes |
| :heavy_check_mark: `.launch()` -> `ManagedInstance` | Start one IviumSoft process and map it to the new driver instance number |
| :heavy_check_mark: `.close(instance_number, force=False)` | Gracefully close an instance (refuses a measuring one unless `force`) |
| :heavy_check_mark: `.adopt(instance_number, pid)` | Re-attach to an instance launched outside the manager |
| :heavy_check_mark: `.discover()` -> `DiscoveryReport` | Read-only: pair tracked instances, orphan instance numbers and untracked processes |
| :heavy_check_mark: `.close_orphans(force=False)` | Close every untracked IviumSoft process the manager does not track |
| :heavy_check_mark: `.list_instances()` -> `list[ManagedInstance]` | One record per active instance (managed carry a pid; orphans have `pid=None`) |

## Tools Methods
| Tools Methods (DataProcessing)                                | Description                                                                                    |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| :heavy_check_mark: export_to_csv(data, file_path)             | Saves data on a .csv file                                                                      |
| :heavy_check_mark: get_idf_data(idf_path)                     | Extracts the primary data from a ivium .idf file and returns a list of points (data matrix)    |
| :heavy_check_mark: get_all_idf_data(idf_path)                 | Extracts all data (primary and extra data) from a ivium .idf file and returns a data dictionary |
| :heavy_check_mark: convert_idf_to_csv(idf_path)               | Extracts the data from a ivium .idf file and saves the data to a .csv file                     |
| :heavy_check_mark: convert_idf_dir_to_csv(idf_dir_path='.')   | Extracts the data of all .idf files on a directory and saves the data to .csv files            |

### Measurement SQLite readers

Read the SQLite files IviumSoft writes (`DataServer_*.idf.sqlite`) and the catalog
(`index.sqlite`). Read-only, WAL-safe, schema-versioned (DatabaseVersions 5-9 verified); no DLL or
hardware needed. See `docs/terminology.md` for device/instance/channel terms.

| Class / method | Description |
| --- | --- |
| :heavy_check_mark: `MeasurementReader(path)` | Context-managed reader for one measurement file; validates DatabaseVersion |
| :heavy_check_mark: `.metadata()` / `.database_version` | metadata table as a dict / the DatabaseVersion |
| :heavy_check_mark: `.measurements()` / `.method_parameters()` / `.measurement_parts()` | measurement rows / method key-values / cycle-level-channel parts |
| :heavy_check_mark: `.read_points(after_point_id=None)` | Data points (t,x,y,z,q + decoded status + part context); `after_point_id` for incremental tailing |
| :heavy_check_mark: `.read_impedance(after_point_id=None)` | FRA/EIS points (frequency, Z', Z'') |
| :heavy_check_mark: `.latest_point_id()` | Highest point_id (tailer catch-up cursor) |
| :heavy_check_mark: `.to_csv(path)` / `.to_dataframe()` | Export points to CSV / pandas (pandas optional, lazy import) |
| :heavy_check_mark: `MeasurementIndex(path)` | Context-managed reader for index.sqlite |
| :heavy_check_mark: `.entries(...)` | Filter the catalog (serial, device, technique, title, project, operator, date range, limit) |
| :heavy_check_mark: `.resolve_path(entry, base_dir)` / `.open_measurement(entry, base_dir)` | Build a file path / open its MeasurementReader |
