#!/usr/bin/env bash
#
# Captura un área parado SIEMPRE en la carpeta de datos.
#
# El error que este script elimina: scraper_v9.py escribe en `crudo/`
# relativo al directorio actual. Corrido desde el clon del repo, el JSONL
# aterriza ahí en vez de en Drive — en Colab encima es efímero y se
# pierde sin que nada avise. Estaba documentado en tres lugares y volvió
# a pasar igual, así que mejor hacerlo imposible que seguir recordándolo.
#
# Uso:
#   ./capturar.sh "Agropecuaria"
#   ./capturar.sh "Salud" --sin-navegador
#
# La carpeta de datos se resuelve sola. Para forzarla:
#   MML_DATOS="/ruta/a/monitor_mercado_laboral" ./capturar.sh "Salud"
#
# Códigos de salida: los de scraper_v9.py (2 = rechazo del sitio,
# 3 = captura cortada a mitad), o 1 si falla la resolución de rutas.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

msg()   { printf '  %s\n' "$*"; }
fatal() { printf '\n  ⛔  %s\n\n' "$*" >&2; exit 1; }

if [ $# -lt 1 ]; then
    cat >&2 <<FIN

  Uso: $(basename "$0") "<Área>" [opciones de scraper_v9.py]
       $(basename "$0") --donde      # imprime la carpeta de datos

  Áreas disponibles:
FIN
    PYTHONPATH="$REPO" python3 - <<'PY' >&2
from carreras_sies_2026 import CARRERAS_POR_AREA
for a, c in CARRERAS_POR_AREA.items():
    print(f"    {len(c):3d} términos  {a}")
PY
    echo >&2
    exit 1
fi

SOLO_RUTA=0
if [ "$1" = "--donde" ]; then
    SOLO_RUTA=1; AREA="(consulta)"; shift
else
    AREA="$1"; shift
fi

# ── 1. Resolver la carpeta de datos ───────────────────────────────
CANDIDATOS=()
if [ -n "${MML_DATOS:-}" ]; then
    CANDIDATOS+=("$MML_DATOS")
else
    for BASE in "$HOME"/Library/CloudStorage/GoogleDrive-* "$HOME/Google Drive"; do
        [ -d "$BASE" ] || continue
        for UNIDAD in "Mi unidad" "My Drive" "."; do
            RUTA="$BASE/$UNIDAD/monitor_mercado_laboral"
            [ -d "$RUTA" ] && CANDIDATOS+=("$RUTA")
        done
    done
    [ -d /content/drive/MyDrive/monitor_mercado_laboral ] \
        && CANDIDATOS+=(/content/drive/MyDrive/monitor_mercado_laboral)
fi

if [ "${#CANDIDATOS[@]}" -eq 0 ]; then
    fatal "No encontré la carpeta de datos.

  Busqué en Google Drive (escritorio) y en Colab. Si está en otro lado,
  indicámela:

      MML_DATOS=\"/ruta/a/monitor_mercado_laboral\" $(basename "$0") \"$AREA\"

  Tiene que ser la carpeta que contiene crudo/ y maestras/."
fi

# Deduplicar por ruta canónica: "." puede duplicar un match.
DATOS=""
VISTAS=""
for C in "${CANDIDATOS[@]}"; do
    REAL="$(cd "$C" 2>/dev/null && pwd -P)" || continue
    case "$VISTAS" in *"[$REAL]"*) continue ;; esac
    VISTAS="$VISTAS[$REAL]"
    [ -z "$DATOS" ] && DATOS="$REAL"
done

N_UNICAS="$(printf '%s' "$VISTAS" | tr -cd '[' | wc -c | tr -d ' ')"
if [ "$N_UNICAS" -gt 1 ]; then
    fatal "Encontré $N_UNICAS carpetas de datos y no sé cuál usar:

$(printf '%s' "$VISTAS" | tr ']' '\n' | tr -d '[' | sed 's/^/      /')

  Elegí una:
      MML_DATOS=\"<la que corresponda>\" $(basename "$0") \"$AREA\""
fi

[ -w "$DATOS" ] || fatal "La carpeta de datos no es escribible: $DATOS"
mkdir -p "$DATOS/crudo"

if [ "$SOLO_RUTA" -eq 1 ]; then
    printf '%s\n' "$DATOS"
    exit 0
fi

# ── 2. ¿Hay Chromium para Playwright? ─────────────────────────────
# Si no, se usa el modo directo. Playwright 1.62 no soporta Chromium en
# macOS 12, y ahí instalarlo no es una opción.
EXTRA=""
case " $* " in
    *" --sin-navegador "*) ;;
    *)
        if ! python3 - <<'PY' >/dev/null 2>&1
import os, sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)
PY
        then
            EXTRA="--sin-navegador"
        fi
        ;;
esac

# ── 3. Correr ─────────────────────────────────────────────────────
msg ""
msg "repo   : $REPO"
msg "datos  : $DATOS"
msg "área   : $AREA"
[ -n "$EXTRA" ] && msg "sesión : directo (Chromium no disponible para Playwright)"
msg ""

cd "$DATOS"
exec env PYTHONPATH="$REPO" python3 -u "$REPO/scraper_v9.py" "$AREA" ${EXTRA:+$EXTRA} "$@"
