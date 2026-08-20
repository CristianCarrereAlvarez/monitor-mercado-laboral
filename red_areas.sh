#!/usr/bin/env bash
#
# Genera el gráfico de relación entre áreas y lo deja con las demás
# visualizaciones.
#
#   ./red_areas.sh          # genera y abre
#   ./red_areas.sh --no-abrir
#
# Queda en <datos>/visualizaciones/red_areas.html.
#
# Lee aviso_programa.csv, así que necesita la homologación puesta y una
# consolidación hecha: si falta, dice qué correr.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
VIZ="$DATOS/visualizaciones"
mkdir -p "$VIZ"
SALIDA="$VIZ/red_areas.html"

PYTHONPATH="$REPO" python3 -u "$REPO/red_areas.py" \
    --maestras "$DATOS/maestras" --salida "$SALIDA" || exit $?

if [ "$ABRIR" -eq 1 ] && command -v open >/dev/null 2>&1; then
    open "$SALIDA"
fi
