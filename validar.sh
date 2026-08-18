#!/usr/bin/env bash
#
# Revisa la homologación entrada_trabajando → programa propio.
#
#   ./validar.sh                          # informe
#   ./validar.sh --adoptar-nombres-maestra   # y arregla los espacios
#   ./validar.sh --tope 50                # cola de revisión más larga
#
# Lee <datos>/maestras/homologacion.csv y la contrasta con el catálogo
# propio y con la tabla ISCED-F, que viven en el repo.
#
# Para forzar la carpeta de datos:  MML_DATOS=... ./validar.sh

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATOS="$("$REPO/capturar.sh" --donde)" || exit 1

exec env PYTHONPATH="$REPO" python3 -u "$REPO/validar_homologacion.py" \
    --homologacion "$DATOS/maestras/homologacion.csv" \
    --carreras "$DATOS/maestras/entradas_trabajando.csv" \
    --aviso-carrera "$DATOS/maestras/aviso_entrada.csv" "$@"
