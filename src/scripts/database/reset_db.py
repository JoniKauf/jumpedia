from database import queries
from utils import devtools

# devtools.time_left(feedback=lambda s: f"U SURE??? {s} seconds left!!!")

with queries.connected(None) as (conn, cursor):
    for db in queries.get_database_names(True):
        cursor.execute(f"DROP DATABASE `{db}`")

    cursor.execute(f"CREATE DATABASE `{queries.META_DATABASE_NAME}`")

with queries.connected(queries.MetaDatabase) as (conn, cursor):
    cursor.execute(
        """
        CREATE TABLE community (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) UNIQUE,
            display_name VARCHAR(50) UNIQUE,
            database_name VARCHAR(50) UNIQUE         
        )
    """
    )
