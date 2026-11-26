#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export DATABASE_URL=postgresql+psycopg://tfa:tfa@localhost:5432/tfa
alembic upgrade head
alembic revision --autogenerate -m "${1:-migration}"
