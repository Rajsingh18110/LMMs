#!/bin/bash
echo "=== SUMMARIZING TASK ==="
python3.11 test_cli.py task summarize

echo "=== SQLITE TASK MEMORY QUERY ==="
DB_PATH=$(ls ~/.lmms/workspaces/*/database.sqlite | head -n 1)
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" -header -column "SELECT * FROM task_memory;"
else
    echo "No DB found."
fi
