#!/usr/bin/env bash
# Alternative to Docker: set up the same database on a locally installed PostgreSQL 16
# (Ubuntu/Debian: sudo apt install postgresql postgresql-16-pgvector).
set -euo pipefail
sudo -u postgres psql <<SQL
CREATE USER persona WITH PASSWORD 'persona';
CREATE DATABASE persona_platform OWNER persona;
CREATE DATABASE persona_platform_test OWNER persona;
SQL
for db in persona_platform persona_platform_test; do
  sudo -u postgres psql -d "$db" -c 'CREATE EXTENSION IF NOT EXISTS vector;'
done
echo "Done. Now run: alembic upgrade head"
