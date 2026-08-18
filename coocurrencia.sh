#!/usr/bin/env bash
#
# Genera el dashboard de co-ocurrencia y lo deja en la carpeta de datos.
#
#   ./coocurrencia.sh          # genera y abre
#   ./coocurrencia.sh --no-abrir
#
# El HTML queda en <datos>/visualizaciones/coocurrencia_programas.html
# — en Drive, así que
# sobrevive a apagar la máquina y se sincroniza solo.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
VIZ="$DATOS/visualizaciones"
mkdir -p "$VIZ"
SALIDA="$VIZ/coocurrencia_programas.html"

PYTHONPATH="$REPO" python3 -u "$REPO/coocurrencia.py" \
    --maestras "$DATOS/maestras" --salida "$SALIDA" || exit $?

if [ "$ABRIR" -eq 1 ] && command -v open >/dev/null 2>&1; then
    open "$SALIDA"
fi
