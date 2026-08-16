"""
Control de calidad sobre las maestras
======================================

No es análisis: es la lista de chequeos que hay que pasar **después de
cada consolidación**, siempre los mismos, para responder una sola
pregunta — ¿puedo confiar en estas maestras, y qué tengo que tener en
cuenta al usarlas?

Por eso es un script y no celdas de un notebook. Un cuaderno sirve
cuando cada paso depende de lo que viste en el anterior; esto corre
idéntico todos los meses. `mensual.sh` lo ejecuta solo al terminar de
consolidar, así que los chequeos no dependen de que alguien se acuerde.

  1. Umbral de genericidad   ¿la distribución sigue siendo bimodal?
  2. Avisos genéricos        ¿quiénes tildan media taxonomía?
  3. Concentración           ¿un empleador es el área entera?
  4. Deriva del catálogo     ¿quedaron términos sin mapear?
  5. Diagnóstico por término ¿cuáles traen ruido? (§7 pendiente 4)

  PANEL LONGITUDINAL         ¿el panel acumuló? ¿hay duraciones?

El panel va aparte a propósito: **no es un control, es el resultado.**
Es la variable que justifica que el monitor sea longitudinal. Hoy puede
estar vacío —hacen falta dos corridas separadas en el tiempo— y eso no
es un error, es que todavía no hay profundidad.

Solo stdlib: corre en cualquier lado sin instalar nada.

Uso:
  python control.py
  python control.py --maestras maestras
"""

import argparse, csv, os, re, sys, unicodedata
from collections import Counter, defaultdict

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30      # si no se puede importar, el valor documentado

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ANCHO = 64
linea = lambda c='═': print(c * ANCHO)


def normalizar(s):
    if not isinstance(s, str):
        return ''
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def tokens(s):
    """Tokens de más de 3 letras: los cortos ('en', 'de', 'y') no
    discriminan nada."""
    return {t for t in normalizar(s).split() if len(t) > 3}


def hay_prefijo(termino_tokens, texto):
    """¿Algún token del texto empieza con algún token del término?

    Imita cómo matchea el buscador del sitio, que es por prefijo y no por
    palabra completa: por eso "Derecho" trae avisos que dicen "derechos".
    Sin esto, el diagnóstico subestima la precisión del término."""
    tt = tokens(texto)
    return any(a.startswith(t) or t.startswith(a)
               for t in termino_tokens for a in tt)


def leer(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def entero(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def pct(x, b):
    return f"{x*100/b:.1f}%" if b else "-"


# ══════════════════════════════════════════════════════════
# 1 · UMBRAL DE GENERICIDAD
# ══════════════════════════════════════════════════════════

def bloque_umbral(avisos):
    print(f"\n── 1. Umbral de genericidad (UMBRAL_AVISO_GENERICO = {UMBRAL})")
    dist = Counter(entero(a.get('n_carreras_declaradas')) for a in avisos)

    chicos = sorted(v for v in dist if v <= UMBRAL)
    grandes = sorted(v for v in dist if v > UMBRAL)

    print(f"   valores hasta {UMBRAL}: "
          + ', '.join(f"{v}({dist[v]})" for v in chicos[:14])
          + (' …' if len(chicos) > 14 else ''))
    if not grandes:
        print(f"   por encima del umbral: ninguno")
        print(f"   ✓ no hay avisos genéricos en esta consolidación")
        return
    print(f"   por encima: " + ', '.join(f"{v}({dist[v]})" for v in grandes))

    # La distribución observada es bimodal con un hueco enorme: valores
    # legítimos hasta ~25, y después el salto a los que tildan medio
    # catálogo. Un valor apenas por encima del corte es sospechoso.
    sospechosos = [v for v in grandes if v < UMBRAL * 3]
    maximo_legitimo = max(chicos) if chicos else 0
    if sospechosos:
        print(f"   ⚠  hay avisos con {', '.join(map(str, sospechosos))} "
              f"carreras, cerca del corte.")
        print(f"      El umbral supone un hueco entre lo legítimo (máx "
              f"observado: {maximo_legitimo}) y lo genérico.")
        print(f"      Revisá esos avisos: puede ser un concurso "
              f"multidisciplinario real.")
    else:
        print(f"   ✓ el hueco se mantiene: máximo legítimo {maximo_legitimo}, "
              f"siguiente {min(grandes)}")


# ══════════════════════════════════════════════════════════
# 2 · AVISOS GENÉRICOS
# ══════════════════════════════════════════════════════════

def bloque_genericos(avisos):
    print(f"\n── 2. Avisos genéricos (declaran > {UMBRAL} carreras)")
    gen = [a for a in avisos
           if entero(a.get('n_carreras_declaradas')) > UMBRAL]
    if not gen:
        print("   ninguno")
        return
    print(f"   {len(gen)} de {len(avisos)} avisos ({pct(len(gen), len(avisos))})")
    print(f"   Aparecen en la búsqueda de CUALQUIER carrera. Excluilos de")
    print(f"   todo análisis por carrera: usá n_avisos_especificos.")
    por_emp = Counter(a.get('empresa_id') for a in gen)
    print(f"\n   {'avisos':>6}  {'empresa_id':<12} ejemplo de título")
    for eid, n in por_emp.most_common(8):
        t = next((a.get('titulo', '') for a in gen
                  if a.get('empresa_id') == eid), '')
        print(f"   {n:>6}  {str(eid):<12} {t[:38]}")


# ══════════════════════════════════════════════════════════
# 3 · CONCENTRACIÓN POR EMPLEADOR
# ══════════════════════════════════════════════════════════

def bloque_concentracion(avisos):
    print(f"\n── 3. Concentración por empleador")
    print(f"   Leer ANTES de cualquier agregado: el conteo de avisos mide")
    print(f"   publicación, no demanda. En Derecho un solo empleador fue el")
    print(f"   35% del área, con su boilerplate institucional.")

    def top(sub, etiqueta):
        c = Counter(a.get('empresa_id') for a in sub if a.get('empresa_id'))
        n = len(sub)
        if not n or not c:
            return
        t1 = c.most_common(1)[0][1]
        t3 = sum(v for _, v in c.most_common(3))
        t10 = sum(v for _, v in c.most_common(10))
        marca = '⚠' if t1 / n > 0.25 else ' '
        print(f"   {marca} {etiqueta:<28} n={n:>6}  "
              f"top1 {pct(t1,n):>6}  top3 {pct(t3,n):>6}  top10 {pct(t10,n):>6}")

    print(f"\n     {'ámbito':<28} {'avisos':>8}  {'top1':>11} {'top3':>11} {'top10':>11}")
    top(avisos, 'TODAS LAS ÁREAS')
    por_area = defaultdict(list)
    for a in avisos:
        for area in (a.get('areas_scraping') or '').split(' | '):
            if area:
                por_area[area].append(a)
    for area in sorted(por_area, key=lambda x: -len(por_area[x])):
        top(por_area[area], area[:28])


# ══════════════════════════════════════════════════════════
# 4 · DERIVA DEL CATÁLOGO
# ══════════════════════════════════════════════════════════

def bloque_deriva(avisos, aviso_termino):
    print(f"\n── 4. Deriva del catálogo (ruta A)")
    sin_map = sum(1 for a in avisos
                  if entero(a.get('n_terminos_sin_mapeo')) > 0)
    if aviso_termino is None:
        print("   aviso_termino.csv no existe — ¿consolidaste con la versión")
        print("   nueva de consolidar.py?")
        return
    huerfanos = sorted({f['termino_busqueda'] for f in aviso_termino
                        if str(f.get('mapeado')).lower() not in ('true', '1')})
    if not huerfanos and not sin_map:
        print(f"   ✓ los {len({f['termino_busqueda'] for f in aviso_termino})} "
              f"términos del crudo mapean contra el catálogo actual")
        return
    print(f"   ⚠  {len(huerfanos)} término(s) del crudo ya no están en el")
    print(f"      catálogo, y {sin_map} avisos quedaron sin mapeo.")
    print(f"      Pasa cuando se edita carreras_sies_2026.py después de una")
    print(f"      corrida. Los crudos viejos conservan el término anterior.")
    for t in huerfanos[:10]:
        print(f"        {t}")


# ══════════════════════════════════════════════════════════
# 5 · DIAGNÓSTICO POR TÉRMINO  (§7 pendiente 4)
# ══════════════════════════════════════════════════════════

def bloque_terminos(avisos, aviso_termino, aviso_carrera):
    print(f"\n── 5. Diagnóstico por término")
    if aviso_termino is None:
        print("   requiere aviso_termino.csv")
        return
    print(f"   El buscador matchea por prefijo sobre el CUERPO del aviso, así")
    print(f"   que un término que es palabra corriente arrastra ruido")
    print(f"   proporcional a su frecuencia en prosa de RR.HH. Los tres")
    print(f"   números juntos lo delatan; ninguno solo alcanza.")

    info = {a['aviso_id']: a for a in avisos}
    # carreras declaradas por aviso, solo de avisos específicos
    decl = defaultdict(set)
    if aviso_carrera:
        for f in aviso_carrera:
            if f.get('fuente') != 'declarada':
                continue
            if entero(f.get('n_carreras_declaradas_aviso')) > UMBRAL:
                continue
            decl[f['aviso_id']].add(f.get('carrera_trabajando') or '')

    por_term = defaultdict(list)
    for f in aviso_termino:
        por_term[f['termino_busqueda']].append(f['aviso_id'])

    filas = []
    for term, ids in por_term.items():
        tt = tokens(term)
        n = len(ids)
        if not n:
            filas.append((term, 0, None, None, None)); continue
        n_tit = sum(1 for i in ids
                    if hay_prefijo(tt, info.get(i, {}).get('titulo', '')))
        # Denominador según §7: todos los avisos del término SIN los
        # genéricos. No "los que declaran carreras" — eso infla el
        # porcentaje y no es lo que dice la especificación.
        espec = [i for i in ids
                 if entero(info.get(i, {}).get('n_carreras_declaradas')) <= UMBRAL]
        n_car = sum(1 for i in espec
                    if any(hay_prefijo(tt, c) for c in decl.get(i, ())))
        emp = Counter(info.get(i, {}).get('empresa_id') for i in ids
                      if info.get(i, {}).get('empresa_id'))
        top1 = emp.most_common(1)[0][1] / n if emp else 0
        filas.append((term, n, n_tit / n,
                      (n_car / len(espec)) if espec else None, top1))

    filas.sort(key=lambda r: -r[1])
    print(f"\n   {'término':<40} {'avisos':>7} {'títu':>6} {'carr':>6} {'top1':>6}")
    for term, n, ptit, pcar, top1 in filas:
        if n == 0:
            print(f"   {term[:40]:<40} {0:>7}   ——     ——     ——   "
                  f"← sin resultados")
            continue
        flag = ''
        if ptit is not None and ptit < 0.25 and (pcar is None or pcar < 0.25):
            flag = ' ⚠ ruido'
        elif top1 > 0.30:
            flag = ' ⚠ 1 empleador'
        pc = f"{pcar*100:5.1f}%" if pcar is not None else "   ——"
        print(f"   {term[:40]:<40} {n:>7} {ptit*100:5.1f}% {pc} "
              f"{top1*100:5.1f}%{flag}")

    print(f"\n   títu = el término aparece en el título del aviso")
    print(f"   carr = carrera declarada afín / avisos no genéricos del término")
    print(f"   top1 = share del empleador más frecuente")
    print(f"   Persistir un `estado_termino` a partir de esto sigue")
    print(f"   pendiente; hoy es un informe, no un registro.")


# ══════════════════════════════════════════════════════════
# PANEL LONGITUDINAL
# ══════════════════════════════════════════════════════════

def bloque_panel(avisos):
    linea()
    print("  PANEL LONGITUDINAL")
    linea()
    print("  No es un control: es lo que el monitor produce.")

    multi = sum(1 for a in avisos if entero(a.get('n_corridas_visto')) > 1)
    print(f"\n  avisos vistos en más de una corrida : {multi} de {len(avisos)}")

    cal = Counter(a.get('calidad_duracion') for a in avisos)
    print(f"\n  calidad de la duración — NO se deben mezclar")
    for k, etiqueta in (
            ('observada',     'medición real (PUBLICADA → DESACTIVADA)'),
            ('cota_superior', 'techo: ya estaba de baja al verla'),
            ('censurada',     'seguía viva en la última observación')):
        print(f"    {k:<14} {cal.get(k, 0):>7}   {etiqueta}")

    dur = sorted(entero(a.get('dias_publicado_hasta_baja'), -1)
                 for a in avisos
                 if a.get('calidad_duracion') == 'observada'
                 and a.get('dias_publicado_hasta_baja'))
    dur = [d for d in dur if d >= 0]
    if not dur:
        print(f"\n  Sin duraciones medidas todavía.")
        print(f"  Hacen falta dos corridas SEPARADAS EN EL TIEMPO sobre el")
        print(f"  mismo aviso. Dos corridas del mismo día no sirven: el")
        print(f"  panel gana profundidad con las semanas, no con más áreas.")
        return
    n = len(dur)
    print(f"\n  días publicado → baja   (solo las {n} observadas)")
    print(f"    mediana {dur[n//2]}  ·  p25 {dur[n//4]}  ·  "
          f"p75 {dur[3*n//4]}  ·  máx {dur[-1]}")


# ══════════════════════════════════════════════════════════

def main(dir_maestras):
    p = lambda n: os.path.join(dir_maestras, n)
    avisos = leer(p('avisos.csv'))
    if avisos is None:
        print(f"⛔  No existe {p('avisos.csv')}. Corré consolidar.py primero.")
        sys.exit(1)

    linea()
    print("  CONTROL DE CALIDAD — maestras")
    linea()
    print(f"  directorio : {os.path.abspath(dir_maestras)}")
    print(f"  avisos     : {len(avisos)}")

    bloque_umbral(avisos)
    bloque_genericos(avisos)
    bloque_concentracion(avisos)
    at = leer(p('aviso_termino.csv'))
    bloque_deriva(avisos, at)
    bloque_terminos(avisos, at, leer(p('aviso_carrera.csv')))

    print()
    bloque_panel(avisos)
    print()
    linea()
    print("  Siguiente: la cola de homologación es otro trabajo, a otro")
    print("  ritmo.  python homologar.py --maestras <dir>")
    linea()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    a = ap.parse_args()
    main(a.maestras)
