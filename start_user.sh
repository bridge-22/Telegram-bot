#!/bin/bash
source .env
echo "$CLONE_PATH"
cd $CLONE_PATH
cd Telegram-bot/
tmux new-session -d -s myscripts 'python3 bot_main.py'
tmux new-window -t myscripts 'python3 admin_panel.py'
echo "To show scripts console: tmux attach -t myscripts"
echo "Switch between scripts: Ctrl+b n (next window) / Ctrl+b p (previous window)"
echo "See list of windows: Ctrl+b w"
echo "Go back to background: Ctrl+b d (detach - scripts keep running)"
sleep 5
tmux list-sessions

