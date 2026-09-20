#!/usr/bin/env bash
set -e

echo "Configuring PostgreSQL 16..."
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/16/main/postgresql.conf
echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/16/main/pg_hba.conf
echo "host all all ::/0 trust" >> /etc/postgresql/16/main/pg_hba.conf

service postgresql restart

echo "Creating databases and extensions..."
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\""
su - postgres -c "psql -c \"CREATE DATABASE historical_archive;\"" || true
su - postgres -c "psql -c \"CREATE DATABASE archive_db;\"" || true
su - postgres -c "psql -d historical_archive -c \"CREATE EXTENSION IF NOT EXISTS vector;\""
su - postgres -c "psql -d archive_db -c \"CREATE EXTENSION IF NOT EXISTS vector;\""

echo "PostgreSQL setup complete!"
