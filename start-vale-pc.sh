#!/bin/sh
python3 ~/vale/splash/vale-splash.py
~/vale/build/wm/vwin &
WM_PID=$!
sleep 1
python3 ~/vale/wallpaper/vpaper.py &
python3 ~/vale/panel/vale-panel.py &
wait $WM_PID
