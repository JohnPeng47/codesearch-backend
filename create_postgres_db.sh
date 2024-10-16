#!/bin/bash

# Check if all required arguments are provided
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <DB_USER> <DB_PASS> <DB_NAME> [REMOTE_IP]"
    exit 1
fi

DB_USER="$1"
DB_PASS="$2"
DB_NAME="$3"

echo "Setting up PostgreSQL..."
if [ "$DB_USER" != "postgres" ]; then
    echo "Creating new user: $DB_USER"
    psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
else
    echo "Updating password for existing postgres user"
    psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$DB_PASS';"
fi

echo "Creating database: $DB_NAME"
psql -U postgres -c "CREATE DATABASE $DB_NAME;"

echo "Granting privileges on $DB_NAME to $DB_USER"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "Updating pg_hba.conf to allow password authentication for local connections..."
echo "host    $DB_NAME    $DB_USER    127.0.0.1/32    md5" >> /etc/postgresql/*/main/pg_hba.conf

echo "Restarting PostgreSQL to apply changes..."
systemctl restart postgresql

echo "PostgreSQL setup completed successfully!"
echo "You can now connect using the following SQLAlchemy URI:"
echo "SQLALCHEMY_DATABASE_URI = \"postgresql://$DB_USER:$DB_PASS@127.0.0.1:5433/$DB_NAME\""
