#!/usr/bin/env bash
#
# Genera la referencia de variables y la deja en la carpeta de datos.
#
#   ./variables.sh          # genera y abre
#   ./variables.sh --no-abrir
#
# El HTML queda en <datos>/visualizaciones/variables_maestras.html
# — en Drive, así que
# sobrevive a apagar la máquina y se sincroniza solo.
#
# No lee maestras ni crudo: sale entero de consolidar.py, homologar.py y
# glosario.py. Hay que regenerarlo cuando cambia el CÓDIGO, no cuando
# llegan datos nuevos — igual que DICCIONARIO.md.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ABRIR=1
[ "${1:-}" = "--no-abrir" ] && ABRIR=0

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
VIZ="$DATOS/visualizaciones"
mkdir -p "$VIZ"
SALIDA="$VIZ/variables_maestras.html"

PYTHONPATH="$REPO" python3 -u "$REPO/variables.py" --salida "$SALIDA" || exit $?

if [ "$ABRIR" -eq 1 ] && command -v open >/dev/null 2>&1; then
    open "$SALIDA"
fi
