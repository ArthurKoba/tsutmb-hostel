#!/bin/bash

echo "Updating Project with GitHub. Project directory - `pwd`"
source venv/bin/activate
git pull origin main
systemctl restart gunicorn.service
