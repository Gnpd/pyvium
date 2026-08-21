'''Tests for the measurement SQLite reader.

A tiny DatabaseVersion-9 file is synthesised in a tmp dir from the known schema,
so no real measurement data is committed and no hardware is needed.'''
# Tests are self-describing and use pytest fixtures (redefined-outer-name).
# pylint: disable=missing-function-docstring,redefined-outer-name

import sqlite3

import pytest

from pyvium.tools import (MeasurementReader, UnsupportedDatabaseVersionError,
                          decode_status)

_DDL = """
CREATE TABLE metadata (key TEXT, value TEXT);
CREATE TABLE measurement (measurement_id INTEGER PRIMARY KEY, start_time TEXT,
    end_time TEXT, mt BLOB);
CREATE TABLE method (measurement_id INTEGER, k TEXT, v TEXT);
CREATE TABLE measurementpart (measurementpart_id INTEGER PRIMARY KEY,
    measurement_id INTEGER, cycle INTEGER, level INTEGER, tstep INTEGER,
    muxchannel INTEGER, wexchannel INTEGER, measvalue REAL);
CREATE TABLE point (point_id INTEGER PRIMARY KEY, measurementpart_id INTEGER,
    t REAL, x REAL, y REAL, z REAL, q REAL, statusbyte INTEGER);
CREATE TABLE pointfra (point_id INTEGER, f REAL, z1 REAL, z2 REAL, ohr REAL,
    fraquality REAL);
CREATE TABLE point_small (point_id INTEGER PRIMARY KEY, measurement_id INTEGER,
    reason INTEGER);
"""

# statusbyte 131076 = bit2 (iovl) set + current-range index 2 in bits 16..23.
_IOVL_CR2 = (2 << 16) | 4
_CR2 = 2 << 16


def _build(path, db_version="9"):
    con = sqlite3.connect(path)
    con.executescript(_DDL)
    con.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("DatabaseVersion", db_version), ("SoftwareVersion", "4.1153"),
        ("DeviceAlias", "Oc-0-3")])
    con.execute("INSERT INTO measurement VALUES (1, '2024-10-08 09:55:09', "
                "'2024-10-08 11:06:22', NULL)")
    con.executemany("INSERT INTO method VALUES (1, ?, ?)",
                    [("Title", "MyScan"), ("Technique", "CycliScan")])
    con.executemany("INSERT INTO measurementpart VALUES (?,?,?,?,?,?,?,?)", [
        (1, 1, 1, 1, 0, 0, 1, 0.0),
        (2, 1, 1, 2, 3, 0, 1, 1.5)])
    con.executemany("INSERT INTO point VALUES (?,?,?,?,?,?,?,?)", [
        (1, 1, 0.2, 0.2, -2.4e-5, -0.113, 0.0, _CR2),
        (2, 1, 0.4, 0.4, -2.4e-5, -0.113, 0.0, _CR2),
        (3, 2, 0.6, 0.6, -0.2, -0.45, -0.04, _IOVL_CR2),
        (4, 2, 0.8, 0.8, -0.2, -0.55, -0.05, _CR2),
        (5, 2, 1.0, 1.0, -0.2, -0.65, -0.06, _CR2)])
    con.executemany("INSERT INTO pointfra VALUES (?,?,?,?,?,?)", [
        (4, 10.0, 1.12, -1.49, 0.00085, 0.999),
        (5, 11.7, 0.45, -0.025, 0.00095, 0.999)])
    # Curated whole-run subset: points 1 (part 1), 3 and 5 (part 2).
    con.executemany("INSERT INTO point_small VALUES (?,?,?)", [
        (1, 1, 0), (3, 1, 1), (5, 1, 2)])
    con.commit()
    con.close()
    return path


@pytest.fixture
def db_path(tmp_path):
    return _build(str(tmp_path / "measurement_v9.sqlite"))


def test_metadata_and_version(db_path):
    with MeasurementReader(db_path) as reader:
        assert reader.database_version == 9
        meta = reader.metadata()
    assert meta["DatabaseVersion"] == "9"
    assert meta["DeviceAlias"] == "Oc-0-3"


def test_measurements_and_method(db_path):
    with MeasurementReader(db_path) as reader:
        measurements = reader.measurements()
        method = reader.method_parameters()
    assert [m.measurement_id for m in measurements] == [1]
    assert measurements[0].start_time == "2024-10-08 09:55:09"
    assert method == {"Title": "MyScan", "Technique": "CycliScan"}


def test_measurement_parts(db_path):
    with MeasurementReader(db_path) as reader:
        parts = reader.measurement_parts()
    assert [p.measurementpart_id for p in parts] == [1, 2]
    assert (parts[0].cycle, parts[0].level, parts[0].wexchannel) == (1, 1, 1)
    assert parts[1].level == 2


def test_read_points_joins_part_context_and_decodes_status(db_path):
    with MeasurementReader(db_path) as reader:
        points = reader.read_points()
    assert [p.point_id for p in points] == [1, 2, 3, 4, 5]
    assert points[0].cycle == 1 and points[0].level == 1 and points[0].wexchannel == 1
    assert points[2].level == 2                # point 3 is in part 2
    assert points[2].status["iovl"] is True    # statusbyte 131076 -> iovl set
    assert points[2].status["cr"] == 2
    assert points[0].status["iovl"] is False


def test_read_points_after_point_id_is_incremental(db_path):
    with MeasurementReader(db_path) as reader:
        newer = reader.read_points(after_point_id=3)
    assert [p.point_id for p in newer] == [4, 5]


def test_read_impedance(db_path):
    with MeasurementReader(db_path) as reader:
        eis = reader.read_impedance()
    assert [p.point_id for p in eis] == [4, 5]
    assert eis[0].frequency == 10.0
    assert eis[0].z_re == 1.12 and eis[0].z_im == -1.49


def test_read_points_scoped_to_a_part(db_path):
    # Part 2 holds points 3,4,5; scoping keeps a large cycliscan bounded.
    with MeasurementReader(db_path) as reader:
        part2 = reader.read_points(measurementpart_id=2)
        part1 = reader.read_points(measurementpart_id=1)
    assert [p.point_id for p in part2] == [3, 4, 5]
    assert [p.point_id for p in part1] == [1, 2]


def test_read_points_by_cycle(db_path):
    with MeasurementReader(db_path) as reader:
        cycle1 = reader.read_points(cycle=1)
        cycle9 = reader.read_points(cycle=9)  # no such cycle
    assert [p.point_id for p in cycle1] == [1, 2, 3, 4, 5]
    assert cycle9 == []


def test_read_points_limit_is_a_hard_cap(db_path):
    # limit truncates in SQL (first N in point_id order); combine with a cursor.
    with MeasurementReader(db_path) as reader:
        first_two = reader.read_points(limit=2)
        next_two = reader.read_points(after_point_id=2, limit=2)
    assert [p.point_id for p in first_two] == [1, 2]
    assert [p.point_id for p in next_two] == [3, 4]


def test_read_impedance_scoped_to_a_part(db_path):
    # Both FRA points (4,5) belong to part 2; part 1 has none.
    with MeasurementReader(db_path) as reader:
        part2 = reader.read_impedance(measurementpart_id=2)
        part1 = reader.read_impedance(measurementpart_id=1)
    assert [p.point_id for p in part2] == [4, 5]
    assert part1 == []


def test_part_summaries(db_path):
    with MeasurementReader(db_path) as reader:
        summaries = reader.part_summaries()
    assert [(s.measurementpart_id, s.point_count) for s in summaries] == [(1, 2), (2, 3)]
    assert summaries[0].level == 1 and summaries[1].level == 2
    # t-range spans the part's points (part 1: t 0.2..0.4).
    assert summaries[0].t_min == 0.2 and summaries[0].t_max == 0.4


def test_part_summaries_from_part_id_scopes_to_tail(db_path):
    # Inclusive bound: from_part_id=2 keeps part 2 (a live caller's current task
    # whose count is still growing), drops part 1.
    with MeasurementReader(db_path) as reader:
        tail = reader.part_summaries(from_part_id=2)
        whole = reader.part_summaries(from_part_id=1)
    assert [(s.measurementpart_id, s.point_count) for s in tail] == [(2, 3)]
    assert [s.measurementpart_id for s in whole] == [1, 2]


def test_has_overview_true_when_point_small_present(db_path):
    with MeasurementReader(db_path) as reader:
        assert reader.has_overview() is True


def test_read_overview_points_returns_curated_subset(db_path):
    # point_small curates points 1, 3, 5; overview joins full part context.
    with MeasurementReader(db_path) as reader:
        overview = reader.read_overview_points()
        newer = reader.read_overview_points(after_point_id=1)
        capped = reader.read_overview_points(limit=2)
        by_cycle = reader.read_overview_points(cycle=1)
    assert [p.point_id for p in overview] == [1, 3, 5]
    assert overview[1].measurementpart_id == 2 and overview[1].level == 2
    assert overview[0].wexchannel == 1        # part context joined through
    assert [p.point_id for p in newer] == [3, 5]   # after_point_id is exclusive
    assert [p.point_id for p in capped] == [1, 3]  # hard cap in point_id order
    assert [p.point_id for p in by_cycle] == [1, 3, 5]


def test_overview_absent_reports_false_and_raises(tmp_path):
    # A file without a point_small table: has_overview False, reads raise (a
    # missing curation index is not the same as an empty point set).
    path = str(tmp_path / "no_overview.sqlite")
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE metadata (key TEXT, value TEXT);
        CREATE TABLE measurement (measurement_id INTEGER PRIMARY KEY, start_time TEXT,
            end_time TEXT, mt BLOB);
        CREATE TABLE measurementpart (measurementpart_id INTEGER PRIMARY KEY,
            measurement_id INTEGER, cycle INTEGER, level INTEGER, tstep INTEGER,
            muxchannel INTEGER, wexchannel INTEGER, measvalue REAL);
        CREATE TABLE point (point_id INTEGER PRIMARY KEY, measurementpart_id INTEGER,
            t REAL, x REAL, y REAL, z REAL, q REAL, statusbyte INTEGER);
    """)
    con.execute("INSERT INTO metadata VALUES ('DatabaseVersion', '9')")
    con.execute("INSERT INTO measurement VALUES (1, NULL, NULL, NULL)")
    con.execute("INSERT INTO measurementpart VALUES (1, 1, 1, 1, 0, 0, 1, 0.0)")
    con.execute("INSERT INTO point VALUES (1, 1, 0.2, 0.2, -1e-5, -0.1, 0.0, 0)")
    con.commit()
    con.close()
    with MeasurementReader(path) as reader:
        assert reader.has_overview() is False
        with pytest.raises(UnsupportedDatabaseVersionError):
            reader.read_overview_points()


def test_latest_part_id(db_path):
    with MeasurementReader(db_path) as reader:
        assert reader.latest_part_id() == 2


def test_latest_point_id(db_path):
    with MeasurementReader(db_path) as reader:
        assert reader.latest_point_id() == 5


def test_read_impedance_without_pointfra_returns_empty(tmp_path):
    # Non-EIS techniques produce files with no pointfra table; read_impedance must
    # return [] rather than raising, so a caller need not know the technique first.
    path = str(tmp_path / "no_fra.sqlite")
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE metadata (key TEXT, value TEXT);
        CREATE TABLE measurement (measurement_id INTEGER PRIMARY KEY, start_time TEXT,
            end_time TEXT, mt BLOB);
        CREATE TABLE measurementpart (measurementpart_id INTEGER PRIMARY KEY,
            measurement_id INTEGER, cycle INTEGER, level INTEGER, tstep INTEGER,
            muxchannel INTEGER, wexchannel INTEGER, measvalue REAL);
        CREATE TABLE point (point_id INTEGER PRIMARY KEY, measurementpart_id INTEGER,
            t REAL, x REAL, y REAL, z REAL, q REAL, statusbyte INTEGER);
    """)
    con.execute("INSERT INTO metadata VALUES ('DatabaseVersion', '9')")
    con.execute("INSERT INTO measurement VALUES (1, NULL, NULL, NULL)")
    con.execute("INSERT INTO measurementpart VALUES (1, 1, 1, 1, 0, 0, 1, 0.0)")
    con.execute("INSERT INTO point VALUES (1, 1, 0.2, 0.2, -1e-5, -0.1, 0.0, 0)")
    con.commit()
    con.close()
    with MeasurementReader(path) as reader:
        assert reader.read_impedance() == []
        assert [p.point_id for p in reader.read_points()] == [1]


def test_to_csv(db_path, tmp_path):
    out = tmp_path / "points.csv"
    with MeasurementReader(db_path) as reader:
        reader.to_csv(str(out))
    lines = out.read_text(encoding="UTF-8").splitlines()
    assert lines[0].startswith("point_id,")
    assert len(lines) == 1 + 5  # header + 5 points


def test_old_version_raises(tmp_path):
    # below the verified minimum: older schemas may differ structurally.
    path = _build(str(tmp_path / "old.sqlite"), db_version="4")
    with pytest.raises(UnsupportedDatabaseVersionError):
        MeasurementReader(path).open()


def test_newer_version_warns_and_reads(tmp_path):
    # newer than the verified max: assumed additive-only, so read with a warning.
    path = _build(str(tmp_path / "future.sqlite"), db_version="999")
    with pytest.warns(UserWarning):
        with MeasurementReader(path) as reader:
            assert reader.database_version == 999
            assert [p.point_id for p in reader.read_points()] == [1, 2, 3, 4, 5]


def test_methods_require_open(db_path):
    reader = MeasurementReader(db_path)
    with pytest.raises(RuntimeError):
        reader.metadata()


def test_decode_status_bits():
    decoded = decode_status(_IOVL_CR2)
    assert decoded["iovl"] is True
    assert decoded["eovl"] is False
    assert decoded["cr"] == 2
    assert decode_status(0)["iovl"] is False


def test_reader_dataclasses_are_exported_from_the_package_root():
    # part_summaries() returns MeasurementPartSummary, so it belongs alongside
    # its sibling dataclasses at the top level.
    import pyvium  # pylint: disable=import-outside-toplevel

    for name in ("DataPoint", "ImpedancePoint", "IndexEntry", "MeasurementInfo",
                 "MeasurementPart", "MeasurementPartSummary"):
        assert hasattr(pyvium, name), f"pyvium.{name} is not exported"
