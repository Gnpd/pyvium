'''Shared helpers for reading IviumSoft measurement SQLite files.

IviumSoft stores each measurement in a DataServer_*.idf.sqlite file and keeps an
index.sqlite catalog of them. This module centralises the bits both readers need:
the supported DatabaseVersion set, a read-only WAL-safe connection helper, the
status-byte decoder, and the provisional per-technique column labels.
'''
import sqlite3
import warnings
from pathlib import Path

# DatabaseVersion (metadata table) values this reader is verified against. The
# tables the reader reads (point, pointdata, pointfra, metadata, measurement,
# method) are identical across versions 5-9; measurementpart only gained columns
# (muxchannel @6, wexchannel @7, measvalue @9), which the reader treats as
# optional. All five were verified against sample files. A version newer than the
# max is assumed to be more of the same (additive only): it is read with a
# warning. A version below the min is rejected, since we cannot assume the older
# schema is merely a column-subset.
SUPPORTED_DB_VERSIONS = frozenset({5, 6, 7, 8, 9})

# Read-only connections wait this long for the WAL writer instead of failing fast.
_BUSY_TIMEOUT_MS = 2000

# statusbyte bit layout, mirroring the point_expanded_status view shipped in the
# measurement files. Kept here so the reader does not depend on that view existing
# in every DatabaseVersion.
_STATUS_EOVL = 32
_STATUS_IOVL = 4
_STATUS_EXT = 16
_STATUS_FLAGS_MASK = 65280          # bits 8..15
_STATUS_CR_MASK = 16711680          # bits 16..23
_STATUS_BCR_MASK = 4278190080       # bits 24..31


class UnsupportedDatabaseVersionError(ValueError):
    '''Raised when a measurement file's DatabaseVersion is not supported.'''


def connect_readonly(db_path: str) -> sqlite3.Connection:
    '''Opens a measurement/index SQLite file read-only and WAL-safe.

        Uses URI mode=ro (never creates or writes the file or its -wal/-shm
        siblings) and a busy timeout so a query never blocks IviumSoft's writer.
        Callers must keep queries short and avoid long-lived transactions, so a
        read never delays a WAL checkpoint.'''
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=_BUSY_TIMEOUT_MS / 1000)
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    return connection


def read_database_version(connection: sqlite3.Connection) -> int:
    '''Returns the DatabaseVersion recorded in the metadata table.'''
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'DatabaseVersion'").fetchone()
    if row is None:
        raise UnsupportedDatabaseVersionError(
            "No DatabaseVersion in metadata; not an IviumSoft measurement file?")
    return int(row[0])


def verify_database_version(version: int) -> None:
    '''Checks a DatabaseVersion against the verified set.

        Verified versions pass silently. A version newer than the verified max
        is allowed with a UserWarning (newer versions have only added columns,
        which the reader tolerates), so reading keeps working without a code
        change. A version below the verified min raises
        UnsupportedDatabaseVersionError, since an older schema may differ in ways
        we cannot assume away.'''
    if version in SUPPORTED_DB_VERSIONS:
        return
    supported = ", ".join(str(v) for v in sorted(SUPPORTED_DB_VERSIONS))
    if version > max(SUPPORTED_DB_VERSIONS):
        warnings.warn(
            f"DatabaseVersion {version} is newer than the verified versions "
            f"({supported}); reading it on the assumption it only adds columns. "
            "Verify the results and add it to SUPPORTED_DB_VERSIONS once checked.",
            UserWarning, stacklevel=2)
        return
    raise UnsupportedDatabaseVersionError(
        f"DatabaseVersion {version} is not supported (verified: {supported}). "
        "Older schemas may differ structurally; capture a sample file to add support.")


def decode_status(statusbyte: int) -> dict:
    '''Decodes a point statusbyte into its flags, mirroring point_expanded_status.

        Returns eovl/iovl/ext (booleans), and flags/cr/bcr (integers): the
        E- and I-overload bits, the external bit, the status flags, and the
        current-range / bipotentiostat-current-range indices.'''
    statusbyte = int(statusbyte or 0)
    return {
        "eovl": bool(statusbyte & _STATUS_EOVL),
        "iovl": bool(statusbyte & _STATUS_IOVL),
        "ext": bool(statusbyte & _STATUS_EXT),
        "flags": (statusbyte & _STATUS_FLAGS_MASK) >> 8,
        "cr": (statusbyte & _STATUS_CR_MASK) >> 16,
        "bcr": (statusbyte & _STATUS_BCR_MASK) >> 24,
    }


# Generic meaning of the point table's x/y/z/q columns. The DLL exposes the same
# per-technique triplet through IV_getdata (d1/d2/d3) and the meaning depends on
# the technique; in the dbver-9 samples x is the control/time axis, y the current,
# z the potential and q the charge. This is PROVISIONAL and not yet confirmed
# per technique; raw columns are always available on DataPoint regardless of labels.
_DEFAULT_COLUMN_LABELS = {"x": "x", "y": "current", "z": "potential", "q": "charge"}

# Per-technique overrides, keyed by the index.sqlite "technique" string. Empty
# until confirmed against captured sample files.
_TECHNIQUE_COLUMN_LABELS: dict = {}


def column_labels(technique: str | None = None) -> dict:
    '''Best-effort names for the point table's x/y/z/q columns for a technique.

        Provisional: returns the generic mapping unless a confirmed override
        exists. Use DataPoint's raw x/y/z/q when the labelling matters.'''
    labels = dict(_DEFAULT_COLUMN_LABELS)
    if technique:
        labels.update(_TECHNIQUE_COLUMN_LABELS.get(technique, {}))
    return labels
