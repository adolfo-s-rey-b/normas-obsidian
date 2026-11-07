#!/usr/bin/env bash
# Sirve el repositorio en http://127.0.0.1:8765 para que el plugin lea catalogo/ localmente.
cd "$(dirname "$0")/.." && exec python3 -m http.server 8765 --bind 127.0.0.1
