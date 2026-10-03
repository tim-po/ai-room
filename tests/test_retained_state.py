"""Migration release gate must fail closed, including under python -O."""
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_retained_state.py'
spec = importlib.util.spec_from_file_location('retained_state', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def database(path, values):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE retained (value TEXT)')
        db.executemany('INSERT INTO retained VALUES (?)', [(v,) for v in values])
    return path


def test_additive_rows_columns_and_uri_characters(tmp_path):
    before = database(tmp_path / 'before?#.db', ['private', 'private'])
    after = database(tmp_path / 'after?#.db', ['private', 'private', 'new'])
    with sqlite3.connect(after) as db:
        db.execute('ALTER TABLE retained ADD COLUMN extra TEXT')
    assert checker.verify(before, after) == {'retained': 2}


def test_duplicate_loss_rejected_without_row_disclosure(tmp_path):
    before = database(tmp_path / 'before.db', ['sensitive-row', 'sensitive-row'])
    after = database(tmp_path / 'after.db', ['sensitive-row'])
    with pytest.raises(ValueError, match='Changed or missing retained rows: retained') as error:
        checker.verify(before, after)
    assert 'sensitive-row' not in str(error.value)


def test_missing_media_directory_rejected(tmp_path):
    with pytest.raises(ValueError, match='existing directory'):
        checker.media(tmp_path / 'missing')


@pytest.mark.parametrize('failure', ['rows', 'media', 'foreign_keys'])
def test_optimized_cli_still_rejects_corruption(tmp_path, failure):
    before = database(tmp_path / 'before.db', ['retained'])
    after = database(tmp_path / 'after.db', [] if failure == 'rows' else ['retained'])
    if failure == 'foreign_keys':
        with sqlite3.connect(after) as db:
            db.execute('CREATE TABLE parents (id INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE children (parent INTEGER REFERENCES parents(id))')
            db.execute('INSERT INTO children VALUES (1)')
    old_media, new_media = tmp_path / 'old-media', tmp_path / 'new-media'
    old_media.mkdir(); new_media.mkdir()
    (old_media / 'clip.webm').write_bytes(b'original')
    (new_media / 'clip.webm').write_bytes(b'changed' if failure == 'media' else b'original')
    result = subprocess.run([sys.executable, '-O', str(SCRIPT), str(before), str(after),
                             '--before-media', str(old_media), '--after-media', str(new_media)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert '"integrity": "ok"' not in result.stdout
    assert 'ValueError' in result.stderr
