#!/bin/bash

# Get the JSON data from config
CONFIG_DATA=$(sqlite3 data/webui.db "SELECT data FROM config ORDER BY id DESC LIMIT 1;")

# Replace "enable_signup": false with "enable_signup": true using sed
UPDATED_DATA=$(echo "$CONFIG_DATA" | sed 's/"enable_signup": false/"enable_signup": true/g')

# Update the database
sqlite3 data/webui.db "UPDATE config SET data='$UPDATED_DATA' WHERE id=(SELECT id FROM config ORDER BY id DESC LIMIT 1);"

echo "User signups have been enabled successfully!" 