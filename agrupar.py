"""
Cómo se agrupan los programas, según el mercado
================================================

No dibuja la co-ocurrencia: la mide. Para cada par de programas
formativos calcula si aparecen juntos **más de lo que el azar
explicaría**, arma un agrupamiento jerárquico con esa señal, y lo
contrasta contra la clasificación ISCED-F.

La pregunta que contesta es: **¿el mercado agrupa las formaciones como
las agrupa la taxonomía oficial?** Donde coincide, ISCED describe algo
real. Donde no, hay un hallazgo.

LAS TRES TRAMPAS QUE ESTE ARCHIVO EVITA, Y POR QUÉ
  1. **Contar co-ocurrencias crudas mide frecuencia, no asociación.**
     `Administración de Empresas` aparece con todo porque aparece mucho.
     Por eso cada par lleva Jaccard (cuánto se solapan) y *lift* (cuánto
     más de lo esperado), y un test exacto de Fisher con corrección de
     Benjamini-Hochberg. Sin eso, el ranking es un ranking de tamaño.

  2. **Un empleador con una plantilla cuenta N veces una sola decisión.**
     Es la lección 8. Si una empresa publica cincuenta avisos con el
     mismo conjunto de tres programas, eso es UNA decisión, no cincuenta
     observaciones. Acá cada par (empresa, conjunto) cuenta una vez, y
     el informe muestra cuánto se achica la base al hacerlo.

  3. **Un aviso con un solo programa no informa nada sobre agrupamiento.**
     Es la mayoría. La base real del análisis son los avisos que piden
     dos o más, y la cifra va arriba de todo.

QUÉ NO HACE
  No decide cuántos grupos hay. Corta el dendrograma en varios valores
  de k y muestra la concordancia con ISCED en todos, para que se vea que
  el resultado no está elegido a dedo. Elegir el k que maximiza la
  concordancia y después reportar esa concordancia como evidencia sería
  circular.

Uso:
  ./agrupar.sh
  python agrupar.py --maestras <dir> --salida <archivo.html>
"""

import argparse, csv, html, itertools, json, math, os, sys
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

REPO = os.path.dirname(os.path.abspath(__file__))

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30

# Un programa entra al agrupamiento si aparece en al menos esta cantidad
# de observaciones informativas. Con menos, su fila de distancias es casi
# toda 1 y el agrupamiento lo cuelga de cualquier lado.
MIN_OBS = 3
KS = list(range(2, 21))


# ══════════════════════════════════════════════════════════════════
# ESTADÍSTICA
# ══════════════════════════════════════════════════════════════════

def log_c(n, k):
    """log del coeficiente binomial, por lgamma: con N de miles, calcular
    los enteros exactos y después dividirlos es lento y no hace falta."""
    if k < 0 or k > n:
        return float('-inf')
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1))


def fisher_derecha(a, b, c, d):
    """p de una cola del test exacto de Fisher: probabilidad de observar
    `a` o más en la celda superior izquierda, dados los marginales.

    Acá `a` = avisos con los dos programas, y la cola derecha responde
    exactamente la pregunta que importa: ¿aparecen juntos más de lo
    esperable si fueran independientes?
    """
    n = a + b + c + d
    fila, col = a + b, a + c
    tope = min(fila, col)
    base = log_c(n, col)
    total = 0.0
    for x in range(a, tope + 1):
        lp = log_c(fila, x) + log_c(n - fila, col - x) - base
        total += math.exp(lp)
    return min(1.0, total)


def bh(pvals):
    """Benjamini-Hochberg: convierte p en q (FDR). Con miles de pares,
    mirar los p sin corregir garantiza falsos hallazgos."""
    m = len(pvals)
    orden = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    menor = 1.0
    for pos in range(m - 1, -1, -1):
        i = orden[pos]
        menor = min(menor, pvals[i] * m / (pos + 1))
        q[i] = menor
    return q


def dendrograma(items, dist):
    """Agrupamiento jerárquico aglomerativo con enlace promedio (UPGMA).

    Devuelve la lista de fusiones [(izq, der, altura, tamaño)]. Enlace
    promedio y no simple porque el simple encadena: un solo par cercano
    pega dos grupos que no tienen nada que ver.

    Implementación directa O(n³); con 200 programas corre en un
    parpadeo y se lee entera.
    """
    n = len(items)
    activos = {i: [i] for i in range(n)}
    nodos = {i: items[i] for i in range(n)}
    d = {(i, j): dist(items[i], items[j])
         for i in range(n) for j in range(i + 1, n)}
    sig = n
    fusiones = []
    while len(activos) > 1:
        # el par más cercano, con desempate estable por índice
        par = min(((i, j) for i in activos for j in activos if i < j),
                  key=lambda k: (d[k], k))
        i, j = par
        h = d[par]
        miembros = activos[i] + activos[j]
        for k in list(activos):
            if k in (i, j):
                continue
            ni, nj = len(activos[i]), len(activos[j])
            a = d[(min(i, k), max(i, k))]
            b = d[(min(j, k), max(j, k))]
            d[(min(sig, k), max(sig, k))] = (a * ni + b * nj) / (ni + nj)
        del activos[i], activos[j]
        activos[sig] = miembros
        fusiones.append((i, j, h, len(miembros)))
        nodos[sig] = None
        sig += 1
    return fusiones


def cortar(fusiones, n, k):
    """Los k grupos que resultan de cortar el dendrograma."""
    padre = {}
    for paso, (i, j, _, _) in enumerate(fusiones):
        if paso >= n - k:
            break
        padre[i] = padre[j] = n + paso
    def raiz(x):
        while x in padre:
            x = padre[x]
        return x
    grupos = defaultdict(list)
    for h in range(n):
        grupos[raiz(h)].append(h)
    return list(grupos.values())


def ari(a, b):
    """Índice de Rand ajustado entre dos particiones (listas de etiquetas).

    Ajustado —y no el Rand crudo— porque dos particiones al azar ya
    coinciden bastante: el crudo da números altos que no significan nada.
    ARI vale 0 en el azar y 1 en la coincidencia perfecta.
    """
    n = len(a)
    if n < 2:
        return float('nan')
    tabla = Counter(zip(a, b))
    fa, fb = Counter(a), Counter(b)
    c2 = lambda x: x * (x - 1) / 2
    suma = sum(c2(v) for v in tabla.values())
    sa = sum(c2(v) for v in fa.values())
    sb = sum(c2(v) for v in fb.values())
    esperado = sa * sb / c2(n)
    maximo = (sa + sb) / 2
    return (suma - esperado) / (maximo - esperado) if maximo != esperado \
        else float('nan')


# ══════════════════════════════════════════════════════════════════
# DATOS
# ══════════════════════════════════════════════════════════════════

def entero(v, d=0):
    try:
        return int(str(v).strip() or d)
    except (TypeError, ValueError):
        return d


def leer(path, obligatorio=True):
    if not os.path.exists(path):
        if obligatorio:
            print(f"⛔  No existe {path}")
            sys.exit(1)
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def preparar(dir_maestras):
    M = lambda n: os.path.join(dir_maestras, n)
    if not os.path.exists(M('aviso_programa.csv')):
        print("⛔  No existe aviso_programa.csv — corré ./procesar.sh\n")
        sys.exit(1)

    filas = [r for r in leer(M('aviso_programa.csv'))
             if r['tipo_entrada'] == 'programa_propio'
             and entero(r.get('n_entradas_declaradas_aviso')) <= UMBRAL
             and r.get('atribucion_multiple') != 'True']
    empresa = {r['aviso_id']: (r.get('empresa_id') or 's/e')
               for r in leer(M('avisos.csv'))}
    campo = {}
    for r in filas:
        campo[r['programa_propio']] = (r.get('isced_estrecho_cod') or '',
                                       r.get('area_sies') or '')

    por_aviso = defaultdict(set)
    for r in filas:
        por_aviso[r['aviso_id']].add(r['programa_propio'])

    con_uno = sum(1 for v in por_aviso.values() if len(v) == 1)
    multi = {a: v for a, v in por_aviso.items() if len(v) > 1}

    # Lección 8: un empleador que repite su plantilla tomó UNA decisión.
    vistos, obs = set(), []
    for a, v in sorted(multi.items()):
        clave = (empresa.get(a, 's/e'), frozenset(v))
        if clave in vistos:
            continue
        vistos.add(clave)
        obs.append(v)

    return {
        'conjuntos': obs,
        'n_con_programa': len(por_aviso),
        'n_con_uno': con_uno,
        'n_multi': len(multi),
        'n_dedup': len(obs),
        'campo': campo,
    }


def asociar(conjuntos):
    """Frecuencias, pares y la estadística de cada par."""
    N = len(conjuntos)
    freq = Counter()
    pares = Counter()
    for v in conjuntos:
        for p in v:
            freq[p] += 1
        for a, b in itertools.combinations(sorted(v), 2):
            pares[(a, b)] += 1

    filas = []
    for (a, b), n_ab in pares.items():
        na, nb = freq[a], freq[b]
        # tabla 2×2 sobre las observaciones (conjuntos deduplicados)
        c11 = n_ab
        c10, c01 = na - n_ab, nb - n_ab
        c00 = N - c11 - c10 - c01
        if c00 < 0:
            continue
        jac = n_ab / (na + nb - n_ab)
        esperado = na * nb / N
        filas.append({
            'a': a, 'b': b, 'n': n_ab, 'na': na, 'nb': nb,
            'jaccard': jac,
            'lift': (n_ab / esperado) if esperado else float('inf'),
            'p': fisher_derecha(c11, c10, c01, c00),
        })
    if filas:
        qs = bh([f['p'] for f in filas])
        for f, q in zip(filas, qs):
            f['q'] = q
    filas.sort(key=lambda f: (f['q'], -f['n'], f['a'], f['b']))
    return filas, freq, N


def analizar(dir_maestras):
    base = preparar(dir_maestras)
    filas, freq, N = asociar(base['conjuntos'])

    # ── agrupamiento ──────────────────────────────────────────────
    progs = sorted(p for p, f in freq.items() if f >= MIN_OBS)
    jac = {}
    for f in filas:
        jac[(f['a'], f['b'])] = f['jaccard']
    def dist(x, y):
        k = (x, y) if x < y else (y, x)
        return 1 - jac.get(k, 0.0)

    resultado = {'base': base, 'pares': filas, 'N': N,
                 'freq': dict(freq), 'progs': progs}
    if len(progs) < 4:
        resultado['fusiones'] = []
        return resultado

    fus = dendrograma(progs, dist)
    resultado['fusiones'] = fus

    # ── concordancia con ISCED, en TODOS los k ────────────────────
    # Elegir el k que maximiza la concordancia y después reportar esa
    # concordancia como evidencia sería circular. Se reportan todos.
    campo = base['campo']
    ref = [campo.get(p, ('', ''))[0] for p in progs]
    curva = []
    for k in KS:
        if k > len(progs):
            break
        grupos = cortar(fus, len(progs), k)
        etiq = [0] * len(progs)
        for gi, g in enumerate(grupos):
            for x in g:
                etiq[x] = gi
        curva.append({'k': k, 'ari': ari(etiq, ref),
                      'grupos': [[progs[x] for x in g] for g in grupos]})

    # k por codo: el salto más grande entre alturas de fusión, PERO
    # restringido a un rango razonable. Sin la restricción gana siempre
    # una de las últimas fusiones —son las más altas— y el «codo» sale
    # en k = n−1, o sea casi nada agrupado: un corte que no agrupa.
    alturas = [h for _, _, h, _ in fus]
    n_p = len(progs)
    k_max = max(2, min(20, n_p // 2))
    saltos = [(alturas[i + 1] - alturas[i], n_p - i - 1)
              for i in range(len(alturas) - 1)
              if 2 <= n_p - i - 1 <= k_max]
    k_codo = max(saltos)[1] if saltos else 2
    resultado['curva'] = curva
    resultado['k_codo'] = k_codo

    # ── dónde el mercado y la taxonomía no coinciden ──────────────
    sig = [f for f in filas if f['q'] < 0.05]
    resultado['cruzan'] = [f for f in sig
                           if campo.get(f['a'], ('', ''))[0]
                           != campo.get(f['b'], ('', ''))[0]]
    juntos = {(f['a'], f['b']) for f in filas}
    mismo_campo = []
    por_campo = defaultdict(list)
    for p in progs:
        c = campo.get(p, ('', ''))[0]
        if c:
            por_campo[c].append(p)
    for c, ps in sorted(por_campo.items()):
        for a, b in itertools.combinations(sorted(ps), 2):
            if (a, b) not in juntos:
                mismo_campo.append({'campo': c, 'a': a, 'b': b,
                                    'na': freq[a], 'nb': freq[b]})
    resultado['nunca_juntos'] = sorted(
        mismo_campo, key=lambda r: -(r['na'] + r['nb']))
    resultado['significativos'] = sig
    return resultado


def informe(r):
    b = r['base']
    print("=" * 68)
    print("  CÓMO SE AGRUPAN LOS PROGRAMAS")
    print("=" * 68)
    print(f"  avisos específicos con al menos un programa : {b['n_con_programa']}")
    print(f"    con UN solo programa (no informan)       : {b['n_con_uno']}")
    print(f"    con dos o más — la base del análisis     : {b['n_multi']}")
    print(f"  tras deduplicar (empresa × conjunto)       : {b['n_dedup']}")
    if b['n_multi']:
        perdido = 100 - b['n_dedup'] * 100 / b['n_multi']
        print(f"    la deduplicación se lleva el {perdido:.0f}%: eran "
              f"plantillas repetidas")
    if b['n_dedup'] < 30:
        print("\n  ⚠  Con menos de 30 observaciones el agrupamiento no dice")
        print("     gran cosa. Los números salen igual, pero leelos como")
        print("     exploración y no como resultado.")

    print(f"\n  pares de programas observados : {len(r['pares'])}")
    print(f"  significativos (q < 0,05)     : {len(r.get('significativos', []))}")
    print(f"  programas en el agrupamiento  : {len(r['progs'])} "
          f"(aparecen en ≥{MIN_OBS} observaciones)")

    rep = [f for f in r['pares'] if f['n'] >= 2]
    print(f"  pares vistos más de una vez   : {len(rep)}  "
          f"(los de n=1 no son evidencia)")
    if rep:
        print("\n  LOS PARES MÁS ASOCIADOS  (n = observaciones juntas)")
        print(f"     {'n':>3} {'lift':>6} {'jacc':>5} {'q':>8}  par")
        for f in rep[:12]:
            print(f"     {f['n']:>3} {f['lift']:>6.1f} {f['jaccard']:>5.2f} "
                  f"{f['q']:>8.4f}  {f['a'][:26]} + {f['b'][:26]}")

    if r.get('curva'):
        print("\n  CONCORDANCIA CON EL CAMPO ISCED ESTRECHO  (ARI)")
        print("     0 = como el azar · 1 = idéntica")
        for c in r['curva']:
            marca = '  ← codo' if c['k'] == r['k_codo'] else ''
            print(f"     k={c['k']:>3}   ARI = {c['ari']:.3f}{marca}")

    if r.get('cruzan'):
        print(f"\n  PARES ASOCIADOS QUE CRUZAN CAMPOS ISCED: "
              f"{len(r['cruzan'])}")
        print("     el mercado los pide juntos, la taxonomía los separa")
        for f in r['cruzan'][:10]:
            print(f"     {f['n']:>3}  {f['a'][:30]} + {f['b'][:30]}")
    print("=" * 68 + chr(10))


# ══════════════════════════════════════════════════════════════════
# LA PÁGINA
# ══════════════════════════════════════════════════════════════════

def svg_dendro(progs, fus, k, campo):
    """Dendrograma clásico: hojas a la izquierda, fusiones a la derecha,
    la altura de cada fusión es la distancia a la que se unieron."""
    n = len(progs)
    if n < 2:
        return '<p class="vacio">Muy pocos programas para agrupar.</p>'
    hijos = {}
    for paso, (i, j, h, _) in enumerate(fus):
        hijos[n + paso] = (i, j, h)

    orden = []
    def bajar(x):
        if x < n:
            orden.append(x); return
        i, j, _ = hijos[x]
        bajar(i); bajar(j)
    bajar(n + len(fus) - 1)
    fila = {h: k2 for k2, h in enumerate(orden)}

    # qué grupo le toca a cada hoja con el corte elegido
    grupo = {}
    for gi, g in enumerate(cortar(fus, n, min(k, n))):
        for x in g:
            grupo[x] = gi

    ALTO, PAD, ANCHO_R, ETQ = 17, 14, 300, 300
    H = PAD * 2 + ALTO * n
    W = ETQ + ANCHO_R + 30
    hmax = max([h for _, _, h, _ in fus] + [1e-9])
    px = lambda h: ETQ + 16 + (h / hmax) * ANCHO_R

    pos = {}
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Dendrograma '
         f'de {n} programas agrupados por co-ocurrencia">']
    for h in range(n):
        y = PAD + ALTO * fila[h] + ALTO / 2
        pos[h] = (ETQ + 12, y)
        col = f'var(--g{grupo.get(h, 0) % 8})'
        p.append(f'<text class="hoja" x="{ETQ}" y="{y + 3:.1f}" '
                 f'text-anchor="end" fill="{col}">'
                 f'{html.escape(progs[h][:44])}</text>')
    for paso, (i, j, h, _) in enumerate(fus):
        (x1, y1), (x2, y2) = pos[i], pos[j]
        x = px(h)
        mismo = grupo.get(i) is not None and grupo.get(i) == grupo.get(j)
        col = f'var(--g{grupo[i] % 8})' if mismo else 'var(--line)'
        p.append(f'<path class="rama" stroke="{col}" d="M{x1:.1f},{y1:.1f} '
                 f'H{x:.1f} V{y2:.1f} H{x2:.1f}"/>')
        pos[n + paso] = (x, (y1 + y2) / 2)
        if mismo:
            grupo[n + paso] = grupo[i]
    p.append('</svg>')
    return chr(10).join(p)


def svg_curva(curva, k_codo):
    if not curva:
        return ''
    W, H, M = 560, 190, 34
    ks = [c['k'] for c in curva]
    vs = [0 if c['ari'] != c['ari'] else c['ari'] for c in curva]
    lo, hi = min(vs + [0]), max(vs + [0.2])
    fx = lambda k: M + (k - ks[0]) / max(1, ks[-1] - ks[0]) * (W - M - 14)
    fy = lambda v: H - 24 - (v - lo) / max(1e-9, hi - lo) * (H - 48)
    p = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Concordancia '
         f'con ISCED según el número de grupos">']
    p.append(f'<line class="eje" x1="{M}" y1="{fy(0):.1f}" x2="{W - 14}" '
             f'y2="{fy(0):.1f}"/>')
    p.append(f'<text class="ejet" x="{M - 6}" y="{fy(0) + 3:.1f}" '
             f'text-anchor="end">0</text>')
    d = ' '.join(f'{"M" if i == 0 else "L"}{fx(c["k"]):.1f},'
                 f'{fy(vs[i]):.1f}' for i, c in enumerate(curva))
    p.append(f'<path class="curva" d="{d}"/>')
    for i, c in enumerate(curva):
        r = 4 if c['k'] == k_codo else 2.5
        p.append(f'<circle class="pt{" codo" if c["k"] == k_codo else ""}" '
                 f'cx="{fx(c["k"]):.1f}" cy="{fy(vs[i]):.1f}" r="{r}"/>')
        if c['k'] % 2 == 0 or c['k'] == k_codo:
            p.append(f'<text class="ejet" x="{fx(c["k"]):.1f}" y="{H - 6}" '
                     f'text-anchor="middle">{c["k"]}</text>')
    p.append(f'<text class="ejet" x="{M - 6}" y="{fy(hi) + 3:.1f}" '
             f'text-anchor="end">{hi:.2f}</text>')
    p.append('</svg>')
    return chr(10).join(p)


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cómo se agrupan los programas — Monitor Mercado Laboral</title>
<style>
:root{
  --ground:#E9ECEA; --surface:#F6F8F6; --surface-2:#FFFFFF; --ink:#16211E;
  --muted:#4E5C58; --line:#C3CCC8; --line-soft:#D8DFDB; --accent:#0E7A80;
  --warn:#A8384E; --warn-wash:#F6E4E8;
  --g0:#0E7A80; --g1:#8A5A12; --g2:#3C5EA8; --g3:#7A3D6B;
  --g4:#2F6B46; --g5:#A8384E; --g6:#55606B; --g7:#8A6D1F;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --display:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0E1513; --surface:#16201D; --surface-2:#1B2724; --ink:#DCE5E1;
  --muted:#869993; --line:#2E3D39; --line-soft:#22302C; --accent:#4CB8C0;
  --warn:#E4788C; --warn-wash:#33191F;
  --g0:#4CB8C0; --g1:#E2B464; --g2:#8FA9E8; --g3:#C594B6;
  --g4:#8FD0A8; --g5:#E4788C; --g6:#9FAAB4; --g7:#D2B662;
}}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);
 font-size:16px;line-height:1.62;margin:0;padding:0 20px 90px;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto}
header{padding:60px 0 28px;border-bottom:1px solid var(--line);
 margin-bottom:30px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--muted);margin:0 0 16px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(30px,5vw,46px);
 line-height:1.08;letter-spacing:-.015em;margin:0 0 18px;text-wrap:balance}
.lede{font-size:17.5px;color:var(--muted);margin:0;max-width:62ch}
h2{font-family:var(--display);font-weight:600;font-size:23px;
 margin:48px 0 8px;letter-spacing:-.01em}
p{margin:0 0 14px;max-width:68ch}
code{font-family:var(--mono);font-size:.88em;background:var(--surface);
 border:1px solid var(--line-soft);border-radius:3px;padding:.1em .34em}
.cifras{display:flex;flex-wrap:wrap;gap:8px 30px;margin:22px 0 0;
 font-variant-numeric:tabular-nums}
.cifra b{display:block;font:600 25px/1 var(--display)}
.cifra span{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;
 text-transform:uppercase;color:var(--muted)}
.aviso{border-left:3px solid var(--warn);background:var(--warn-wash);
 padding:14px 18px;margin:20px 0;border-radius:0 3px 3px 0;font-size:14.5px}
.caja{background:var(--surface);border:1px solid var(--line);
 border-radius:4px;padding:16px;margin:18px 0;overflow-x:auto}
svg{display:block;width:100%;height:auto}
.hoja{font-family:var(--mono);font-size:9.5px}
.rama{fill:none;stroke-width:1.2}
.curva{fill:none;stroke:var(--accent);stroke-width:1.8}
.pt{fill:var(--accent)}.pt.codo{fill:var(--warn)}
.eje{stroke:var(--line);stroke-width:1}
.ejet{font-family:var(--mono);font-size:9px;fill:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:8px}
th,td{text-align:left;padding:6px 10px 6px 0;
 border-bottom:1px solid var(--line-soft);vertical-align:top}
th{font-family:var(--mono);font-size:10px;letter-spacing:.09em;
 text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--line)}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;
 font-family:var(--mono);font-size:12px}
.vacio{color:var(--muted);font-size:14px}
.leyenda{font-family:var(--mono);font-size:11px;color:var(--muted);
 margin-top:10px}
footer{border-top:1px solid var(--line);padding-top:20px;margin-top:56px;
 font-family:var(--mono);font-size:12px;color:var(--muted)}
</style></head><body><div class="wrap">
<header>
  <p class="eyebrow">Monitor Mercado Laboral Chile</p>
  <h1>Cómo se agrupan los programas</h1>
  <p class="lede">Qué formaciones pide el mercado juntas más de lo que el
  azar explicaría, cómo se agrupan si se las deja agruparse solas, y
  cuánto se parece ese agrupamiento a la clasificación oficial.</p>
  <div class="cifras">__CIFRAS__</div>
</header>
__AVISO__

<h2>La base, y por qué es más chica de lo que parece</h2>
<p>Un aviso que pide <b>un solo</b> programa no dice nada sobre
agrupamiento: la base real son los que piden dos o más. Y un empleador
que repite su plantilla tomó <b>una</b> decisión, no cincuenta, así que
cada par (empresa, conjunto) cuenta una sola vez.</p>
__BASE__

<h2>Los pares asociados</h2>
<p>Contar co-ocurrencias crudas mide frecuencia, no asociación:
<code>Administración de Empresas</code> aparece con todo porque aparece
mucho. Por eso van tres medidas. <b>Jaccard</b> es cuánto se solapan;
<b>lift</b> es cuántas veces más de lo esperado si fueran independientes;
<b>q</b> es el p del test exacto de Fisher corregido por
Benjamini-Hochberg — con cientos de pares, mirar el p sin corregir
garantiza hallazgos falsos.</p>
__PARES__

<h2>El agrupamiento</h2>
<p>Enlace promedio sobre la distancia <code>1 − Jaccard</code>. Promedio
y no simple porque el simple encadena: un solo par cercano pega dos
grupos que no tienen nada que ver. El color marca los grupos al cortar
en k = __KCODO__, que es donde el dendrograma da su salto más grande.</p>
<div class="caja">__DENDRO__</div>

<h2>¿Coincide con ISCED?</h2>
<p>El índice de Rand ajustado compara el agrupamiento con el campo
estrecho ISCED-F: <b>0 es lo que daría el azar</b>, 1 es coincidencia
perfecta. Se muestra en todos los cortes a propósito — elegir el k que
maximiza la concordancia y después reportar esa concordancia como
evidencia sería circular.</p>
<div class="caja">__CURVA__</div>
__CURVANOTA__

<h2>Donde el mercado y la taxonomía no coinciden</h2>
<p>Pares asociados de forma significativa cuyos programas están en
campos ISCED distintos. Son los casos donde el empleador junta lo que la
clasificación separa.</p>
__CRUZAN__

<footer>Generado por <code>agrupar.py</code> desde
<code>aviso_programa.csv</code> · __DIR__</footer>
</div></body></html>
"""


def pagina(r, dir_maestras):
    b = r['base']
    esc = html.escape
    cif = [('observaciones', b['n_dedup']),
           ('pares', len(r['pares'])),
           ('significativos', len(r.get('significativos', []))),
           ('programas', len(r['progs']))]
    cifras = ''.join(f'<div class="cifra"><b>{v}</b><span>{k}</span></div>'
                     for k, v in cif)

    aviso = ''
    if b['n_dedup'] < 40:
        aviso = (f'<div class="aviso"><b>Base chica: {b["n_dedup"]} '
                 f'observaciones.</b> Los números salen igual, pero con '
                 f'esta cantidad el agrupamiento es exploración, no '
                 f'resultado. Un par que aparece dos veces puede ser '
                 f'casualidad.</div>')

    perdido = (100 - b['n_dedup'] * 100 / b['n_multi']) if b['n_multi'] else 0
    base = (f'<table><tr><th>etapa</th><th>avisos</th></tr>'
            f'<tr><td>con al menos un programa</td>'
            f'<td class="n">{b["n_con_programa"]}</td></tr>'
            f'<tr><td>con un solo programa — no informan</td>'
            f'<td class="n">−{b["n_con_uno"]}</td></tr>'
            f'<tr><td><b>con dos o más</b></td>'
            f'<td class="n"><b>{b["n_multi"]}</b></td></tr>'
            f'<tr><td>tras deduplicar (empresa × conjunto)</td>'
            f'<td class="n">{b["n_dedup"]}</td></tr></table>'
            f'<p class="leyenda">la deduplicación se lleva el '
            f'{perdido:.0f}% — eran plantillas repetidas</p>')

    # Un par visto UNA vez no es evidencia de nada: su Jaccard da 1,00 y
    # su lift es el máximo posible, y las dos cosas son artefactos de que
    # los dos programas aparecen una sola vez. Se cuentan aparte.
    repetidos = [f for f in r['pares'] if f['n'] >= 2]
    unicos = len(r['pares']) - len(repetidos)
    if repetidos:
        fs = repetidos[:40]
        pares = ('<table><tr><th>par</th><th>n</th><th>jaccard</th>'
                 '<th>lift</th><th>q</th></tr>' + ''.join(
                     f'<tr><td>{esc(f["a"])} <span style="color:var(--muted)">'
                     f'+</span> {esc(f["b"])}</td>'
                     f'<td class="n">{f["n"]}</td>'
                     f'<td class="n">{f["jaccard"]:.2f}</td>'
                     f'<td class="n">{f["lift"]:.1f}</td>'
                     f'<td class="n">{f["q"]:.4f}</td></tr>' for f in fs)
                 + '</table>')
        if len(repetidos) > 40:
            pares += (f'<p class="leyenda">… y {len(repetidos) - 40} pares '
                      f'más con n ≥ 2</p>')
        if unicos:
            pares += (f'<p class="leyenda">Quedan afuera {unicos} pares '
                      f'vistos UNA sola vez. No son evidencia: su Jaccard '
                      f'da 1,00 y su lift el máximo posible solo porque '
                      f'los dos programas aparecen una vez.</p>')
    else:
        pares = (f'<p class="vacio">Ningún par se repitió. Los '
                 f'{unicos} pares observados aparecen una sola vez cada '
                 f'uno, así que no hay nada que medir.</p>')

    k = r.get('k_codo', 2)
    dendro = svg_dendro(r['progs'], r['fusiones'], k, b['campo']) \
        if r['fusiones'] else '<p class="vacio">Muy pocos programas.</p>'
    curva = svg_curva(r.get('curva', []), k)

    cn = ''
    if r.get('curva'):
        mejor = max(r['curva'], key=lambda c: -9 if c['ari'] != c['ari']
                    else c['ari'])
        cn = (f'<p>El máximo está en <b>k = {mejor["k"]}</b>, con '
              f'<b>ARI = {mejor["ari"]:.3f}</b>. ')
        cn += ('Con esa cifra el agrupamiento del mercado y la taxonomía '
               'apenas se parecen: el mercado no reproduce ISCED.</p>'
               if mejor['ari'] < 0.2 else
               'Es una concordancia apreciable: la taxonomía describe algo '
               'que el mercado también hace.</p>')

    if r.get('cruzan'):
        cruzan = ('<table><tr><th>par</th><th>campos ISCED</th><th>n</th>'
                  '<th>q</th></tr>' + ''.join(
                      f'<tr><td>{esc(f["a"])} + {esc(f["b"])}</td>'
                      f'<td class="n">{esc(b["campo"].get(f["a"], ("", ""))[0])}'
                      f' ≠ {esc(b["campo"].get(f["b"], ("", ""))[0])}</td>'
                      f'<td class="n">{f["n"]}</td>'
                      f'<td class="n">{f["q"]:.4f}</td></tr>'
                      for f in r['cruzan'][:25]) + '</table>')
    else:
        cruzan = ('<p class="vacio">Ninguno: todos los pares '
                  'significativos caen dentro del mismo campo ISCED. Con '
                  'una base chica eso es más falta de potencia que '
                  'acuerdo.</p>')

    return (PAGINA
            .replace('__CIFRAS__', cifras).replace('__AVISO__', aviso)
            .replace('__BASE__', base).replace('__PARES__', pares)
            .replace('__DENDRO__', dendro).replace('__CURVA__', curva)
            .replace('__CURVANOTA__', cn).replace('__CRUZAN__', cruzan)
            .replace('__KCODO__', str(k))
            .replace('__DIR__', esc(os.path.abspath(dir_maestras))))


def main(dir_maestras, salida):
    r = analizar(dir_maestras)
    informe(r)
    os.makedirs(os.path.dirname(os.path.abspath(salida)) or '.', exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(pagina(r, dir_maestras))
    print(f"  Archivo: {os.path.abspath(salida)}" + chr(10))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--salida', default='agrupamiento.html')
    a = ap.parse_args()
    main(a.maestras, a.salida)
