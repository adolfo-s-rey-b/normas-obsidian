#!/usr/bin/env bash
# Imprime la geometría «x,y AxB» (formato de grim -g) de la primera ventana de
# Hyprland cuyo título empieza por $1. Sirve para capturar ventanas que el CLI de
# Obsidian no ve (p. ej. Preferencias, que en Obsidian 1.15 es una ventana aparte).
hyprctl clients -j | python3 -c '
import json, sys
pref = sys.argv[1]
for c in json.load(sys.stdin):
    if c["title"].startswith(pref):
        x, y = c["at"]; w, h = c["size"]
        print(f"{x},{y} {w}x{h}")
        break
' "$1"
