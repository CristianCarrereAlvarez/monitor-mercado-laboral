#!/usr/bin/env bash
#
# Consultar qué hay detrás de un nombre de carrera, sin escribir rutas.
#
#   ./mirar.sh "Ingeniería en Metalmecánica"
#   ./mirar.sh --buscar metal
#   ./mirar.sh "Electricidad" --n 20
#
# Resuelve la carpeta de datos igual que capturar.sh y procesar.sh.
# Para forzarla:  MML_DATOS=... ./mirar.sh "..."

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    cat >&2 <<FIN

  Uso: ./mirar.sh "<nombre de carrera>"  [--n 20]
       ./mirar.sh --buscar <texto>

FIN
    exit 1
fi

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1

exec env PYTHONPATH="$REPO" python3 -u "$REPO/mirar.py" \
    --maestras "$DATOS/maestras" "$@"
