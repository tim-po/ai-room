"""Additive tables that a module creates on first use, so deployments need no migration step."""
import sqlite3


def additive_tables(app, statements):
    """Returns ensure(): runs the CREATE ... IF NOT EXISTS statements once per process and database,
    on a connection of its own (never inside a request's transaction)."""
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
        finally:
            connection.close()
        ready.add(key)

    return ensure
