'''Reader for a single IviumSoft measurement SQLite file (DataServer_*.idf.sqlite).

Pure file I/O over the stdlib sqlite3 module: no DLL, hardware-free and testable.
Opens the file read-only and WAL-safe so it can tail a measurement that IviumSoft
is still writing (see connect_readonly).
'''
from dataclasses import dataclass

from .data_processing_functions import DataProcessing
from .measurement_schema import (connect_readonly, decode_status,
                                 read_database_version, verify_database_version)


@dataclass
class MeasurementInfo:
    '''One row of the measurement table.'''
    measurement_id: int
    start_time: str | None
    end_time: str | None


@dataclass
class MeasurementPart:  # pylint: disable=too-many-instance-attributes
    '''One row of measurementpart: a cycle/level/channel grouping of points.'''
    measurementpart_id: int
    measurement_id: int
    cycle: int | None
    level: int | None
    tstep: int | None
    muxchannel: int | None
    wexchannel: int | None
    measvalue: float | None


@dataclass
class MeasurementPartSummary:
    '''A measurementpart plus its point_count and t-range.

        Lighter than reading a part's points: it lets a caller size and label each
        task (e.g. a cycliscan with thousands of parts) for a picker without
        touching the point data. Only parts that actually have points appear.'''
    measurementpart_id: int
    cycle: int | None
    level: int | None
    point_count: int
    t_min: float | None
    t_max: float | None


@dataclass
class DataPoint:  # pylint: disable=too-many-instance-attributes
    '''One measured point. x/y/z/q are the raw per-technique columns (see
        measurement_schema.column_labels); status decodes statusbyte.'''
    point_id: int
    t: float | None
    x: float | None
    y: float | None
    z: float | None
    q: float | None
    statusbyte: int | None
    measurementpart_id: int
    cycle: int | None
    level: int | None
    muxchannel: int | None
    wexchannel: int | None

    @property
    def status(self) -> dict:
        '''Decoded statusbyte (eovl/iovl/ext/flags/cr/bcr).'''
        return decode_status(self.statusbyte)


@dataclass
class ImpedancePoint:
    '''One impedance/FRA point (pointfra): frequency and complex impedance.'''
    point_id: int
    t: float | None
    frequency: float | None
    z_re: float | None
    z_im: float | None
    ohmic_resistance: float | None
    quality: float | None


_POINT_COLUMNS = ("point_id", "t", "x", "y", "z", "q", "statusbyte",
                  "measurementpart_id", "cycle", "level", "muxchannel", "wexchannel")


class MeasurementReader:
    '''Read-only reader for one measurement file.

        Use as a context manager so the connection is closed promptly (WAL
        readers must not linger):

            with MeasurementReader(path) as reader:
                for point in reader.read_points():
                    ...

        Validates the file's DatabaseVersion on open and raises
        UnsupportedDatabaseVersionError for versions it has not been verified
        against.'''

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._connection = None
        self._database_version = None
        self._table_columns_cache: dict[str, set] = {}

    def __enter__(self) -> "MeasurementReader":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def open(self) -> "MeasurementReader":
        '''Opens the read-only connection and validates the DatabaseVersion.'''
        self._connection = connect_readonly(self._db_path)
        self._table_columns_cache = {}
        self._database_version = read_database_version(self._connection)
        verify_database_version(self._database_version)
        return self

    def close(self) -> None:
        '''Closes the connection if open.'''
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._table_columns_cache = {}

    @property
    def database_version(self) -> int:
        '''The DatabaseVersion read from the metadata table.'''
        self._require_open()
        return self._database_version

    def metadata(self) -> dict:
        '''Returns the metadata table as a {key: value} dict.'''
        self._require_open()
        return {row["key"]: row["value"]
                for row in self._connection.execute("SELECT key, value FROM metadata")}

    def measurements(self) -> list[MeasurementInfo]:
        '''Returns one MeasurementInfo per row of the measurement table.'''
        self._require_open()
        rows = self._connection.execute(
            "SELECT measurement_id, start_time, end_time FROM measurement "
            "ORDER BY measurement_id")
        return [MeasurementInfo(row["measurement_id"], row["start_time"], row["end_time"])
                for row in rows]

    def method_parameters(self, measurement_id: int | None = None) -> dict:
        '''Returns the method parameters as a {name: value} dict.'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        rows = self._connection.execute(
            "SELECT k, v FROM method WHERE measurement_id = ?", (measurement_id,))
        return {row["k"]: row["v"] for row in rows}

    def measurement_parts(self, measurement_id: int | None = None) -> list[MeasurementPart]:
        '''Returns the measurementpart rows (cycle/level/channel groupings).

            muxchannel/wexchannel/measvalue were added in DatabaseVersions 6/7/9
            respectively; on older files they are reported as None.'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        present = self._table_columns("measurementpart")
        optional = ", ".join(name if name in present else f"NULL AS {name}"
                             for name in ("muxchannel", "wexchannel", "measvalue"))
        rows = self._connection.execute(
            "SELECT measurementpart_id, measurement_id, cycle, level, tstep, "
            f"{optional} FROM measurementpart "
            "WHERE measurement_id = ? ORDER BY measurementpart_id", (measurement_id,))
        return [MeasurementPart(
            row["measurementpart_id"], row["measurement_id"], row["cycle"], row["level"],
            row["tstep"], row["muxchannel"], row["wexchannel"], row["measvalue"])
            for row in rows]

    def read_points(self, measurement_id: int | None = None,
                    after_point_id: int | None = None,
                    measurementpart_id: int | None = None,
                    cycle: int | None = None,
                    limit: int | None = None) -> list[DataPoint]:
        '''Returns the measured points in point_id order.

            after_point_id returns only points with a greater point_id, which is
            how a live tailer fetches new data incrementally (WHERE point_id > ?).

            measurementpart_id / cycle scope the read to one task / cycle of the
            measurement -- essential for a large cycliscan, whose full point set
            can be millions of rows while a single part is only hundreds.

            limit is a hard SQL cap (LIMIT): it returns the first `limit` points in
            point_id order, so the reader never materialises more than that. Combine
            it with after_point_id to page a bounded window; on its own it truncates
            (it does not decimate), so the caller must decide whether more remain
            (e.g. by comparing against latest_point_id).'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        present = self._table_columns("measurementpart")
        mux = "mp.muxchannel" if "muxchannel" in present else "NULL"
        wex = "mp.wexchannel" if "wexchannel" in present else "NULL"
        query = (
            "SELECT p.point_id, p.t, p.x, p.y, p.z, p.q, p.statusbyte, "
            f"p.measurementpart_id, mp.cycle, mp.level, {mux} AS muxchannel, {wex} AS wexchannel "
            "FROM point p JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?")
        params: list = [measurement_id]
        if measurementpart_id is not None:
            query += " AND p.measurementpart_id = ?"
            params.append(measurementpart_id)
        if cycle is not None:
            query += " AND mp.cycle = ?"
            params.append(cycle)
        if after_point_id is not None:
            query += " AND p.point_id > ?"
            params.append(after_point_id)
        query += " ORDER BY p.point_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [DataPoint(*[row[column] for column in _POINT_COLUMNS])
                for row in self._connection.execute(query, params)]

    def part_summaries(
            self, measurement_id: int | None = None) -> list[MeasurementPartSummary]:
        '''Returns one MeasurementPartSummary per non-empty measurementpart.

            A single GROUP BY over point (indexed on measurementpart_id) yields
            each task's point_count and t-range, so a picker over a large cycliscan
            can list and size its tasks without reading any point data. Empty parts
            are skipped.'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        rows = self._connection.execute(
            "SELECT p.measurementpart_id, mp.cycle, mp.level, "
            "COUNT(*) AS point_count, MIN(p.t) AS t_min, MAX(p.t) AS t_max "
            "FROM point p JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ? "
            "GROUP BY p.measurementpart_id, mp.cycle, mp.level "
            "ORDER BY p.measurementpart_id", (measurement_id,))
        return [MeasurementPartSummary(
            row["measurementpart_id"], row["cycle"], row["level"],
            row["point_count"], row["t_min"], row["t_max"]) for row in rows]

    def read_impedance(self, measurement_id: int | None = None,
                       after_point_id: int | None = None,
                       measurementpart_id: int | None = None,
                       cycle: int | None = None,
                       limit: int | None = None) -> list[ImpedancePoint]:
        '''Returns the impedance/FRA points (frequency, Z', Z'') in point_id order.

            after_point_id, measurementpart_id, cycle and limit behave exactly as
            in read_points (incremental tailing, task/cycle scoping, hard SQL cap).

            Returns [] when the file has no pointfra table at all, which is the
            case for non-EIS techniques: a caller that does not know the technique
            up front can call this unconditionally without catching an error.'''
        self._require_open()
        if not self._table_columns("pointfra"):  # no FRA table -> non-EIS measurement
            return []
        measurement_id = self._resolve_measurement_id(measurement_id)
        query = (
            "SELECT f.point_id, p.t, f.f, f.z1, f.z2, f.ohr, f.fraquality "
            "FROM pointfra f JOIN point p ON p.point_id = f.point_id "
            "JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?")
        params: list = [measurement_id]
        if measurementpart_id is not None:
            query += " AND p.measurementpart_id = ?"
            params.append(measurementpart_id)
        if cycle is not None:
            query += " AND mp.cycle = ?"
            params.append(cycle)
        if after_point_id is not None:
            query += " AND f.point_id > ?"
            params.append(after_point_id)
        query += " ORDER BY f.point_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [ImpedancePoint(row["point_id"], row["t"], row["f"], row["z1"],
                               row["z2"], row["ohr"], row["fraquality"])
                for row in self._connection.execute(query, params)]

    def latest_point_id(self, measurement_id: int | None = None) -> int | None:
        '''Returns the highest point_id so far, or None if there are no points.

            A tailer stores this as its catch-up cursor (last_seen).'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        row = self._connection.execute(
            "SELECT MAX(p.point_id) AS max_point_id FROM point p "
            "JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?", (measurement_id,)).fetchone()
        return row["max_point_id"]

    def latest_part_id(self, measurement_id: int | None = None) -> int | None:
        '''Returns the highest measurementpart_id that has points, or None.

            The "current task" of a live cycliscan: a viewer can scope to it to
            keep a live plot bounded, and re-scope when it advances.'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        row = self._connection.execute(
            "SELECT MAX(p.measurementpart_id) AS max_part_id FROM point p "
            "JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?", (measurement_id,)).fetchone()
        return row["max_part_id"]

    def to_csv(self, file_path: str, measurement_id: int | None = None) -> None:
        '''Exports the points (with a header row) to a CSV file.'''
        points = self.read_points(measurement_id)
        rows = [list(_POINT_COLUMNS)]
        rows.extend([getattr(point, column) for column in _POINT_COLUMNS]
                    for point in points)
        DataProcessing.export_to_csv(rows, file_path)

    def to_dataframe(self, measurement_id: int | None = None):
        '''Returns the points as a pandas DataFrame (pandas imported lazily).'''
        try:
            import pandas  # pylint: disable=import-outside-toplevel
        except ImportError as error:
            raise ImportError(
                "to_dataframe requires pandas; install it or use read_points()."
            ) from error
        points = self.read_points(measurement_id)
        return pandas.DataFrame(
            [[getattr(point, column) for column in _POINT_COLUMNS] for point in points],
            columns=list(_POINT_COLUMNS))

    def _require_open(self) -> None:
        if self._connection is None:
            raise RuntimeError(
                "MeasurementReader is not open; use it as a context manager or call open().")

    def _table_columns(self, table: str) -> set:
        '''Returns the set of column names in a table (for version-tolerant queries).

            Columns were added across DatabaseVersions without removals, so a query
            can fall back to NULL for a column an older file does not have. An empty
            set means the table does not exist (PRAGMA table_info yields no rows),
            which callers use to detect optional tables such as pointfra.

            Memoised per table for the lifetime of the connection: the schema cannot
            change mid-file, so this avoids a PRAGMA on every read for a live tailer.'''
        cached = self._table_columns_cache.get(table)
        if cached is None:
            cached = {row["name"]
                      for row in self._connection.execute(f'PRAGMA table_info("{table}")')}
            self._table_columns_cache[table] = cached
        return cached

    def _resolve_measurement_id(self, measurement_id: int | None) -> int:
        if measurement_id is not None:
            return measurement_id
        row = self._connection.execute(
            "SELECT MIN(measurement_id) AS measurement_id FROM measurement").fetchone()
        if row is None or row["measurement_id"] is None:
            raise ValueError("No measurement found in this file")
        return row["measurement_id"]
