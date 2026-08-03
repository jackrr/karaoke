#!/bin/sh
set -e

# Bind-mounted /data arrives owned by whoever created it on the host, so take
# ownership before dropping to the unprivileged app user. Non-recursive: the
# app makes its own subdirectories, and chown -R on a full media volume would
# make every restart slow. Skipped entirely when the caller passed --user.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data
    chown app:app /data

    # DATABASE_PATH/STORAGE_DIR can point at separately mounted volumes (see
    # README's split-volume example) that arrive owned by whoever created
    # them on the host, not just /data.
    db_dir=$(dirname "${DATABASE_PATH:-/data/karaoke.db}")
    if [ "$db_dir" != "/data" ]; then
        mkdir -p "$db_dir"
        chown app:app "$db_dir"
    fi
    if [ -n "$STORAGE_DIR" ] && [ "$STORAGE_DIR" != "/data/storage" ]; then
        mkdir -p "$STORAGE_DIR"
        chown app:app "$STORAGE_DIR"
    fi

    exec setpriv --reuid=app --regid=app --init-groups "$@"
fi

exec "$@"
