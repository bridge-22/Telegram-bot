#!/bin/bash
apt-get install gcc python3-devel make libsqlite3-devel git -y 
apt-get install python3 python3-module-pip python3-venv curl wget build-essential libssl-dev libffi-dev python3-dev net-tools sqlite3 -y
apt-get install python3-module-pip -y
apt-get install tmux -y 
pip3 install -r requirements.txt
cd
git clone https://github.com/bridge-22/Telegram-bot.git
cd Telegram-bot/
read -p "Write your telegram-bot token: " token_raw
token = f"$token_raw"
echo "TELEGRAM_BOT=$token > .env
tmux new-session -d -s myscripts 'python3 bot_main.py'
tmux new-window -t myscripts 'python3 admin_panel.py'
echo "To show scripts console: tmux attach -t myscripts"
echo "Switch between scripts: Ctrl+b n (next window) / Ctrl+b p (previous window)"
echo "See list of windows: Ctrl+b w"
echo "Go back to background: Ctrl+b d (detach - scripts keep running)"
sleep 5
tmux list-sessions
