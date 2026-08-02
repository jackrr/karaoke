#!/bin/sh
set -e

# Bind-mounted /data arrives owned by whoever created it on the host, so take
# ownership before dropping to the unprivileged app user. Non-recursive: the
# app makes its own subdirectories, and chown -R on a full media volume would
# make every restart slow. Skipped entirely when the caller passed --user.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data
    chown app:app /data
    exec setpriv --reuid=app --regid=app --init-groups "$@"
fi

exec "$@"
