-- Runs automatically by the postgres image on first container start
-- (only when the data directory is empty). Creates a separate database
-- for the test suite so `Base.metadata.drop_all()` in tests/conftest.py
-- never touches the dev database that shares the same Postgres server.
CREATE DATABASE habitual_test OWNER habitual;