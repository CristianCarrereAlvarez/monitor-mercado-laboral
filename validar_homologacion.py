"""
Validación de la homologación carrera_trabajando → programa propio
===================================================================

`homologacion.csv` es trabajo humano: 528 nombres de carrera declarados
en los avisos, mapeados a un catálogo propio de programas formativos, a
un campo ISCED-F, a un nivel, o a nada. Este script no lo produce ni lo
corrige: lo **revisa**, y separa tres cosas que no son lo mismo.

  ⛔ ERROR    rompe el join o el vocabulario. Hay que arreglarlo antes
              de usar el archivo para cualquier análisis.
  ⚠  REVISAR  el archivo es válido pero algo no cierra. Necesita ojo
              humano; el script no decide.
  ·  INFORME  contexto para saber dónde está parado el trabajo.

POR QUÉ EXISTE
  El mapeo no es "carrera → programa" y ya. Un nombre de aviso puede
  apuntar a un programa, a un campo de estudio (`Ingeniería`), a un
  nivel sin disciplina (`MBA`), a un cargo (`Paramédico`) o a nada
  (`Otra carrera`). Cinco destinos distintos, cada uno con su propia
  regla de coherencia. Escritas a mano en una planilla, esas reglas se
  violan en silencio: una fila con `tipo_entrada = campo_iscedf` y un
  programa lleno se ve bien y no lo está.

  Y hay un error que no se ve nunca: el nombre de la carrera es la
  clave del join, y once de los 528 traen espacios de más. Si el
  archivo y la maestra difieren en un espacio, esa carrera desaparece
  del análisis sin que nada avise. Es la lección 10 del proyecto.

Uso:
  ./validar.sh
  python validar_homologacion.py --homologacion <ruta> [--carreras <ruta>]
"""

import argparse, csv, os, re, sys, unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

REPO = os.path.dirname(os.path.abspath(__file__))

# Vocabularios cerrados. Fuente: hoja «Diccionario» del libro de
# homologación. Si se agrega un valor, va acá y va allá.
VOCAB = {
    'tipo_entrada': {'programa_propio', 'campo_iscedf', 'nivel_formativo',
                     'solo_ocupacion', 'no_informativo'},
    'tipo_relacion': {'exacta', 'equivalente', 'multiple',
                      'no_homologable_programa', 'no_homologable_carrera'},
    'estado': {'validado', 'propuesto', 'pendiente', 'descartado'},
    'confianza': {'alta', 'media', 'baja'},
    'nivel_formativo': {'', 'tecnico', 'profesional', 'profesional_con_grado',
                        'licenciatura', 'posgrado', 'posgrado_postitulo',
                        'sin_definir'},
}

# Qué destino admite cada tipo_entrada.
#   programa  : la columna programa_propio debe estar llena / vacía
#   isced     : la columna isced_cod debe estar llena / vacía
DESTINO = {
    'programa_propio': ('lleno', 'vacio'),
    'campo_iscedf':    ('vacio', 'lleno'),
    'nivel_formativo': ('vacio', 'vacio'),
    'solo_ocupacion':  ('vacio', 'vacio'),
    'no_informativo':  ('vacio', 'vacio'),
}

# Una genérica SIES "residual" no nombra una carrera: es el cajón donde
# SIES pone lo que no tiene entrada propia. Un programa respaldado solo
# por un cajón es, por definición, un programa sin equivalente SIES.
RESIDUAL = re.compile(r'^(otr[oa]s?\b|postítulo|postitulo)', re.I)


def nz(s):
    """Minúsculas, sin tildes, espacios colapsados."""
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip()


def entero(v):
    try:
        return int(str(v).strip() or 0)
    except (TypeError, ValueError):
        return 0


def leer(path, que):
    if not os.path.exists(path):
        print(f"\n  ⛔  No existe {que}: {path}\n")
        sys.exit(1)
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class Informe:
    """Junta los hallazgos y los imprime agrupados, con el peso de cada
    uno en menciones. El orden por volumen es lo que hace accionable un
    listado de 30 líneas."""

    def __init__(self):
        self.errores, self.revisar = [], []

    def error(self, grupo, texto, peso=0):
        self.errores.append((grupo, texto, peso))

    def rev(self, grupo, texto, peso=0):
        self.revisar.append((grupo, texto, peso))

    def volcar(self, titulo, items, marca):
        if not items:
            return
        print(f"\n{'─' * 68}\n  {titulo}: {len(items)}\n{'─' * 68}")
        for grupo in dict.fromkeys(g for g, _, _ in items):
            sub = [i for i in items if i[0] == grupo]
            peso = sum(i[2] for i in sub)
            print(f"\n  {marca} {grupo}  —  {len(sub)} filas"
                  + (f", {peso} menciones" if peso else ""))
            for _, t, _ in sorted(sub, key=lambda i: -i[2]):
                print(f"      {t}")


def main(f_hom, f_prog, f_isced, f_carr, tope, adoptar_nombres):
    H = leer(f_hom, 'la homologación')
    P = leer(f_prog, 'el catálogo de programas propios')
    I = leer(f_isced, 'la tabla ISCED-F')
    prog = {r['programa_propio']: r for r in P}
    isced = {r['codigo']: r['nombre'] for r in I}
    inf = Informe()

    def n(r):
        return entero(r.get('n_avisos_especificos'))

    por_carrera = defaultdict(list)
    for r in H:
        por_carrera[r['carrera_trabajando']].append(r)
    total = sum(n(v[0]) for v in por_carrera.values())

    print("=" * 68)
    print(f"  VALIDACIÓN DE LA HOMOLOGACIÓN")
    print("=" * 68)
    print(f"  {len(H)} filas · {len(por_carrera)} carreras de trabajando · "
          f"{total} menciones específicas")
    print(f"  catálogo propio: {len(prog)} programas · "
          f"ISCED-F: {len(isced)} códigos")

    # ── 1. clave y orden ───────────────────────────────────────────
    dup = [k for k, c in Counter((r['carrera_trabajando'],
                                  r['orden_relacion']) for r in H).items()
           if c > 1]
    for k in dup:
        inf.error('clave duplicada (carrera_trabajando + orden_relacion)',
                  f"{k[0]}  orden {k[1]}")
    for k, v in por_carrera.items():
        ordenes = sorted(entero(r['orden_relacion']) for r in v)
        if ordenes != list(range(1, len(v) + 1)):
            inf.error('orden_relacion no correlativo desde 1',
                      f"{k}  →  {ordenes}", n(v[0]))

    # ── 2. vocabularios ────────────────────────────────────────────
    for col, validos in VOCAB.items():
        for r in H:
            if r.get(col, '') not in validos:
                inf.error(f'valor fuera del vocabulario de `{col}`',
                          f"{r['carrera_trabajando'][:44]:44s} "
                          f"{col} = {r.get(col)!r}", n(r))

    # ── 3. coherencia tipo_entrada ↔ destino ───────────────────────
    for r in H:
        te = r['tipo_entrada']
        if te not in DESTINO:
            continue
        esp_p, esp_i = DESTINO[te]
        hay_p = bool(r['programa_propio'].strip())
        hay_i = bool(r['isced_cod'].strip())
        if (esp_p == 'lleno') != hay_p:
            inf.error(f'tipo_entrada `{te}` con programa_propio '
                      f'{"vacío" if esp_p == "lleno" else "lleno"}',
                      f"{r['carrera_trabajando'][:44]:44s} "
                      f"→ {r['programa_propio'] or '(vacío)'}", n(r))
        if (esp_i == 'lleno') != hay_i:
            inf.error(f'tipo_entrada `{te}` con isced_cod '
                      f'{"vacío" if esp_i == "lleno" else "lleno"}',
                      f"{r['carrera_trabajando'][:44]:44s} "
                      f"→ {r['isced_cod'] or '(vacío)'}", n(r))

    # ── 4. destinos que existen ────────────────────────────────────
    for r in H:
        p = r['programa_propio'].strip()
        if p and p not in prog:
            inf.error('programa_propio que no está en el catálogo',
                      f"{r['carrera_trabajando'][:44]:44s} → {p}", n(r))
        c = r['isced_cod'].strip()
        if c:
            if c not in isced:
                inf.error('isced_cod que no existe en ISCED-F 2013',
                          f"{r['carrera_trabajando'][:44]:44s} → {c}", n(r))
            elif nz(r['isced_nombre']) != nz(isced[c]):
                inf.error('isced_nombre que no corresponde al código',
                          f"{r['carrera_trabajando'][:40]:40s} {c} dice "
                          f"{r['isced_nombre']!r}, es {isced[c]!r}", n(r))

    # ── 5. multiple ↔ número de filas ──────────────────────────────
    for k, v in por_carrera.items():
        marcadas = sum(1 for r in v if r['tipo_relacion'] == 'multiple')
        if len(v) > 1 and marcadas != len(v):
            inf.error('carrera con varios destinos sin marcar todas '
                      '`multiple`', f"{k}  ({len(v)} filas, {marcadas} "
                      f"marcadas)", n(v[0]))
        if len(v) == 1 and marcadas:
            inf.error('`multiple` en una carrera con un solo destino', k,
                      n(v[0]))

    # ── 6. el join contra la maestra ───────────────────────────────
    # El nombre es la clave y once de los 528 traen espacios de más.
    adoptar = {}
    if f_carr and os.path.exists(f_carr):
        CT = leer(f_carr, 'la maestra de carreras')
        maes = {r['carrera_trabajando'] for r in CT}
        homs = set(por_carrera)
        idx_m = defaultdict(list)
        for x in maes:
            idx_m[nz(x)].append(x)
        for x in sorted(homs - maes):
            iguales = [y for y in idx_m.get(nz(x), []) if y != x]
            if iguales:
                adoptar[x] = iguales[0]
                inf.error('el nombre solo calza al normalizar espacios '
                          '(el join exacto lo pierde)',
                          f"homologación {x!r}  ≠  maestra {iguales[0]!r}",
                          n(por_carrera[x][0]))
            else:
                inf.error('carrera en la homologación que no está en la '
                          'maestra', repr(x), n(por_carrera[x][0]))
        idx_h = {nz(x) for x in homs}
        for x in sorted(maes - homs):
            if nz(x) not in idx_h:
                inf.rev('carrera de la maestra sin fila de homologación',
                        repr(x))
    else:
        print(f"\n  ·  Sin maestra a mano: no se validó el join por nombre."
              f"\n     (--carreras <dir maestras>/carreras_trabajando.csv)")

    # ── 7. no_homologable_carrera ──────────────────────────────────
    # Definición acordada: el programa destino es el correcto, pero no
    # tiene carrera genérica SIES que lo respalde. Si la tiene, el valor
    # está mal puesto: es una equivalencia común.
    for r in H:
        if r['tipo_relacion'] != 'no_homologable_carrera':
            continue
        p = prog.get(r['programa_propio'].strip())
        if not p:
            continue
        g = p['generica_sies'].strip()
        if g and not RESIDUAL.match(g):
            inf.rev('`no_homologable_carrera` cuyo destino SÍ tiene '
                    'genérica SIES',
                    f"{r['carrera_trabajando'][:38]:38s} → "
                    f"{r['programa_propio'][:30]:30s} "
                    f"(genérica: {g})", n(r))

    # ── 8. desajuste de nivel ──────────────────────────────────────
    # El nombre del aviso suele declarar el nivel; el programa destino
    # declara en qué niveles se imparte. Cuando se contradicen, uno de
    # los dos está mal. Heurística sobre el nombre: avisa, no decide.
    def nivel_del_nombre(s):
        t = nz(s)
        if re.match(r'^(tecnico|tecnica|tec\b|tns\b|tecnologo)', t):
            return 'tecnico'
        # Anclado al comienzo a propósito: en «Dibujo de Proyectos de
        # Arquitectura e Ingeniería» la palabra aparece como
        # complemento, no como el nivel del programa. Buscarla en
        # cualquier posición daba un falso positivo.
        if re.match(r'(ingenieria|licenciatura|licenciado|pedagogia|'
                    r'magister|doctorado|mba)\b', t):
            return 'superior'
        return None

    for r in H:
        p = prog.get(r['programa_propio'].strip())
        if not p:
            continue
        niveles = {x.strip() for x in p['nivel_condicion'].split('|')
                   if x.strip()}
        ln = nivel_del_nombre(r['carrera_trabajando'])
        etq = None
        if ln == 'tecnico' and 'tecnico' not in niveles:
            etq = 'el nombre dice técnico, el programa no se imparte en técnico'
        elif ln == 'superior' and niveles == {'tecnico'}:
            etq = 'el nombre dice ingeniería/licenciatura, el programa es solo técnico'
        if etq:
            inf.rev(etq, f"{r['carrera_trabajando'][:40]:40s} → "
                         f"{r['programa_propio'][:32]:32s} "
                         f"[{'|'.join(sorted(niveles))}] "
                         f"{r['estado']}/{r['confianza']}", n(r))

    # ── salida ─────────────────────────────────────────────────────
    # La maestra manda: es lo que consolidar.py escribe desde el crudo.
    # Solo se reescriben nombres que ya calzaban al normalizar, así que
    # ninguna fila cambia de destino.
    if adoptar and adoptar_nombres:
        for r in H:
            if r['carrera_trabajando'] in adoptar:
                r['carrera_trabajando'] = adoptar[r['carrera_trabajando']]
        with open(f_hom, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(H[0].keys()))
            w.writeheader()
            w.writerows(H)
        print(f"\n  ✓  {len(adoptar)} nombres reescritos con la grafía de "
              f"la maestra, en {f_hom}")
        inf.errores = [e for e in inf.errores
                       if 'espacios' not in e[0]]

    inf.volcar('ERRORES — rompen el join o el vocabulario',
               inf.errores, '⛔')
    inf.volcar('REVISAR — el archivo es válido, pero algo no cierra',
               inf.revisar, '⚠ ')

    # ── informe ────────────────────────────────────────────────────
    print(f"\n{'─' * 68}\n  INFORME\n{'─' * 68}")

    def bloque(titulo, clave, orden):
        print(f"\n  {titulo}")
        cnt, men = Counter(), Counter()
        for k, v in por_carrera.items():
            x = clave(v)
            cnt[x] += 1
            men[x] += n(v[0])
        for x in orden:
            if cnt[x]:
                print(f"    {x:22s} {cnt[x]:4d} carreras  {men[x]:6d} "
                      f"menciones  {men[x] * 100 / total:5.1f}%")

    bloque('destino (tipo_entrada)', lambda v: v[0]['tipo_entrada'],
           ['programa_propio', 'campo_iscedf', 'nivel_formativo',
            'solo_ocupacion', 'no_informativo'])
    bloque('estado', lambda v: min(r['estado'] for r in v),
           ['descartado', 'pendiente', 'propuesto', 'validado'])
    bloque('confianza', lambda v: min(r['confianza'] for r in v),
           ['alta', 'baja', 'media'])

    sin = [p for p in prog if not any(r['programa_propio'] == p for r in H)]
    print(f"\n  programas del catálogo que no reciben ninguna carrera: "
          f"{len(sin)} de {len(prog)}")
    for p in sorted(sin):
        print(f"      {p}")

    pend = sorted((v for v in por_carrera.values()
                   if all(r['estado'] != 'validado' for r in v)),
                  key=lambda v: -n(v[0]))
    peso = sum(n(v[0]) for v in pend)
    print(f"\n  cola de revisión: {len(pend)} carreras, {peso} menciones "
          f"({peso * 100 / total:.1f}% del total)")
    for v in pend[:tope]:
        r = v[0]
        dest = r['programa_propio'] or f"{r['isced_cod']} {r['isced_nombre']}"
        print(f"    {n(r):5d}  {r['carrera_trabajando'][:40]:40s} "
              f"{r['confianza']:5s} → {dest[:44]}")
    if len(pend) > tope:
        print(f"    … y {len(pend) - tope} carreras más "
              f"({sum(n(v[0]) for v in pend[tope:])} menciones)")

    print(f"\n{'=' * 68}")
    print(f"  {len(inf.errores)} errores · {len(inf.revisar)} para revisar")
    print(f"{'=' * 68}\n")
    return 1 if inf.errores else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--homologacion', default='maestras/homologacion.csv')
    ap.add_argument('--programas',
                    default=os.path.join(REPO, 'programas_propios.csv'))
    ap.add_argument('--isced', default=os.path.join(REPO, 'isced_f_2013.csv'))
    ap.add_argument('--carreras', default='maestras/carreras_trabajando.csv',
                    help='la maestra, para validar el join por nombre')
    ap.add_argument('--adoptar-nombres-maestra', action='store_true',
                    help='reescribe en la homologación los nombres que solo '
                         'difieren en espacios, con la grafía de la maestra')
    ap.add_argument('--tope', type=int, default=25,
                    help='cuántas carreras de la cola listar (default 25)')
    a = ap.parse_args()
    sys.exit(main(a.homologacion, a.programas, a.isced, a.carreras, a.tope,
                  a.adoptar_nombres_maestra))
