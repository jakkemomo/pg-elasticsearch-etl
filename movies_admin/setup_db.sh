#!/bin/sh
cd /usr/src/schema_design
python schema.py
cd /usr/src/sqlite_to_postgres
python load_data.py
