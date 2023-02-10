#!/bin/bash

service_filename="tsutmb-hostel.service"

echo "Updating Project (`service_filename`) with GitHub. Project directory - `pwd`"
source venv/bin/activate
git pull origin master
systemctl restart service_filename
