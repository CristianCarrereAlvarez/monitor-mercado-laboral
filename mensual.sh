#!/usr/bin/env bash
#
# Corrida mensual completa: las 10 áreas en orden, y después consolidar.
#
# Pensado para lanzarlo una vez al mes y olvidarse. Es reanudable de
# punta a punta: si se corta a mitad, se relanza lo mismo y cada área
# baja solo lo que le falta.
#
# Uso:
#   ./mensual.sh                 # todas las áreas + consolidar
#   ./mensual.sh --solo-captura  # sin consolidar
#   ./mensual.sh --desde "Salud" # retomar desde un área
#
# Deja un log por corrida en <datos>/logs/ y un resumen al final.
#
# CUÁNDO SE CORTA TODO
#   Si un área falla por rechazo del sitio o por un problema local (SSL,
#   DNS, red), las demás van a fallar igual: no tiene sentido insistir y
#   con un bloqueo por IP encima lo empeora. Se corta y se avisa.
#   Un corte a mitad de captura (código 3) sí se reintenta una vez.

set -uo pipefail   # sin -e: el manejo de errores es explícito

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# De menor a mayor cantidad de términos: los problemas salen baratos.
AREAS=(
    "Derecho"
    "Humanidades"
    "Agropecuaria"
    "Arte y Arquitectura"
    "Ciencias Sociales"
    "Educación"
    "Ciencias Básicas"
    "Salud"
    "Administración y Comercio"
    "Tecnología"
)

CONSOLIDAR=1
DESDE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --solo-captura) CONSOLIDAR=0; shift ;;
        --desde) DESDE="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) printf '\n  ⛔  Opción desconocida: %s\n\n' "$1" >&2; exit 1 ;;
    esac
done

DATOS="$("$REPO/capturar.sh" --donde)" || exit 1
mkdir -p "$DATOS/logs"
SELLO="$(date +%Y-%m-%d_%H%M%S)"
LOG="$DATOS/logs/mensual_$SELLO.log"

# caffeinate existe solo en macOS; en otros lados se corre pelado.
if command -v caffeinate >/dev/null 2>&1; then
    SIN_DORMIR=(caffeinate -i)
else
    SIN_DORMIR=()
fi

linea() { printf '%s\n' "════════════════════════════════════════════════════════════════"; }

{
linea
echo "  CORRIDA MENSUAL — $(date '+%Y-%m-%d %H:%M')"
echo "  datos: $DATOS"
echo "  log  : $LOG"
linea

OK=(); FALLARON=(); SALTEADAS=()
ARRANCO=1
[ -n "$DESDE" ] && ARRANCO=0

for AREA in "${AREAS[@]}"; do
    if [ "$ARRANCO" -eq 0 ]; then
        if [ "$AREA" = "$DESDE" ]; then
            ARRANCO=1
        else
            SALTEADAS+=("$AREA"); continue
        fi
    fi

    echo
    linea
    echo "  ▶  $AREA   ($(date '+%H:%M'))"
    linea

    "${SIN_DORMIR[@]+"${SIN_DORMIR[@]}"}" "$REPO/capturar.sh" "$AREA"
    COD=$?

    if [ "$COD" -eq 3 ]; then
        echo
        echo "  ↻  se cortó a mitad; reintento una vez (es reanudable)"
        sleep 10
        "${SIN_DORMIR[@]+"${SIN_DORMIR[@]}"}" "$REPO/capturar.sh" "$AREA"
        COD=$?
    fi

    case "$COD" in
        0) OK+=("$AREA") ;;
        2) FALLARON+=("$AREA")
           echo
           linea
           echo "  ⛔  CORRIDA MENSUAL INTERRUMPIDA en '$AREA'"
           linea
           echo "  El fallo no es de esta área: o el sitio rechaza, o hay"
           echo "  un problema local. Las demás van a fallar igual, así que"
           echo "  no sigo — con un bloqueo por IP, insistir lo empeora."
           echo
           echo "  Mirá el motivo arriba. Cuando esté resuelto, retomá sin"
           echo "  repetir lo ya hecho:"
           echo
           echo "      ./mensual.sh --desde \"$AREA\""
           linea
           break ;;
        *) FALLARON+=("$AREA")
           echo "  ⚠  '$AREA' terminó con código $COD; sigo con la próxima" ;;
    esac
done

echo
linea
echo "  RESUMEN — $(date '+%Y-%m-%d %H:%M')"
linea
echo "  capturadas : ${#OK[@]}/${#AREAS[@]}"
for A in ${OK[@]+"${OK[@]}"};        do echo "      ✓  $A"; done
for A in ${FALLARON[@]+"${FALLARON[@]}"}; do echo "      ✗  $A"; done
for A in ${SALTEADAS[@]+"${SALTEADAS[@]}"}; do echo "      ·  $A (salteada)"; done

if [ "$CONSOLIDAR" -eq 1 ] && [ "${#OK[@]}" -gt 0 ]; then
    echo
    linea
    echo "  CONSOLIDANDO"
    linea
    cd "$DATOS" && PYTHONPATH="$REPO" python3 -u "$REPO/consolidar.py" \
        --crudo crudo --maestras maestras
elif [ "$CONSOLIDAR" -eq 1 ]; then
    echo
    echo "  No se consolidó: ninguna área se capturó."
fi

echo
echo "  Log completo: $LOG"
linea
} 2>&1 | tee "$LOG"

exit "${PIPESTATUS[0]}"
