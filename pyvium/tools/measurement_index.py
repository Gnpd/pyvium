'''Reader for the IviumSoft measurement catalog (index.sqlite).

The index has one table, measurements, with one row per stored measurement and
the location (file + path) of its DataServer_*.sqlite file. Use it to browse
history and to find the file backing a given serial/technique/time, then hand the
resolved path to MeasurementReader. Pure read-only file I/O.
'''
from dataclasses import dataclass
from pathlib import Path

from .measurement_db import MeasurementReader
from .measurement_schema import connect_readonly


@dataclass
class IndexEntry:  # pylint: disable=too-many-instance-attributes
    '''One row of the index measurements table.'''
    file: str
    path: str
    measurement_id: int
    serialnumber: str | None
    device_alias: str | None
    start_time: str | None
    end_time: str | None
    technique: str | None
    method: str | None
    title: str | None
    project: str | None
    operator: str | None
    filesize: int | None
    muxchannel: int | None
    wexchannels: int | None
    dbver: int | None


_ENTRY_COLUMNS = ("file", "path", "measurement_id", "serialnumber", "device_alias",
                  "start_time", "end_time", "technique", "method", "title", "project",
                  "operator", "filesize", "muxchannel", "wexchannels", "dbver")


class MeasurementIndex:
    '''Read-only reader for index.sqlite.

        Use as a context manager:

            with MeasurementIndex(index_path) as index:
                for entry in index.entries(serialnumber="P33162", technique="CycliScan"):
                    with index.open_measurement(entry, base_dir) as reader:
                        ...'''

    def __init__(self, index_path: str):
        self._index_path = index_path
        self._connection = None

    def __enter__(self) -> "MeasurementIndex":
        self.open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def open(self) -> "MeasurementIndex":
        '''Opens the read-only connection.'''
        self._connection = connect_readonly(self._index_path)
        return self

    def close(self) -> None:
        '''Closes the connection if open.'''
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def entries(self, *,  # pylint: disable=too-many-arguments
                serialnumber: str | None = None, device_alias: str | None = None,
                technique: str | None = None, title_contains: str | None = None,
                project: str | None = None, operator: str | None = None,
                start_after: str | None = None, start_before: str | None = None,
                limit: int | None = None) -> list[IndexEntry]:
        '''Returns catalog entries matching the given filters (all optional).

            Equality filters: serialnumber, device_alias, technique, project,
            operator. title_contains is a substring match. start_after/start_before
            bound start_time (string comparison works for ISO-like timestamps).
            Results are newest-first; limit caps the count.'''
        if self._connection is None:
            raise RuntimeError(
                "MeasurementIndex is not open; use it as a context manager or call open().")
        conditions: list[str] = []
        params: list = []
        for column, value in (("serialnumber", serialnumber), ("device_alias", device_alias),
                              ("technique", technique), ("project", project),
                              ("operator", operator)):
            if value is not None:
                conditions.append(f"{column} = ?")
                params.append(value)
        if title_contains is not None:
            conditions.append("title LIKE ?")
            params.append(f"%{title_contains}%")
        if start_after is not None:
            conditions.append("start_time >= ?")
            params.append(start_after)
        if start_before is not None:
            conditions.append("start_time <= ?")
            params.append(start_before)

        query = f"SELECT {', '.join(_ENTRY_COLUMNS)} FROM measurements"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY start_time DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [IndexEntry(*[row[column] for column in _ENTRY_COLUMNS])
                for row in self._connection.execute(query, params)]

    @staticmethod
    def resolve_path(entry: IndexEntry, base_dir: str) -> str:
        '''Builds the on-disk path to an entry's measurement file.

            base_dir is the DataServer root; entry.path is its subdirectory
            (often empty) and entry.file the filename.'''
        return str(Path(base_dir) / (entry.path or "") / entry.file)

    def open_measurement(self, entry: IndexEntry, base_dir: str) -> MeasurementReader:
        '''Convenience: returns an (unopened) MeasurementReader for an entry.'''
        return MeasurementReader(self.resolve_path(entry, base_dir))
