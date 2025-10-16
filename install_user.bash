#!/bin/bash
apt-get install python3 python3-pip python3-venv curl wget build-essential libssl-dev libffi-dev python3-dev net-tools sqlite3 -y
pip3 install -r requirements.txt
python3 bot_main.py
