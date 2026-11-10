"""Connection helpers for this project; GUI connections must enable their own FKs."""
import sqlite3
from pathlib import Path


def connect(path, *, readonly=False, create=False):
    if sqlite3.sqlite_version_info < (3, 31, 0):
        raise RuntimeError('SQLite 3.31+ is required for generated-column constraints')
    mode = 'ro' if readonly else 'rwc' if create else 'rw'
    con = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=' + mode, uri=True)
    con.execute('PRAGMA foreign_keys=ON')
    if con.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        con.close()
        raise RuntimeError('Foreign-key enforcement could not be enabled')
    return con
