'''Tests for the measurement index (catalog) reader.

A tiny index.sqlite is synthesised in a tmp dir, so no real catalog data is
committed and no hardware is needed.'''
# Tests are self-describing and use pytest fixtures (redefined-outer-name).
# pylint: disable=missing-function-docstring,redefined-outer-name

import os
import sqlite3

import pytest

from pyvium.tools import IndexEntry, MeasurementIndex, MeasurementReader

_DDL = """
CREATE TABLE measurements (
    file VARCHAR(255), path VARCHAR(255), measurement_id INTEGER,
    serialnumber VARCHAR(255), device_alias VARCHAR(255), start_time VARCHAR(255),
    end_time VARCHAR(255), technique VARCHAR(255), method VARCHAR(255),
    title VARCHAR(255), project VARCHAR(255), operator VARCHAR(255),
    filesize INTEGER, muxchannel INTEGER, wexchannels INTEGER, dbver INTEGER,
    PRIMARY KEY(file, measurement_id));
"""

_ROWS = [
    # file, path, mid, serial, alias, start, end, technique, method, title,
    # project, operator, filesize, mux, wex, dbver
    ("DataServer_A_2021.sqlite", "", 1, "P33162", "P33162", "2021-08-30 22:02:30",
     "2021-08-30 22:10:00", "ChronoPotentiometry", "cp.imf", "Scan 1", "projX",
     "alice", 1000, 0, 0, 6),
    ("DataServer_B_2023.sqlite", "UCM\\CompackStat", 1, "P33162", "P33162",
     "2023-02-14 11:45:14", "2023-02-14 12:00:00", "Mixed Mode", "mm.imf",
     "WennerProve", "projY", "bob", 2000, 0, 1, 8),
    ("DataServer_C_2024.sqlite", "", 1, "R54223", "Oc-0-3", "2024-10-08 09:55:09",
     "2024-10-08 11:06:22", "CycliScan", "cs.imf", "Battery test", "projY",
     "alice", 3000, 0, 1, 9),
]


@pytest.fixture
def index_path(tmp_path):
    path = str(tmp_path / "index.sqlite")
    con = sqlite3.connect(path)
    con.executescript(_DDL)
    con.executemany(
        "INSERT INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", _ROWS)
    con.commit()
    con.close()
    return path


def test_reopen_closes_the_previous_connection(index_path):
    index = MeasurementIndex(index_path)
    index.open()
    # Private access is deliberate: the connection is not exposed publicly, and
    # holding a reference is exactly what keeps an abandoned one alive.
    first_connection = index._connection  # pylint: disable=protected-access

    index.open()

    with pytest.raises(sqlite3.ProgrammingError):
        first_connection.execute("SELECT 1")
    assert index.entries()  # still usable
    index.close()


def test_entries_newest_first(index_path):
    with MeasurementIndex(index_path) as index:
        entries = index.entries()
    assert all(isinstance(e, IndexEntry) for e in entries)
    assert [e.file for e in entries] == [
        "DataServer_C_2024.sqlite", "DataServer_B_2023.sqlite", "DataServer_A_2021.sqlite"]


def test_filter_by_serial(index_path):
    with MeasurementIndex(index_path) as index:
        entries = index.entries(serialnumber="P33162")
    assert {e.file for e in entries} == {
        "DataServer_A_2021.sqlite", "DataServer_B_2023.sqlite"}


def test_filter_by_serial_is_case_insensitive(index_path):
    # IviumSoft stores the same device under different casing depending on its
    # power source, so a serial filter must match regardless of case.
    with MeasurementIndex(index_path) as index:
        lower = index.entries(serialnumber="p33162")
        upper = index.entries(serialnumber="P33162")
    assert {e.file for e in lower} == {e.file for e in upper} == {
        "DataServer_A_2021.sqlite", "DataServer_B_2023.sqlite"}


def test_title_contains_supports_like_wildcards(index_path):
    """Documented behaviour, not an oversight: _ and % are wildcards.

        Operator-typed titles are rarely remembered exactly, and escaping these
        would turn searches that find something into searches that find nothing:
        no real title holds a literal _ or %, so an escaped "Scan_1" matches
        zero rows while the wildcard form finds "Scan 1"."""
    with MeasurementIndex(index_path) as index:
        assert [e.title for e in index.entries(title_contains="Scan_1")] == ["Scan 1"]
        assert [e.title for e in index.entries(title_contains="Battery%test")] == [
            "Battery test"]
        # A term without wildcards is still a plain substring match.
        assert [e.title for e in index.entries(title_contains="Wenner")] == [
            "WennerProve"]


def test_filter_by_technique_and_title_substring(index_path):
    with MeasurementIndex(index_path) as index:
        cycliscan = index.entries(technique="CycliScan")
        battery = index.entries(title_contains="Battery")
    assert [e.file for e in cycliscan] == ["DataServer_C_2024.sqlite"]
    assert [e.file for e in battery] == ["DataServer_C_2024.sqlite"]


def test_filter_by_date_range_and_limit(index_path):
    with MeasurementIndex(index_path) as index:
        in_range = index.entries(start_after="2023-01-01", start_before="2023-12-31")
        capped = index.entries(limit=1)
    assert [e.file for e in in_range] == ["DataServer_B_2023.sqlite"]
    assert len(capped) == 1 and capped[0].file == "DataServer_C_2024.sqlite"


def test_resolve_path_with_and_without_subdir(index_path):
    with MeasurementIndex(index_path) as index:
        entries = {e.file: e for e in index.entries()}
    base = os.path.join("C:", os.sep, "data")
    no_subdir = MeasurementIndex.resolve_path(entries["DataServer_C_2024.sqlite"], base)
    with_subdir = MeasurementIndex.resolve_path(entries["DataServer_B_2023.sqlite"], base)
    assert no_subdir == os.path.join(base, "DataServer_C_2024.sqlite")
    assert with_subdir == os.path.join(base, "UCM\\CompackStat", "DataServer_B_2023.sqlite")


def test_open_measurement_returns_reader(index_path):
    with MeasurementIndex(index_path) as index:
        entry = index.entries(technique="CycliScan")[0]
        reader = index.open_measurement(entry, base_dir="/tmp/data")
    assert isinstance(reader, MeasurementReader)


def test_entries_require_open(index_path):
    with pytest.raises(RuntimeError):
        MeasurementIndex(index_path).entries()
