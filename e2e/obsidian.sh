#!/usr/bin/env bash
# Ejecuta Obsidian (app o CLI) contra el entorno E2E aislado.
#   e2e/obsidian.sh            → abre la app con la configuración aislada
#   e2e/obsidian.sh <comando>  → CLI de Obsidian (p. ej. «files», «dev:screenshot path=…»)
# ELECTRON_RUN_AS_NODE (lo exporta VS Code) hace que Electron arranque como Node
# puro y el CLI falle; por eso se elimina siempre.
E2E=${E2E_DIR:-/tmp/normas-e2e}
exec env -u ELECTRON_RUN_AS_NODE XDG_CONFIG_HOME="$E2E/xdg" obsidian "$@"
