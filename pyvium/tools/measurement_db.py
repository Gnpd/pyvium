'''Reader for a single IviumSoft measurement SQLite file (DataServer_*.idf.sqlite).

Pure file I/O over the stdlib sqlite3 module: no DLL, hardware-free and testable.
Opens the file read-only and WAL-safe so it can tail a measurement that IviumSoft
is still writing (see connect_readonly / INTEGRATION_PLAN data plane).
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

    def __enter__(self) -> "MeasurementReader":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def open(self) -> "MeasurementReader":
        '''Opens the read-only connection and validates the DatabaseVersion.'''
        self._connection = connect_readonly(self._db_path)
        self._database_version = read_database_version(self._connection)
        verify_database_version(self._database_version)
        return self

    def close(self) -> None:
        '''Closes the connection if open.'''
        if self._connection is not None:
            self._connection.close()
            self._connection = None

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
        '''Returns the measurementpart rows (cycle/level/channel groupings).'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        rows = self._connection.execute(
            "SELECT measurementpart_id, measurement_id, cycle, level, tstep, "
            "muxchannel, wexchannel, measvalue FROM measurementpart "
            "WHERE measurement_id = ? ORDER BY measurementpart_id", (measurement_id,))
        return [MeasurementPart(
            row["measurementpart_id"], row["measurement_id"], row["cycle"], row["level"],
            row["tstep"], row["muxchannel"], row["wexchannel"], row["measvalue"])
            for row in rows]

    def read_points(self, measurement_id: int | None = None,
                    after_point_id: int | None = None) -> list[DataPoint]:
        '''Returns the measured points in point_id order.

            after_point_id returns only points with a greater point_id, which is
            how a live tailer fetches new data incrementally (WHERE point_id > ?).'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        query = (
            "SELECT p.point_id, p.t, p.x, p.y, p.z, p.q, p.statusbyte, "
            "p.measurementpart_id, mp.cycle, mp.level, mp.muxchannel, mp.wexchannel "
            "FROM point p JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?")
        params: list = [measurement_id]
        if after_point_id is not None:
            query += " AND p.point_id > ?"
            params.append(after_point_id)
        query += " ORDER BY p.point_id"
        return [DataPoint(*[row[column] for column in _POINT_COLUMNS])
                for row in self._connection.execute(query, params)]

    def read_impedance(self, measurement_id: int | None = None,
                       after_point_id: int | None = None) -> list[ImpedancePoint]:
        '''Returns the impedance/FRA points (frequency, Z', Z'') in point_id order.

            after_point_id behaves as in read_points for incremental tailing.'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        query = (
            "SELECT f.point_id, p.t, f.f, f.z1, f.z2, f.ohr, f.fraquality "
            "FROM pointfra f JOIN point p ON p.point_id = f.point_id "
            "JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?")
        params: list = [measurement_id]
        if after_point_id is not None:
            query += " AND f.point_id > ?"
            params.append(after_point_id)
        query += " ORDER BY f.point_id"
        return [ImpedancePoint(row["point_id"], row["t"], row["f"], row["z1"],
                               row["z2"], row["ohr"], row["fraquality"])
                for row in self._connection.execute(query, params)]

    def latest_point_id(self, measurement_id: int | None = None) -> int | None:
        '''Returns the highest point_id so far, or None if there are no points.

            A tailer stores this as its catch-up cursor (last_seen).'''
        self._require_open()
        measurement_id = self._resolve_measurement_id(measurement_id)
        row = self._connection.execute(
            "SELECT MAX(p.point_id) FROM point p "
            "JOIN measurementpart mp ON mp.measurementpart_id = p.measurementpart_id "
            "WHERE mp.measurement_id = ?", (measurement_id,)).fetchone()
        return row[0]

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

    def _resolve_measurement_id(self, measurement_id: int | None) -> int:
        if measurement_id is not None:
            return measurement_id
        row = self._connection.execute(
            "SELECT MIN(measurement_id) FROM measurement").fetchone()
        if row is None or row[0] is None:
            raise ValueError("No measurement found in this file")
        return row[0]
