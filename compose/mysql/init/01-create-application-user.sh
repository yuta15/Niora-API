# This file is sourced by the official MySQL entrypoint during initial database setup.

if [[ ! ${MYSQL_DATABASE:-} =~ ^[A-Za-z0-9_]+$ ]]; then
    echo >&2 "MYSQL_DATABASE must contain only ASCII letters, digits, and underscores"
    return 1
fi

if [[ ! ${NIORA_DATABASE_APPLICATION_USER:-} =~ ^[A-Za-z0-9_]+$ ]]; then
    echo >&2 "NIORA_DATABASE_APPLICATION_USER must contain only ASCII letters, digits, and underscores"
    return 1
fi

if [[ -z ${NIORA_DATABASE_APPLICATION_PASSWORD:-} ]]; then
    echo >&2 "NIORA_DATABASE_APPLICATION_PASSWORD must not be empty"
    return 1
fi

application_password=${NIORA_DATABASE_APPLICATION_PASSWORD//\\/\\\\}
application_password=${application_password//\'/\'\'}

docker_process_sql --database="$MYSQL_DATABASE" <<EOSQL
CREATE USER '${NIORA_DATABASE_APPLICATION_USER}'@'%' IDENTIFIED BY '${application_password}';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${MYSQL_DATABASE}\`.* TO '${NIORA_DATABASE_APPLICATION_USER}'@'%';
EOSQL

unset application_password
