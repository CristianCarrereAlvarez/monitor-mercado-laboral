"""
Qué hay detrás de un nombre de carrera
=======================================

Herramienta de consulta para la homologación. Dado un nombre de
`entrada_trabajando`, muestra los avisos que lo declaran: qué cargos
son, quién los publica, con qué nivel académico y —lo más útil— **con
qué otras carreras aparece declarado**.

POR QUÉ LAS CO-DECLARADAS SON LA SEÑAL FUERTE
  El nombre solo no alcanza para decidir a qué carrera SIES corresponde.
  Pero si "Ingeniería en Metalmecánica" aparece una y otra vez junto a
  "Ingeniería Civil Mecánica" y "Técnico en Mecánica Industrial", el
  empleador está diciendo a qué familia pertenece. Eso es evidencia; la
  similitud de strings no lo es (ver la columna `sugerencia`, que a
  "Ingeniería Civil" le propone "Ingeniería Civil Industrial").

Excluye los avisos genéricos de los conteos de co-declaración: un aviso
que declara 504 carreras las haría aparecer a todas como co-declaradas.

Uso:
  ./mirar.sh "Ingeniería en Metalmecánica"
  ./mirar.sh --buscar metal          # qué nombres contienen "metal"
  ./mirar.sh "Electricidad" --n 20   # más filas por sección

  python mirar.py "..." --maestras <dir>
"""

import argparse, csv, os, re, sys, unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30


def normalizar(s):
    if not isinstance(s, str):
        return ''
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def entero(v, d=0):
    try:
        return int(str(v).strip() or d)
    except (TypeError, ValueError):
        return d


def leer(path):
    if not os.path.exists(path):
        print(f"⛔  No existe {path}")
        sys.exit(1)
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def barra(n, tope, ancho=22):
    return '█' * max(1, round(n * ancho / tope)) if tope else ''


def tabla(titulo, conteo, total, n, nota=''):
    if not conteo:
        return
    print(f"\n  {titulo}{nota}")
    tope = conteo.most_common(1)[0][1]
    for val, c in conteo.most_common(n):
        etq = (val or '(vacío)')[:52]
        print(f"    {c:>5}  {c*100/total:>5.1f}%  {barra(c, tope):<22} {etq}")
    resto = len(conteo) - n
    if resto > 0:
        print(f"    … y {resto} valores más")


def main(dir_maestras, nombre, buscar, n):
    ac = leer(os.path.join(dir_maestras, 'aviso_entrada.csv'))
    decl = [f for f in ac if f.get('fuente') == 'declarada']

    # ── modo búsqueda ──────────────────────────────────────────────
    if buscar:
        k = normalizar(buscar)
        cnt = Counter()
        for f in decl:
            nm = f.get('entrada_trabajando') or ''
            if k in normalizar(nm):
                if entero(f.get('n_entradas_declaradas_aviso')) <= UMBRAL:
                    cnt[nm] += 1
                else:
                    cnt.setdefault(nm, 0)
        if not cnt:
            print(f"\n  Ningún nombre de carrera contiene «{buscar}».\n")
            return
        print(f"\n  Nombres que contienen «{buscar}»  "
              f"(avisos específicos que los declaran)\n")
        for nm, c in cnt.most_common():
            print(f"    {c:>5}  {nm}")
        print()
        return

    # ── resolver el nombre pedido ──────────────────────────────────
    objetivo = normalizar(nombre)
    exactos = {f['entrada_trabajando'] for f in decl
               if normalizar(f.get('entrada_trabajando')) == objetivo}
    if not exactos:
        cerca = sorted({f['entrada_trabajando'] for f in decl
                        if objetivo in normalizar(f.get('entrada_trabajando'))})
        print(f"\n  No hay ninguna carrera declarada que se llame "
              f"exactamente «{nombre}».")
        if cerca:
            print(f"  Quizás alguna de estas ({len(cerca)}):")
            for c in cerca[:15]:
                print(f"      {c}")
        print(f"\n  Probá  --buscar <texto>  para listar por coincidencia "
              f"parcial.\n")
        return

    ids_todos = {f['aviso_id'] for f in decl
                 if normalizar(f.get('entrada_trabajando')) == objetivo}
    ids_esp = {f['aviso_id'] for f in decl
               if normalizar(f.get('entrada_trabajando')) == objetivo
               and entero(f.get('n_entradas_declaradas_aviso')) <= UMBRAL}

    print("=" * 68)
    print(f"  {' / '.join(sorted(exactos))}")
    print("=" * 68)
    print(f"  avisos que la declaran : {len(ids_todos)}")
    print(f"    específicos          : {len(ids_esp)}   "
          f"(declaran ≤ {UMBRAL} carreras)")
    print(f"    genéricos            : {len(ids_todos) - len(ids_esp)}   "
          f"(excluidos de todo lo que sigue)")
    if not ids_esp:
        print("\n  Sin avisos específicos: solo aparece en avisos que "
              "tildan medio catálogo.\n")
        return

    # ── co-declaradas: la evidencia más fuerte ─────────────────────
    co = Counter()
    for f in decl:
        if f['aviso_id'] in ids_esp:
            otra = f.get('entrada_trabajando') or ''
            if normalizar(otra) != objetivo:
                co[otra] += 1
    tabla("CARRERAS CO-DECLARADAS — con qué la piden junto",
          co, len(ids_esp), n,
          "\n    (% sobre los avisos específicos de esta carrera)")
    if not co:
        print("\n  CARRERAS CO-DECLARADAS")
        print("    Ninguna: siempre se declara sola. Es una señal fuerte "
              "de que\n    el empleador tiene una carrera concreta en "
              "mente.")

    # ── datos del aviso: streaming, avisos.csv pesa decenas de MB ──
    campos = Counter(), Counter(), Counter(), Counter()
    niveles, cargos, empresas, areas = campos
    ejemplos = []
    with open(os.path.join(dir_maestras, 'avisos.csv'),
              encoding='utf-8-sig', newline='') as f:
        for a in csv.DictReader(f):
            if a['aviso_id'] not in ids_esp:
                continue
            niveles[a.get('nivel_academico') or ''] += 1
            cargos[a.get('titulo') or ''] += 1
            empresas[a.get('empresa_nombre')
                     or f"[confidencial {a.get('empresa_id')}]"] += 1
            for ar in (a.get('areas_scraping') or '').split('|'):
                if ar.strip():
                    areas[ar.strip()] += 1
            if len(ejemplos) < 8:
                ejemplos.append((a.get('titulo') or '',
                                 a.get('nivel_academico') or '',
                                 a.get('url') or ''))

    t = len(ids_esp)
    tabla("NIVEL ACADÉMICO — decide si hace falta nivel_condicion",
          niveles, t, n)
    tabla("CARGOS — qué trabajo es en realidad", cargos, t, n)
    tabla("EMPLEADORES", empresas, t, n)
    tabla("ÁREAS del monitor donde apareció", areas, t, n)

    print(f"\n  EJEMPLOS")
    for tit, niv, url in ejemplos:
        print(f"    {tit[:56]}")
        print(f"      {niv or '(sin nivel)'} · {url}")
    print("\n" + "=" * 68 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('nombre', nargs='?', default=None)
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--buscar', default=None,
                    help='lista nombres que contengan este texto')
    ap.add_argument('--n', type=int, default=12,
                    help='filas por sección (default 12)')
    a = ap.parse_args()
    if not a.nombre and not a.buscar:
        ap.error('dame un nombre de carrera, o --buscar <texto>')
    main(a.maestras, a.nombre, a.buscar, a.n)
