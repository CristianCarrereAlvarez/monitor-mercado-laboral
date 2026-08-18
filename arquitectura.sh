#!/usr/bin/env bash
#
# Genera el mapa de archivos del proyecto y lo deja con las demás
# visualizaciones.
#
#   ./arquitectura.sh          # genera y abre
#   ./arquitectura.sh --no-abrir
#
# Queda en <datos>/visualizaciones/arquitectura.html.
#
# No lee datos: sale entero de la declaración que está en
# arquitectura.py. Hay que regenerarlo cuando se agrega un archivo al
# proyecto, no cuando llegan avisos nuevos.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
VIZ="$DATOS/visualizaciones"
mkdir -p "$VIZ"
SALIDA="$VIZ/arquitectura.html"

PYTHONPATH="$REPO" python3 -u "$REPO/arquitectura.py" --salida "$SALIDA" || exit $?

if [ "$ABRIR" -eq 1 ] && command -v open >/dev/null 2>&1; then
    open "$SALIDA"
fi
