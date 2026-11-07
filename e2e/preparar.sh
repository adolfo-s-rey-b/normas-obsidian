#!/usr/bin/env bash
# Prepara un entorno E2E aislado para probar el plugin en Obsidian real.
#
#   E2E_DIR       carpeta de trabajo (por defecto /tmp/normas-e2e); se borra y se recrea
#   VAULT_ORIGEN  (opcional) vault personal del que se COPIAN notas de ejemplo
#                 (carpeta NOTAS_ORIGEN), app.json, appearance.json, el tema y Dataview.
#                 El vault de origen solo se lee.
#   NOTAS_ORIGEN  carpeta del vault de origen a copiar (por defecto «Derecho»)
#   URL_CATALOGO  catálogo para el plugin (por defecto el servidor local de servir.sh)
#
# Crea:
#   $E2E_DIR/vault   vault de pruebas con el plugin compilado
#   $E2E_DIR/xdg     XDG_CONFIG_HOME aislado (obsidian.json solo con ese vault y cli=true),
#                    para que Obsidian no abra ni modifique la configuración real.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
E2E=${E2E_DIR:-/tmp/normas-e2e}
NOTAS=${NOTAS_ORIGEN:-Derecho}
URL=${URL_CATALOGO:-http://127.0.0.1:8765/catalogo}
VAULT="$E2E/vault"
PLUG="$VAULT/.obsidian/plugins/normas-colombianas"

rm -rf "$E2E"
mkdir -p "$PLUG" "$E2E/xdg/obsidian" "$E2E/capturas"

if [ -n "${VAULT_ORIGEN:-}" ]; then
  cp -r "$VAULT_ORIGEN/$NOTAS" "$VAULT/$NOTAS"
  for f in app.json appearance.json; do
    [ -f "$VAULT_ORIGEN/.obsidian/$f" ] && cp "$VAULT_ORIGEN/.obsidian/$f" "$VAULT/.obsidian/"
  done
  tema=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('cssTheme',''))" \
         "$VAULT_ORIGEN/.obsidian/appearance.json" 2>/dev/null || true)
  if [ -n "$tema" ] && [ -d "$VAULT_ORIGEN/.obsidian/themes/$tema" ]; then
    mkdir -p "$VAULT/.obsidian/themes" && cp -r "$VAULT_ORIGEN/.obsidian/themes/$tema" "$VAULT/.obsidian/themes/"
  fi
  if [ -d "$VAULT_ORIGEN/.obsidian/plugins/dataview" ]; then
    mkdir -p "$VAULT/.obsidian/plugins/dataview"
    cp "$VAULT_ORIGEN/.obsidian/plugins/dataview/"{main.js,manifest.json,styles.css} "$VAULT/.obsidian/plugins/dataview/" 2>/dev/null || true
  fi
fi

(cd "$REPO/plugin-obsidian" && npm run build --silent >/dev/null)
cp "$REPO/plugin-obsidian/main.js" "$REPO/manifest.json" "$PLUG/"
printf '{"destino":"Normas","urlBase":"%s"}\n' "$URL" > "$PLUG/data.json"

plugins='["normas-colombianas"]'
[ -d "$VAULT/.obsidian/plugins/dataview" ] && plugins='["dataview","normas-colombianas"]'
echo "$plugins" > "$VAULT/.obsidian/community-plugins.json"

cat > "$E2E/xdg/obsidian/obsidian.json" <<JSON
{"vaults":{"e2e0000000000001":{"path":"$VAULT","ts":$(date +%s)000,"open":true}},"cli":true}
JSON
echo "Entorno E2E listo en $E2E (vault: $VAULT, catálogo: $URL)"
