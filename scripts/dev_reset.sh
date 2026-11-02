#!/usr/bin/env sh
# DEV ONLY: erases the database and loads the sample data set (keeps the admin account).
exec docker compose exec -T api python -m app.devdata.reset --yes
