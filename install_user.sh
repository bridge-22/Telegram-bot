#!/bin/bash
apt-get install -y gcc python3-devel make libsqlite3-devel
apt-get install python3 python3-module-pip python3-venv curl wget build-essential libssl-dev libffi-dev python3-dev net-tools sqlite3 -y
pip3 install -r requirements.txt
python3 bot_main.py
