"""Additive tables that a module creates on first use, so deployments need no migration step."""
import sqlite3


def additive_tables(app, statements, columns=()):
    """Returns ensure(): runs the CREATE ... IF NOT EXISTS statements once per process and database,
    on a connection of its own (never inside a request's transaction). `columns` are (table, column,
    definition) triples added with ALTER TABLE when missing, after the tables exist."""
    ready = set()

    def ensure():
        key = app.config['DATABASE']
        if key in ready:
            return
        connection = sqlite3.connect(key, timeout=10)
        try:
            with connection:
                for statement in statements:
                    connection.execute(statement)
                for table, column, definition in columns:
                    if column not in {r[1] for r in connection.execute(f'PRAGMA table_info({table})')}:
                        connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
        finally:
            connection.close()
        ready.add(key)

    return ensure
