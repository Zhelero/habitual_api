#!/bin/sh
set -e

if [ "$1" = "pytest" ] || [ "$1" = "uvicorn" ]; then
  echo "Waiting for postgres..."

  until pg_isready -h db -p 5432 -U habitual
  do
    sleep 1
  done

  echo "Running migrations..."
  alembic upgrade head
fi

echo "Starting: $@"
exec "$@"