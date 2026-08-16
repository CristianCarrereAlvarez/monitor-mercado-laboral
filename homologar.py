"""
Homologación carreras trabajando → SIES: genera la cola editable
=================================================================

Convierte la taxonomía observada en `maestras/carreras_trabajando.csv`
en `maestras/homologacion_carreras.csv`, un archivo pensado para que una
persona lo abra en una planilla y lo complete a mano.

POR QUÉ UN CSV Y NO UN DICCIONARIO EN PYTHON
  Lo edita una persona, probablemente en una planilla. Un dict de Python
  obliga a tocar código para registrar una decisión.

QUÉ AUTOMATIZA Y QUÉ NO
  Automatiza SOLO el match exacto normalizado (minúsculas, sin tildes,
  sin puntuación). Nada de fuzzy: en esta taxonomía "Ingeniería Civil" e
  "Ingeniería Civil Industrial" están a un token y son carreras
  distintas.

  Sí genera dos columnas `sugerencia` y `score` con el nombre SIES más
  parecido por solapamiento de tokens. **Esas columnas NUNCA se aplican
  solas.** Sirven para ordenar la pantalla y que revisar sea más rápido;
  la decisión la toma la persona escribiendo en `carrera_sies`.

PRESERVA EL TRABAJO MANUAL
  Mismo principio que consolidar.py: es idempotente y las columnas
  manuales sobreviven. Solo rellena celdas VACÍAS; nunca pisa lo que ya
  escribiste, ni siquiera si el match exacto dice otra cosa.

  La clave es compuesta: (carrera_trabajando, nivel_condicion). Eso
  permite resolver los casos 1:N —"Prevención de Riesgos / Seguridad
  Industrial" es "Ingeniería en" o "Técnico en" según el aviso—
  duplicando la fila y poniendo `universitaria` en una y `tecnica` en la
  otra. El default es `*`, que significa "vale para cualquier nivel".

FILAS QUE NO SE BORRAN
  Una carrera que dejó de aparecer en el crudo conserva su fila. La
  decisión ya tomada no se pierde.

`sin_equivalencia` ES UNA DECISIÓN, NO UN HUECO
  Escribirlo en `tipo_relacion` deja registrado que se miró y no hay
  equivalente. Así "Ingeniería Civil" a secas no vuelve a aparecer como
  pendiente en cada revisión.

Uso:
  python homologar.py
  python homologar.py --maestras maestras
"""

import argparse, csv, os, re, sys, unicodedata

try:
    from carreras_sies_2026 import CARRERAS_POR_AREA
except ImportError:
    print("⛔  No pude importar carreras_sies_2026.py.")
    print("    Corré esto con PYTHONPATH apuntando al repo, o desde el repo.")
    sys.exit(1)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ENTRADA = 'carreras_trabajando.csv'
SALIDA  = 'homologacion_carreras.csv'

# Las que el script controla y reescribe en cada corrida.
GESTIONADAS = ['carrera_trabajando', 'nivel_condicion',
               'n_avisos_especificos', 'n_avisos_acum', 'areas_observadas',
               'sugerencia', 'score']

# Las que completa la persona. Se preservan siempre.
MANUALES = ['carrera_sies', 'area_sies', 'tipo_relacion',
            'revisado_por', 'fecha_revision', 'nota']

COLUMNAS = (GESTIONADAS[:2] + MANUALES[:3] + GESTIONADAS[2:]
            + MANUALES[3:])

TIPOS_RELACION = ('exacta', 'agregacion', 'ambigua', 'sin_equivalencia')


def normalizar(s):
    if not isinstance(s, str):
        return ''
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def tokens(s):
    return {t for t in normalizar(s).split() if len(t) > 2}


def indice_sies():
    """nombre SIES normalizado → (nombre canónico, áreas)."""
    idx = {}
    for area, carreras in CARRERAS_POR_AREA.items():
        for sies in carreras.values():
            k = normalizar(sies)
            if k not in idx:
                idx[k] = [sies, set()]
            idx[k][1].add(area)
    return {k: (v[0], ' | '.join(sorted(v[1]))) for k, v in idx.items()}


def sugerir(nombre, sies_idx):
    """(sugerencia, score) por solapamiento de tokens. NO es una decisión:
    ordena la revisión, nada más."""
    t = tokens(nombre)
    if not t:
        return None, None
    mejor, mejor_score = None, 0.0
    for k, (canon, _) in sies_idx.items():
        o = tokens(canon)
        if not o:
            continue
        j = len(t & o) / len(t | o)
        if j > mejor_score:
            mejor, mejor_score = canon, j
    if mejor_score < 0.30:
        return None, None
    return mejor, round(mejor_score, 2)


def leer_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main(dir_maestras):
    p_in  = os.path.join(dir_maestras, ENTRADA)
    p_out = os.path.join(dir_maestras, SALIDA)

    if not os.path.exists(p_in):
        print(f"⛔  No existe {p_in}")
        print(f"    Corré consolidar.py primero.")
        sys.exit(1)

    observadas = leer_csv(p_in)
    sies_idx = indice_sies()

    # Filas previas indexadas por clave compuesta, para preservar.
    previas = {}
    for r in leer_csv(p_out):
        clave = (r.get('carrera_trabajando', ''),
                 r.get('nivel_condicion', '') or '*')
        previas[clave] = r
    extras = [c for r in previas.values() for c in r
              if c not in COLUMNAS]
    extras = list(dict.fromkeys(extras))   # únicas, en orden

    print("=" * 64)
    print("  HOMOLOGACIÓN — cola editable")
    print("=" * 64)
    print(f"  observadas en el crudo : {len(observadas)}")
    print(f"  filas ya existentes    : {len(previas)}")
    if extras:
        print(f"  columnas extra que se conservan: {', '.join(extras)}")

    salida, vistas = [], set()
    n_auto = n_ya = 0

    for obs in observadas:
        nombre = obs['carrera_trabajando']
        if not nombre:
            continue
        # Todas las filas previas de este nombre (puede haber varias por
        # nivel_condicion). Si no hay ninguna, se crea una con '*'.
        niveles = [k[1] for k in previas if k[0] == nombre] or ['*']

        for nivel in niveles:
            clave = (nombre, nivel)
            prev = previas.get(clave, {})
            vistas.add(clave)

            fila = {c: prev.get(c, '') for c in COLUMNAS + extras}
            fila['carrera_trabajando'] = nombre
            fila['nivel_condicion'] = nivel
            fila['n_avisos_especificos'] = obs.get('n_avisos_especificos', '')
            fila['n_avisos_acum'] = obs.get('n_avisos_acum', '')
            fila['areas_observadas'] = obs.get('areas_observadas', '')

            # ── match exacto normalizado: lo único que se automatiza ──
            exacto = sies_idx.get(normalizar(nombre))
            if fila['carrera_sies']:
                n_ya += 1
            elif exacto:
                fila['carrera_sies']  = exacto[0]
                fila['area_sies']     = exacto[1]
                fila['tipo_relacion'] = 'exacta'
                fila['revisado_por']  = 'auto:match_exacto'
                n_auto += 1

            # ── sugerencia: ordena la revisión, no decide ──
            if not fila['carrera_sies']:
                s, sc = sugerir(nombre, sies_idx)
                fila['sugerencia'], fila['score'] = s or '', sc or ''
            else:
                fila['sugerencia'], fila['score'] = '', ''

            salida.append(fila)

    # Filas que ya no aparecen en el crudo: se conservan intactas.
    conservadas = 0
    for clave, prev in previas.items():
        if clave in vistas:
            continue
        fila = {c: prev.get(c, '') for c in COLUMNAS + extras}
        fila['carrera_trabajando'], fila['nivel_condicion'] = clave
        salida.append(fila)
        conservadas += 1

    def orden(f):
        try:
            n = int(f.get('n_avisos_especificos') or 0)
        except ValueError:
            n = 0
        return (bool(f.get('carrera_sies')), -n, f['carrera_trabajando'])

    salida.sort(key=orden)

    os.makedirs(dir_maestras, exist_ok=True)
    with open(p_out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS + extras,
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(salida)

    # ── resumen ────────────────────────────────────────────────
    pend = [f for f in salida if not f.get('carrera_sies')]
    def esp(f):
        try:
            return int(f.get('n_avisos_especificos') or 0)
        except ValueError:
            return 0
    tot_esp  = sum(esp(f) for f in salida)
    pend_esp = sum(esp(f) for f in pend)
    pct = lambda x, b: f"{x*100/b:.1f}%" if b else "-"

    print(f"\n  filas escritas         : {len(salida)}")
    print(f"    resueltas por match  : {n_auto} (nuevas en esta corrida)")
    print(f"    ya resueltas antes   : {n_ya}")
    print(f"    conservadas sin crudo: {conservadas}")
    print(f"    PENDIENTES           : {len(pend)}")
    print(f"\n  cobertura por avisos específicos")
    print(f"    resuelto  : {tot_esp - pend_esp} ({pct(tot_esp-pend_esp, tot_esp)})")
    print(f"    pendiente : {pend_esp} ({pct(pend_esp, tot_esp)})")

    if pend:
        print(f"\n  TOP 15 PENDIENTES — por acá conviene empezar")
        print(f"  {'avisos':>7}  {'carrera_trabajando':<44} sugerencia")
        for f in pend[:15]:
            s = f.get('sugerencia') or '—'
            sc = f" [{f['score']}]" if f.get('score') else ''
            print(f"  {esp(f):>7}  {f['carrera_trabajando'][:44]:<44} "
                  f"{s[:32]}{sc}")

    print(f"\n  Archivo: {p_out}")
    print(f"  Abrilo en una planilla y completá `carrera_sies`,")
    print(f"  `area_sies` y `tipo_relacion` ({' | '.join(TIPOS_RELACION)}).")
    print(f"  `sugerencia` y `score` son ayuda visual: NO son decisiones.")
    print(f"  Volvé a correr esto cuando quieras; lo escrito se conserva.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    a = ap.parse_args()
    main(a.maestras)
