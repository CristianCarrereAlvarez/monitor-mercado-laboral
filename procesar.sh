#!/usr/bin/env bash
#
# Todo lo que va DESPUÉS de la captura, en un comando.
#
#   consolidar → control → diccionario
#
# Existe por la misma razón que capturar.sh: elimina una clase entera de
# error en vez de pedir que la recuerdes. Las tres etapas necesitaban
# exportar una variable con la ruta de Drive, hacer cd, y pasar rutas a
# mano en cada comando. Pegar ese bloque en la terminal falla en cuanto
# algo se detiene a preguntar —un editor, una contraseña—: el resto del
# texto se le mete adentro. Pasó tres veces.
#
# Uso:
#   ./procesar.sh                    # consolidar + control + diccionario
#   ./procesar.sh --solo-consolidar
#   ./procesar.sh --muestra 3000     # diccionario sin leer todo el crudo
#
# La carpeta de datos se resuelve sola (la misma lógica de capturar.sh).
# Para forzarla:  MML_DATOS=... ./procesar.sh
#
# Deja un log por corrida en <datos>/logs/.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SOLO_CONSOLIDAR=0
MUESTRA=()
while [ $# -gt 0 ]; do
    case "$1" in
        --solo-consolidar) SOLO_CONSOLIDAR=1; shift ;;
        --muestra) MUESTRA=(--muestra "${2:-3000}"); shift 2 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) printf '\n  ⛔  Opción desconocida: %s\n\n' "$1" >&2; exit 1 ;;
    esac
done

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
mkdir -p "$DATOS/logs"
LOG="$DATOS/logs/procesar_$(date +%Y-%m-%d_%H%M%S).log"

linea() { printf '%s\n' "════════════════════════════════════════════════════════════════"; }

cd "$DATOS" || { printf '\n  ⛔  No pude entrar a %s\n\n' "$DATOS" >&2; exit 1; }

{
linea
echo "  PROCESAR — $(date '+%Y-%m-%d %H:%M')"
echo "  datos: $DATOS"
linea

echo
linea
echo "  1. CONSOLIDAR"
linea
PYTHONPATH="$REPO" python3 -u "$REPO/consolidar.py" \
    --crudo crudo --maestras maestras
COD=$?

if [ "$COD" -ne 0 ]; then
    echo
    linea
    echo "  ⛔  La consolidación falló (código $COD). No sigo:"
    echo "     el control y el diccionario leen lo que ella escribe."
    linea
    exit "$COD"
fi

if [ "$SOLO_CONSOLIDAR" -eq 0 ]; then
    echo
    linea
    echo "  2. CONTROL DE CALIDAD"
    linea
    PYTHONPATH="$REPO" python3 -u "$REPO/control.py" --maestras maestras

    echo
    linea
    echo "  3. DICCIONARIO DE VARIABLES"
    linea
    # El diccionario lee el crudo entero para calcular el relleno exacto.
    # Con --muestra es aproximado, y el documento lo dice.
    PYTHONPATH="$REPO" python3 -u "$REPO/diccionario.py" \
        --maestras maestras --crudo crudo --evidencia \
        ${MUESTRA[@]+"${MUESTRA[@]}"}
fi

echo
echo "  Log completo: $LOG"
linea
} 2>&1 | tee "$LOG"

exit "${PIPESTATUS[0]}"
