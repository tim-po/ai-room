"""Read-only preservation check for additive staging migrations; emits no row data."""
import argparse
from collections import Counter
import hashlib
import json
import sqlite3
from pathlib import Path


def verify(before, after):
    report = {}
    with sqlite3.connect(Path(before).resolve().as_uri() + '?mode=ro', uri=True) as old, sqlite3.connect(Path(after).resolve().as_uri() + '?mode=ro', uri=True) as new:
        if new.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Migrated database integrity check failed')
        if new.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Migrated database has foreign key violations')
        tables = old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        for (table,) in tables:
            # Names originate in SQLite metadata, still quote them as identifiers.
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [row[1] for row in old.execute(f'PRAGMA table_info({quoted})')]
            selection = ','.join('"' + name.replace('"', '""') + '"' for name in columns)
            previous = old.execute(f'SELECT {selection} FROM {quoted}').fetchall()
            current = Counter(new.execute(f'SELECT {selection} FROM {quoted}').fetchall())
            if Counter(previous) - current:
                raise ValueError(f'Changed or missing retained rows: {table}')
            report[table] = len(previous)
    return report


def media(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError('Media checkpoint must be an existing directory')
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--before-media', type=Path, required=True)
    parser.add_argument('--after-media', type=Path, required=True)
    args = parser.parse_args()
    rows = verify(args.before.resolve(), args.after.resolve())
    old_media, new_media = media(args.before_media), media(args.after_media)
    if any(new_media.get(name) != value for name, value in old_media.items()):
        raise ValueError('Retained media changed')
    print(json.dumps(dict(preserved_rows=rows, preserved_media_files=len(old_media), integrity='ok')))
