#!/usr/bin/env bash
#
# Análisis estadístico del agrupamiento de programas.
#
#   ./agrupar.sh          # analiza, imprime el informe y abre la página
#   ./agrupar.sh --no-abrir
#
# Queda en <datos>/visualizaciones/agrupamiento.html.
#
# Lee aviso_programa.csv y avisos.csv: necesita la homologación puesta y
# una consolidación hecha.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
VIZ="$DATOS/visualizaciones"
mkdir -p "$VIZ"
SALIDA="$VIZ/agrupamiento.html"

PYTHONPATH="$REPO" python3 -u "$REPO/agrupar.py" \
    --maestras "$DATOS/maestras" --salida "$SALIDA" || exit $?

if [ "$ABRIR" -eq 1 ] && command -v open >/dev/null 2>&1; then
    open "$SALIDA"
fi
