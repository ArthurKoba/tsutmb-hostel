#!/bin/bash

echo "Install Project with GitHub. Project directory - `pwd`"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

dir="$PWD/$(dirname "$0")"
if [[ ${dir: -2} = "/." ]] ; then
    dir=${dir::-2}
fi
echo "Project Directory: $dir"

service_filename="tsutmb-hostel.service"

service_content="[Unit]\n"
service_content+="Description=Hostel group and conversation service.\n"
service_content+="After=network-online.target\n"
service_content+="Wants=network-online.target\n\n"
service_content+="[Service]\n"
service_content+="WorkingDirectory=$dir/src\n"
service_content+="ExecStart=$dir/venv/bin/python app.py\n"
service_content+="Restart=always\n"
service_content+="RestartSec=10\n\n"
service_content+="[Install]\n"
service_content+="WantedBy=multi-user.target\n"

echo -e $service_content > $service_filename
echo "$service_filename created"

ln -s $PWD/$service_filename /etc/systemd/system

systemctl daemon-reload
systemctl enable $service_filename
systemctl start $service_filename