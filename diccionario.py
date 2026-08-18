"""
Diccionario de variables: lo que hay, lo que falta y lo que sobra
=================================================================

Lee los datos **reales** —las maestras y el crudo—, los cruza con las
glosas de `glosario.py` y los esquemas declarados en `consolidar.py`, y
emite `DICCIONARIO.md`.

POR QUÉ GENERARLO Y NO ESCRIBIRLO
  Un diccionario escrito a mano se desincroniza en silencio. Si mañana
  `consolidar.py` agrega una columna, un documento estático simplemente
  no la menciona y nada avisa: el lector cree que la lista está
  completa. Es la lección 10 aplicada a la documentación — el hueco
  tiene que verse.

TRES ESTADOS POR COLUMNA
  descrita         está en los datos y tiene glosa
  SIN DOCUMENTAR   está en los datos y nadie escribió qué es
  HUÉRFANA         hay glosa pero la columna ya no existe

Y TRES ORÍGENES
  código      declarada en el esquema de consolidar.py / homologar.py
  manual      no está en el esquema pero sí en el CSV. En las tablas que
              preservan columnas manuales esto es la función, no un
              error: es el trabajo de enriquecimiento a mano.
  ⚠ ausente   está en el esquema y no en el CSV. Eso sí es deriva.

RELLENO
  Porcentaje de filas con valor no vacío. Es lo que distingue una
  columna viva de un campo muerto sin tener que abrir los datos.

Uso:
  python diccionario.py
  python diccionario.py --maestras <dir> --crudo <dir>
  python diccionario.py --muestra 2000      # limita líneas por crudo
  python diccionario.py --salida /otro/DICCIONARIO.md
"""

import argparse, csv, glob, json, os, sys
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# ── esquemas declarados en el código ──────────────────────────────
# Import blando: sin esto no se puede distinguir "columna del código" de
# "columna manual", así que se avisa fuerte en vez de mentir.
ESQUEMAS, FALTA_ESQUEMA = {}, []
try:
    import consolidar as C
    ESQUEMAS.update({
        'avisos.csv':            C.COLS_AVISOS,
        'aviso_entrada.csv':     C.COLS_AVISO_ENTRADA,
        'aviso_termino.csv':     C.COLS_AVISO_TERMINO,
        'aviso_habilidad.csv':   C.COLS_AVISO_HABILIDAD,
        'aviso_institucion.csv': C.COLS_AVISO_INSTITUCION,
        'aviso_programa.csv':    C.COLS_AVISO_PROGRAMA,
        'empresas.csv':          C.COLS_EMPRESAS,
        'entradas_trabajando.csv': C.COLS_ENTRADAS,
        'instituciones.csv':     C.COLS_INSTITUCIONES,
    })
except Exception as e:
    FALTA_ESQUEMA.append(f'consolidar.py ({e})')

try:
    import homologar as H
    ESQUEMAS['homologacion_carreras.csv'] = H.COLUMNAS
except Exception as e:
    FALTA_ESQUEMA.append(f'homologar.py ({e})')

try:
    from glosario import GLOSAS, TABLAS, CON_COLUMNAS_MANUALES
except ImportError as e:
    print(f"⛔  No pude importar glosario.py: {e}")
    print("    Corré esto desde el repo, o con PYTHONPATH apuntando ahí.")
    sys.exit(1)

# Orden de presentación: las tablas grandes primero, las de apoyo después.
# El orden y la lista salen de `glosario.TABLAS`: una tabla nueva se
# declara en un solo lugar. Escrita a mano acá, agregar una maestra
# obligaba a tres ediciones y la tercera se olvidaba — que es cómo
# `aviso_programa.csv` quedó fuera del diccionario la primera vez.
ORDEN = list(TABLAS) or ['avisos.csv']


def leer_maestra(path):
    """(columnas, n_filas, {columna: n_no_vacíos}, encabezados_sucios).

    Streaming: estas tablas llegan a decenas de MB y no hace falta
    tenerlas en RAM.

    Los nombres de columna se limpian de espacios al borde. Un espacio
    ahí nunca significa nada, pero hace que `n_avisos` y `n_avisos ` se
    vean como dos columnas distintas y dispara una alarma de deriva
    falsa. Se limpia y se informa: `encabezados_sucios` lleva los que
    hubo que tocar, para que el arreglo no sea silencioso.
    """
    with open(path, encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        crudos = list(lector.fieldnames or [])
        cols = [c.strip() for c in crudos]
        sucios = [c for c, l in zip(crudos, cols) if c != l]
        llenos = dict.fromkeys(cols, 0)
        n = 0
        for fila in lector:
            n += 1
            for orig, c in zip(crudos, cols):
                v = fila.get(orig)
                if v is not None and str(v).strip() != '':
                    llenos[c] += 1
    return cols, n, llenos, sucios


def leer_crudo(dir_crudo, muestra=None):
    """Claves de primer nivel del registro y del detalle, con relleno.

    `muestra` limita las líneas leídas POR ARCHIVO. Con muestra el
    relleno es aproximado y el documento lo dice; sin muestra es exacto.
    """
    archivos = sorted(glob.glob(os.path.join(dir_crudo, 'crudo_*.jsonl')))
    if not archivos:
        return None
    n = 0
    top, det, lst = {}, {}, {}
    orden_top, orden_det, orden_lst = [], [], []
    # Hasta 6 valores distintos por clave, para poder escribir la glosa
    # desde la evidencia en vez de adivinar por el nombre. Se cuenta
    # aparte cuántos distintos hay EN TOTAL: sin eso, un campo con doce
    # categorías se ve igual que uno con seis, y quien lea la muestra
    # cree que vio el vocabulario completo. Pasó con
    # nombreNivelAcademico, que mostró justo 6 y tocaba el tope.
    ejemplos = {}
    distintos = defaultdict(set)
    TOPE_DISTINTOS = 400   # cortar en campos de texto libre

    def contar(d, acc, orden, prefijo=''):
        for k, v in d.items():
            if k not in acc:
                acc[k] = 0
                orden.append(k)
            if v is not None and v != '' and v != [] and v != {}:
                acc[k] += 1
            clave = prefijo + k
            s = repr(v)
            vistos = distintos[clave]
            if len(vistos) <= TOPE_DISTINTOS:
                vistos.add(s[:200])
            e = ejemplos.setdefault(clave, [])
            if len(e) < 6:
                s = s[:90] + '…' if len(s) > 90 else s
                if s not in e:
                    e.append(s)

    for path in archivos:
        leidas = 0
        with open(path, encoding='utf-8') as f:
            for linea in f:
                if muestra and leidas >= muestra:
                    break
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    reg = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                leidas += 1
                n += 1
                contar(reg, top, orden_top, '_crudo.')
                d = reg.get('detalle')
                if isinstance(d, dict):
                    contar(d, det, orden_det, '_crudo.detalle.')
                l = reg.get('listado')
                if isinstance(l, dict):
                    contar(l, lst, orden_lst, '_crudo.listado.')
    return {'archivos': len(archivos), 'registros': n,
            'top': (orden_top, top), 'detalle': (orden_det, det),
            'listado': (orden_lst, lst),
            'ejemplos': ejemplos,
            'distintos': {k: len(v) for k, v in distintos.items()},
            'tope_distintos': TOPE_DISTINTOS,
            'muestreado': bool(muestra)}


def celda(s):
    """Deja una glosa apta para una celda de tabla markdown.

    Una glosa puede tener párrafos —a veces hacen falta— y un `|` en
    medio de un ejemplo. Cualquiera de los dos parte la fila en dos y
    desalinea la tabla entera desde ahí para abajo. Se escapan acá y no
    en glosario.py: quien escribe una glosa no tiene por qué saber en
    qué formato se va a imprimir.
    """
    return (str(s).replace('|', '\\|')
                  .replace('\r\n', '\n')
                  .replace('\n\n', '<br><br>')
                  .replace('\n', '<br>'))


def pct(x, base):
    return f"{x * 100 / base:.0f}%" if base else "—"


def bloque_columnas(cols_datos, llenos, n_filas, esquema, glosas,
                    admite_manuales, hay_esquema):
    """Devuelve (líneas de tabla markdown, sin_documentar, huerfanas,
    ausentes, manuales)."""
    filas, sin_doc, manuales, ausentes = [], [], [], []
    esquema = esquema or []
    orden = [c for c in esquema if c in cols_datos] + \
            [c for c in cols_datos if c not in esquema]

    for c in orden:
        if not hay_esquema:
            origen = '?'
        elif c in esquema:
            origen = 'código'
        elif admite_manuales:
            origen = 'manual'
            manuales.append(c)
        else:
            origen = '⚠ inesperada'
            manuales.append(c)
        g = glosas.get(c)
        if not g:
            g = '**SIN DOCUMENTAR**'
            sin_doc.append(c)
        relleno = pct(llenos.get(c, 0), n_filas)
        filas.append(f"| `{c}` | {origen} | {relleno} | {celda(g)} |")

    for c in esquema:
        if c not in cols_datos:
            ausentes.append(c)
            g = glosas.get(c) or '**SIN DOCUMENTAR**'
            filas.append(f"| `{c}` | ⚠ ausente | — | {celda(g)} |")

    huerfanas = [c for c in glosas
                 if c not in cols_datos and c not in esquema]
    return filas, sin_doc, huerfanas, ausentes, manuales


def main(dir_maestras, dir_crudo, salida, muestra, evidencia=False,
         clave=None):
    hay_esquema = bool(ESQUEMAS)
    out = []
    tot_sin, tot_huerf, tot_aus, tot_man, tot_cols = [], [], [], [], 0
    tot_sucios = []

    presentes = [t for t in ORDEN
                 if os.path.exists(os.path.join(dir_maestras, t))]
    faltantes = [t for t in ORDEN if t not in presentes]
    otras = sorted(os.path.basename(p)
                   for p in glob.glob(os.path.join(dir_maestras, '*.csv'))
                   if os.path.basename(p) not in ORDEN)

    cuerpo = []
    for tabla in presentes:
        cols, n, llenos, sucios = leer_maestra(
            os.path.join(dir_maestras, tabla))
        tot_cols += len(cols)
        tot_sucios += [(tabla, c) for c in sucios]
        grano, llave = TABLAS.get(tabla, ('—', '—'))
        filas, sin_doc, huerf, aus, man = bloque_columnas(
            cols, llenos, n, ESQUEMAS.get(tabla), GLOSAS.get(tabla, {}),
            tabla in CON_COLUMNAS_MANUALES, hay_esquema)
        tot_sin += [(tabla, c) for c in sin_doc]
        tot_huerf += [(tabla, c) for c in huerf]
        tot_aus += [(tabla, c) for c in aus]
        if tabla in CON_COLUMNAS_MANUALES:
            tot_man += [(tabla, c) for c in man]

        cuerpo.append(f"\n### `{tabla}`\n")
        cuerpo.append(f"**Grano:** {grano} · **Clave:** `{llave}` · "
                      f"**{n:,} filas** · {len(cols)} columnas\n")
        if tabla in CON_COLUMNAS_MANUALES:
            cuerpo.append(
                "> Preserva columnas manuales: cualquier columna fuera "
                "del esquema se arrastra por clave entre corridas, y las "
                "filas que dejan de aparecer en el crudo no se borran.\n")
        cuerpo.append("| columna | origen | relleno | descripción |")
        cuerpo.append("|---|---|---:|---|")
        cuerpo += filas
        if huerf:
            cuerpo.append(
                f"\n⚠ **Glosas huérfanas** (hay descripción, no hay "
                f"columna): {', '.join('`%s`' % c for c in huerf)}\n")

    # ── crudo ─────────────────────────────────────────────────────
    crudo = leer_crudo(dir_crudo, muestra) if os.path.isdir(dir_crudo) else None

    # ── cuerpo del crudo ──────────────────────────────────────────
    # Se arma ANTES del bloque de estado, aunque se imprima después: el
    # estado cuenta glosas faltantes y si el crudo se procesara más
    # tarde, el resumen diría 0 mientras el documento lista pendientes.
    cuerpo_crudo = ["\n---\n\n## Crudo (`crudo_*.jsonl`)\n"]
    if not crudo:
        cuerpo_crudo.append("No se encontró `crudo_*.jsonl` en "
                            f"`{os.path.abspath(dir_crudo)}`.\n")
    else:
        if crudo['muestreado']:
            cuerpo_crudo.append(
                f"> Leído con `--muestra {muestra}`: **el relleno es "
                f"aproximado**. Sin la opción, es exacto.\n")
        cuerpo_crudo.append(
            "Una línea por (aviso × corrida × área). Append-only: el "
            "JSON se guarda íntegro para poder reprocesar sin volver a "
            "golpear el sitio.\n")

        for titulo, campo, glosas_k in (
                ("Envoltorio del registro", 'top', '_crudo'),
                ("Claves de `detalle`", 'detalle', '_crudo.detalle'),
                ("Claves de `listado`", 'listado', '_crudo.listado')):
            orden, cuentas = crudo[campo]
            g = GLOSAS.get(glosas_k, {})
            cuerpo_crudo.append(f"\n### {titulo}\n")
            cuerpo_crudo.append(f"{len(orden)} claves observadas.\n")
            cuerpo_crudo.append("| clave | relleno | descripción |")
            cuerpo_crudo.append("|---|---:|---|")
            sin = []
            for k in orden:
                d = g.get(k)
                if not d:
                    d = '**SIN DOCUMENTAR**'
                    sin.append(k)
                cuerpo_crudo.append(
                    f"| `{k}` | {pct(cuentas[k], crudo['registros'])} "
                    f"| {celda(d)} |")
            huerf = [k for k in g if k not in cuentas]
            if huerf:
                cuerpo_crudo.append(
                    f"\n⚠ Glosas huérfanas: "
                    f"{', '.join('`%s`' % k for k in huerf)}\n")
            tot_sin += [(glosas_k, k) for k in sin]
            tot_huerf += [(glosas_k, k) for k in huerf]

    # ── encabezado y alertas ──────────────────────────────────────
    out.append("# Diccionario de variables — Monitor Mercado Laboral\n")
    out.append("**Generado por `diccionario.py`. No editar a mano.**  ")
    out.append("Las descripciones se escriben en `glosario.py`; el resto "
               "sale de los datos y de los esquemas de `consolidar.py` y "
               "`homologar.py`.\n")
    out.append(f"Fuente: `{os.path.abspath(dir_maestras)}`  ")
    if crudo:
        aprox = " (muestreado)" if crudo['muestreado'] else ""
        plural = '' if crudo['archivos'] == 1 else 's'
        out.append(f"Crudo: {crudo['archivos']} archivo{plural}, "
                   f"{crudo['registros']:,} registros{aprox}\n")
    else:
        out.append("Crudo: no leído\n")

    out.append("## Estado\n")
    out.append(f"- columnas en las maestras: **{tot_cols}**")
    out.append(f"- sin documentar: **{len(tot_sin)}**")
    out.append(f"- glosas huérfanas: **{len(tot_huerf)}**")
    out.append(f"- declaradas y ausentes en el CSV: **{len(tot_aus)}**")
    out.append(f"- columnas manuales detectadas: **{len(tot_man)}**")
    if faltantes:
        out.append(f"- tablas del esquema que no están en la carpeta: "
                   f"{', '.join('`%s`' % t for t in faltantes)}")
    if otras:
        out.append(f"- CSV en la carpeta que el esquema no conoce: "
                   f"{', '.join('`%s`' % t for t in otras)}")
    if not hay_esquema:
        out.append(f"\n> ⚠ **No pude importar los esquemas** "
                   f"({', '.join(FALTA_ESQUEMA)}). Sin ellos no se puede "
                   f"distinguir una columna del código de una manual: la "
                   f"columna `origen` dice `?` en todo el documento.")
    elif FALTA_ESQUEMA:
        out.append(f"\n> ⚠ Esquemas no importados: "
                   f"{', '.join(FALTA_ESQUEMA)}.")

    if tot_sucios:
        out.append("\n> ⚠ Encabezados con espacios al borde, limpiados "
                   "al leer: "
                   + ', '.join(f'`{t}` → `{c!r}`' for t, c in tot_sucios)
                   + ". No cambia nada del análisis, pero un CSV escrito "
                     "por `consolidar.py` no debería tenerlos.")

    if tot_aus:
        out.append("\n> ⚠ **Deriva real**: estas columnas están "
                   "declaradas en el código y no aparecen en el CSV. "
                   "Suele significar que el CSV es viejo — reconsolidar.")
        for t, c in tot_aus:
            out.append(f">   - `{t}` → `{c}`")

    out.append("\n## Cómo leer esto\n")
    out.append("| origen | qué significa |")
    out.append("|---|---|")
    out.append("| `código` | la escribe `consolidar.py`/`homologar.py` |")
    out.append("| `manual` | la agregó una persona; se preserva entre "
               "corridas |")
    out.append("| `⚠ inesperada` | está en el CSV, no en el esquema, y la "
               "tabla no preserva manuales |")
    out.append("| `⚠ ausente` | está en el esquema y no en el CSV |")
    out.append("\n`relleno` es el porcentaje de filas con valor no vacío. "
               "Un relleno de 0% en una columna del código es un campo "
               "muerto de la API, no un bug del pipeline.\n")

    out.append("\n---\n\n## Maestras")
    out += cuerpo
    out += cuerpo_crudo

    # El listado de pendientes va al final: es la lista de trabajo.
    if tot_sin:
        out.append("\n---\n\n## Pendientes de documentar\n")
        out.append("Escribir la glosa en `glosario.py` y volver a "
                   "generar. **Si no sabés qué es una columna, dejala "
                   "acá**: un hueco visible es información; una glosa "
                   "inventada, no.\n")
        actual = None
        for t, c in tot_sin:
            if t != actual:
                out.append(f"\n**{t}**")
                actual = t
            out.append(f"- `{c}`")

    texto = '\n'.join(out) + '\n'
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(texto)

    # ── resumen en pantalla ───────────────────────────────────────
    print("=" * 64)
    print("  DICCIONARIO DE VARIABLES")
    print("=" * 64)
    print(f"  tablas leídas      : {len(presentes)}/{len(ORDEN)}")
    print(f"  columnas           : {tot_cols}")
    print(f"  sin documentar     : {len(tot_sin)}")
    print(f"  glosas huérfanas   : {len(tot_huerf)}")
    print(f"  declaradas ausentes: {len(tot_aus)}")
    print(f"  columnas manuales  : {len(tot_man)}")
    if crudo:
        print(f"  crudo              : {crudo['registros']:,} registro"
              f"{'' if crudo['registros'] == 1 else 's'}"
              f"{' (muestreado)' if crudo['muestreado'] else ''}")
    if tot_sucios:
        print(f"  encabezados limpiados: {len(tot_sucios)} "
              f"(espacios al borde)")
    if tot_aus:
        print("\n  ⚠ DERIVA: columnas declaradas que no están en el CSV.")
        for t, c in tot_aus[:10]:
            print(f"      {t} → {c}")
        print("      Reconsolidá y volvé a generar.")
    if tot_sin:
        una = len(tot_sin) == 1
        print(f"\n  Falta{'' if una else 'n'} {len(tot_sin)} "
              f"glosa{'' if una else 's'}."
              f"{'' if una else ' Las primeras:'}")
        for t, c in tot_sin[:10]:
            print(f"      {t:<26} {c}")
        if len(tot_sin) > 10:
            print(f"      … y {len(tot_sin) - 10} más (están al final "
                  f"del documento)")
    print(f"\n  Archivo: {salida}")
    print("=" * 64 + "\n")

    # --clave: mirar una clave puntual, tenga glosa o no. El bloque de
    # evidencia solo muestra las que FALTAN documentar, así que sin esto
    # una clave ya descrita es inauditable: `carreras` estuvo glosada
    # como "lista de {nombreCarrera}" desde una sonda de 40 avisos y
    # nunca se volvió a mirar contra los 17.744.
    if clave and crudo:
        k = clave.lower()
        hallados = [(pre, c, cuentas)
                    for pre, (orden, cuentas) in
                    (('_crudo.', crudo['top']),
                     ('_crudo.detalle.', crudo['detalle']),
                     ('_crudo.listado.', crudo['listado']))
                    for c in orden if k in c.lower()]
        print("=" * 64)
        print(f"  CLAVES QUE CONTIENEN «{clave}»")
        print("=" * 64)
        if not hallados:
            print(f"  Ninguna clave del crudo contiene «{clave}».")
        for pre, c, cuentas in hallados:
            nd = crudo['distintos'].get(pre + c, 0)
            cuantos = (f"más de {crudo['tope_distintos']}"
                       if nd > crudo['tope_distintos'] else str(nd))
            print(f"\n  ── {pre}{c}   (relleno "
                  f"{pct(cuentas.get(c, 0), crudo['registros'])}, "
                  f"{cuantos} valores distintos)")
            for v in crudo['ejemplos'].get(pre + c, []):
                print(f"       {v}")
        print("=" * 64 + "\n")

    if evidencia and crudo:
        print("=" * 64)
        print("  EVIDENCIA PARA LAS CLAVES DEL CRUDO SIN DOCUMENTAR")
        print("=" * 64)
        print("  Valores reales de cada clave sin glosa. Escribí la glosa")
        print("  a partir de esto, no del nombre de la clave. Si los")
        print("  valores no alcanzan para saber qué es, dejala pendiente.")
        # Una fuente por sección del crudo. Con un if de dos ramas, las
        # claves de `listado` se buscaban con el prefijo del envoltorio
        # y en su diccionario de cuentas: salían con 0% de relleno y sin
        # ejemplos, o sea que el bloque parecía informar "campo vacío"
        # cuando en realidad estaba mirando donde no era.
        FUENTES = {'_crudo': ('_crudo.', crudo['top'][1]),
                   '_crudo.detalle': ('_crudo.detalle.', crudo['detalle'][1]),
                   '_crudo.listado': ('_crudo.listado.', crudo['listado'][1])}
        pendientes = [(t_, c) for t_, c in tot_sin if t_ in FUENTES]
        if not pendientes:
            print("\n  No queda ninguna.")
        for t_, c in pendientes:
            prefijo, cuentas = FUENTES[t_]
            clave = prefijo + c
            nd = crudo['distintos'].get(clave, 0)
            cuantos = (f"más de {crudo['tope_distintos']}"
                       if nd > crudo['tope_distintos'] else str(nd))
            print(f"\n  ── {c}   (relleno "
                  f"{pct(cuentas.get(c, 0), crudo['registros'])}, "
                  f"{cuantos} valores distintos)")
            muestra_n = min(6, nd)
            for v in crudo['ejemplos'].get(clave, []):
                print(f"       {v}")
            if nd > muestra_n:
                print(f"       … y {nd - muestra_n} valores distintos más")
        print("=" * 64 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--crudo', default='crudo')
    ap.add_argument('--salida', default=None,
                    help='por defecto, DICCIONARIO.md en el repo')
    ap.add_argument('--muestra', type=int, default=None,
                    help='líneas por archivo de crudo (relleno aproximado)')
    ap.add_argument('--evidencia', action='store_true',
                    help='muestra valores reales de las claves sin glosa')
    ap.add_argument('--clave', default=None,
                    help='inspecciona una clave del crudo, tenga glosa o no')
    a = ap.parse_args()
    destino = a.salida or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'DICCIONARIO.md')
    main(a.maestras, a.crudo, destino, a.muestra, a.evidencia, a.clave)
