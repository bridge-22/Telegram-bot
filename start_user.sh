#!/bin/bash
path_to_bot="Telegram-bot"

while [[ ! -d $path_to_bot ]]; do
 echo "Folder doesn't exists, write a path to it, or use git clone https://github.com/bridge-22/Telegram-bot"
 read -p "path_to_bot=" path_to_bot
done

echo "path_to_bot=$path_to_bot"
cd $path_to_bot
pwd

tmux new-session -d -s myscripts 'python3 bot_main.py'
tmux new-window -t myscripts 'python3 admin_panel.py'
echo "To show scripts console: tmux attach -t myscripts"
echo "Switch between scripts: Ctrl+b n (next window) / Ctrl+b p (previous window)"
echo "See list of windows: Ctrl+b w"
echo "Go back to background: Ctrl+b d (detach - scripts keep running)"
sleep 5
tmux list-sessions
