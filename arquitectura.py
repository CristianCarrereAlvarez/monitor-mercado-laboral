"""
El mapa de archivos del monitor, y cómo se conectan
====================================================

Genera `visualizaciones/arquitectura.html`: qué archivo produce qué,
qué lee cada uno, y dónde vive cada cosa —repo, Drive o la red—.

POR QUÉ SE GENERA Y NO SE DIBUJA A MANO
  El diagrama anterior («Del catálogo al crudo») era SVG escrito a mano,
  con cada caja en coordenadas absolutas. Sirvió, pero cubría una sola
  etapa y agregarle un archivo significaba recalcular decenas de números.

  Acá el diagrama es una **declaración**: `BANDAS` dice qué archivos hay
  y en qué capa, `FLECHAS` dice qué conecta con qué, y el layout se
  calcula. Sumar un script es una línea, y las coordenadas nunca quedan
  mal.

  El corolario es el de siempre en este proyecto: un documento que se
  actualiza a mano se desincroniza en silencio. Éste no evita eso —hay
  que acordarse de agregar el archivo— pero baja el costo de hacerlo de
  «rehacer el dibujo» a «escribir una línea».

Uso:
  ./arquitectura.sh
  python arquitectura.py --salida arquitectura.html
"""

import argparse, html, os

# ── el modelo ─────────────────────────────────────────────────────
# id: (título, subtítulo, clase)
#   clase:  repo | datos | red | humano | salida
BANDAS = [
    ("FUERA DEL PROYECTO", [
        ('api',   'trabajando.cl', 'GET /api/searchjob · /api/ofertas/{id}', 'red'),
        ('sies',  'SIES Oferta 2026', '29.911 programas · 297 genéricas', 'red'),
        ('unesco', 'ISCED-F 2013', 'UNESCO · 138 códigos', 'red'),
    ]),
    ("CATÁLOGOS — en el repo, versionados", [
        ('cat_sies', 'carreras_sies_2026.py', '10 áreas · 199 términos de búsqueda', 'repo'),
        ('cat_prog', 'programas_propios.csv', '204 programas · nivel · ISCED-F', 'repo'),
        ('cat_isced', 'isced_f_2013.csv', '11 · 29 · 98 códigos', 'repo'),
    ]),
    ("CAPTURA — solo desde IP residencial", [
        ('mensual', 'mensual.sh', 'las 10 áreas en orden, con log', 'repo'),
        ('capturar', 'capturar.sh', 'resuelve la carpeta de datos y hace cd', 'repo'),
        ('scraper', 'scraper_v9.py', 'búsqueda secuencial + detalle ×4', 'repo'),
    ]),
    ("EL CRUDO — append-only, nunca se reescribe", [
        ('crudo', 'crudo/crudo_{área}_{YYYY_MM}.jsonl',
         'JSON íntegro de la API · 51 claves por detalle', 'datos'),
    ]),
    ("DERIVACIÓN", [
        ('procesar', 'procesar.sh', 'consolidar → control → diccionario', 'repo'),
        ('consolidar', 'consolidar.py', 'upsert idempotente · 9 tablas', 'repo'),
        ('homolog_py', 'homologacion.py', 'la clave del join y los niveles', 'repo'),
    ]),
    ("DECISIÓN HUMANA — se edita a mano, se preserva", [
        ('homolog', 'maestras/homologacion.csv',
         '527 entradas → programa propio o campo ISCED', 'humano'),
    ]),
    ("LAS MAESTRAS", [
        ('avisos', 'avisos.csv', '1 fila por aviso · panel longitudinal', 'datos'),
        ('puente', 'tablas puente ×4',
         'aviso × entrada · término · habilidad · institución', 'datos'),
        ('aviso_prog', 'aviso_programa.csv',
         'aviso × programa o campo ISCED', 'datos'),
        ('dim', 'dimensiones ×3',
         'empresas · entradas_trabajando · instituciones', 'datos'),
    ]),
    ("CONTROL Y REFERENCIA", [
        ('control', 'control.py', '6 bloques + panel longitudinal', 'repo'),
        ('validar', 'validar_homologacion.py', 'rompe · revisar · informe', 'repo'),
        ('dicc', 'diccionario.py', '+ glosario.py → DICCIONARIO.md', 'repo'),
        ('mirar', 'mirar.py', 'qué hay detrás de una entrada', 'repo'),
    ]),
    ("VISUALIZACIONES — Drive/visualizaciones/", [
        ('viz_var', 'variables_maestras.html', '126 columnas con su glosa', 'salida'),
        ('viz_coo', 'coocurrencia_programas.html', 'qué programa se pide con qué', 'salida'),
        ('viz_red', 'red_areas.html', 'qué áreas se piden juntas', 'salida'),
        ('viz_agr', 'agrupamiento.html', 'estadística del agrupamiento', 'salida'),
        ('viz_arq', 'arquitectura.html', 'este diagrama', 'salida'),
    ]),
]

# (desde, hasta, etiqueta, estilo)   estilo: normal | suave | fuerte
FLECHAS = [
    ('api', 'scraper', '', 'normal'),
    ('sies', 'cat_sies', '', 'suave'),
    ('sies', 'cat_prog', '', 'suave'),
    ('unesco', 'cat_isced', '', 'suave'),
    ('cat_sies', 'scraper', 'términos', 'normal'),
    ('mensual', 'capturar', '', 'normal'),
    ('capturar', 'scraper', '', 'normal'),
    ('scraper', 'crudo', '', 'fuerte'),
    ('crudo', 'scraper', 'reanudable', 'suave'),
    ('crudo', 'consolidar', '', 'fuerte'),
    ('procesar', 'consolidar', '', 'normal'),
    ('homolog_py', 'consolidar', '', 'normal'),
    ('homolog', 'consolidar', '', 'normal'),
    ('cat_prog', 'consolidar', '', 'normal'),
    ('cat_isced', 'consolidar', '', 'normal'),
    ('consolidar', 'avisos', '', 'fuerte'),
    ('consolidar', 'puente', '', 'fuerte'),
    ('consolidar', 'aviso_prog', '', 'fuerte'),
    ('consolidar', 'dim', '', 'fuerte'),
    ('avisos', 'control', '', 'normal'),
    ('puente', 'control', '', 'normal'),
    ('dim', 'mirar', '', 'normal'),
    ('homolog', 'validar', '', 'normal'),
    ('avisos', 'dicc', '', 'suave'),
    ('aviso_prog', 'viz_coo', '', 'fuerte'),
    ('aviso_prog', 'viz_red', '', 'fuerte'),
    ('aviso_prog', 'viz_agr', '', 'fuerte'),
    ('dicc', 'viz_var', '', 'normal'),
]

# Notas al margen: (id de la caja, texto). Salen a la derecha.
NOTAS = {
    'crudo': 'Guardar el JSON íntegro es lo que permite rehacer cualquier '
             'derivación sin volver a la red.',
    'homolog': 'Es trabajo humano y vive con los datos, no en el repo. '
               '`consolidar.py` lo aplica; si no está, avisa y sigue.',
    'aviso_prog': 'Solo `fuente = declarada`. Los avisos genéricos se '
                  'filtran con `n_entradas_declaradas_aviso`.',
}

ANCHO = 1180
MARGEN = 40
ALTO_CAJA = 62
GAP_X = 16
GAP_BANDA = 74
Y0 = 34


def disponer():
    """Coordenadas de cada caja. Layout por bandas: las cajas de una
    banda se reparten el ancho útil en partes iguales."""
    cajas, y = {}, Y0
    bandas = []
    util = ANCHO - 2 * MARGEN - 300      # 300 = columna de notas
    for titulo, items in BANDAS:
        n = len(items)
        w = (util - GAP_X * (n - 1)) / n
        bandas.append((titulo, y))
        for i, (cid, tit, sub, clase) in enumerate(items):
            cajas[cid] = {
                'x': MARGEN + i * (w + GAP_X), 'y': y + 14,
                'w': w, 'h': ALTO_CAJA,
                'titulo': tit, 'sub': sub, 'clase': clase,
            }
        y += 14 + ALTO_CAJA + GAP_BANDA
    return cajas, bandas, y - GAP_BANDA + 30


def ajustar(txt, ancho_px, px=12):
    """El texto es monoespaciado, así que su ancho es calculable: baja
    el cuerpo hasta que entre y, si aun así no entra, recorta.

    Sin esto el título se desborda de la caja, que es el defecto que
    tenía la primera versión de este diagrama."""
    cabe = ancho_px - 28
    while px > 8.5 and len(txt) * px * 0.6 > cabe:
        px -= 0.5
    max_car = int(cabe / (px * 0.6))
    if len(txt) > max_car:
        txt = txt[:max_car - 1] + '…'
    return txt, px


def camino(a, b):
    """Ruta ortogonal de la caja `a` a la `b`.

    Hacia abajo sale del borde inferior y entra por el superior, con un
    quiebre a media altura. Hacia arriba —la única es la reanudación del
    crudo— rodea por la izquierda, que es como se dibujaba a mano."""
    ax, ay = a['x'] + a['w'] / 2, a['y'] + a['h']
    bx, by = b['x'] + b['w'] / 2, b['y']
    if abs(a['y'] - b['y']) < 1:
        # misma banda: horizontal, de borde a borde
        y = a['y'] + a['h'] / 2
        if a['x'] < b['x']:
            return f"M{a['x'] + a['w']:.0f},{y:.0f} H{b['x']:.0f}"
        return f"M{a['x']:.0f},{y:.0f} H{b['x'] + b['w']:.0f}"
    if b['y'] > a['y']:
        m = (ay + by) / 2
        if abs(ax - bx) < 2:
            return f"M{ax:.0f},{ay:.0f} V{by:.0f}"
        return (f"M{ax:.0f},{ay:.0f} V{m:.0f} H{bx:.0f} V{by:.0f}")
    # hacia arriba, por el costado izquierdo
    izq = min(a['x'], b['x']) - 22
    return (f"M{a['x']:.0f},{a['y'] + a['h'] / 2:.0f} H{izq:.0f} "
            f"V{b['y'] + b['h'] / 2:.0f} H{b['x']:.0f}")


def svg():
    cajas, bandas, alto = disponer()
    p = []
    p.append(f'<svg class="dg" viewBox="0 0 {ANCHO} {alto:.0f}" role="img" '
             f'aria-label="Mapa de los archivos del monitor y sus '
             f'conexiones, de la API de trabajando.cl y los catálogos '
             f'hasta las maestras y las visualizaciones.">')
    p.append('<defs>'
             '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
             'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
             '<polygon class="ah-fill" points="0,1.5 10,5 0,8.5"/></marker>'
             '<marker id="ahs" viewBox="0 0 10 10" refX="9" refY="5" '
             'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
             '<polygon class="ahs-fill" points="0,1.5 10,5 0,8.5"/></marker>'
             '</defs>')

    # flechas primero: quedan por debajo de las cajas
    for a, b, etq, estilo in FLECHAS:
        if a not in cajas or b not in cajas:
            continue
        cls = {'normal': 'edge', 'suave': 'edge-soft',
               'fuerte': 'edge-strong'}[estilo]
        p.append(f'<path class="{cls}" d="{camino(cajas[a], cajas[b])}"/>')
        if etq:
            ca, cb = cajas[a], cajas[b]
            x = (ca['x'] + ca['w'] / 2 + cb['x'] + cb['w'] / 2) / 2
            y = (ca['y'] + ca['h'] + cb['y']) / 2 - 5
            if abs(ca['y'] - cb['y']) < 1:
                x = (max(ca['x'], cb['x']) + min(ca['x'] + ca['w'],
                                                 cb['x'] + cb['w'])) / 2
                y = ca['y'] + ca['h'] / 2 - 7
            p.append(f'<text class="t-edge" x="{x:.0f}" y="{y:.0f}" '
                     f'text-anchor="middle">{html.escape(etq)}</text>')

    for titulo, y in bandas:
        p.append(f'<text class="t-band" x="{MARGEN}" y="{y:.0f}">'
                 f'{html.escape(titulo)}</text>')

    for cid, c in cajas.items():
        p.append(f'<rect class="box b-{c["clase"]}" x="{c["x"]:.0f}" '
                 f'y="{c["y"]:.0f}" width="{c["w"]:.0f}" '
                 f'height="{c["h"]:.0f}" rx="3"/>')
        tit, px = ajustar(c['titulo'], c['w'], 12)
        sub, pxs = ajustar(c['sub'], c['w'], 9.5)
        p.append(f'<text class="t-title tt-{c["clase"]}" '
                 f'style="font-size:{px}px" '
                 f'x="{c["x"] + 14:.0f}" y="{c["y"] + 26:.0f}">'
                 f'{html.escape(tit)}</text>')
        p.append(f'<text class="t-sub" style="font-size:{pxs}px" '
                 f'x="{c["x"] + 14:.0f}" '
                 f'y="{c["y"] + 46:.0f}">{html.escape(sub)}</text>')

    # notas al margen
    x = ANCHO - 300 + MARGEN
    for cid, txt in NOTAS.items():
        c = cajas.get(cid)
        if not c:
            continue
        # arranca en el borde derecho de la banda: una línea que sale
        # de la caja cruzaría por encima de sus vecinas.
        borde = MARGEN + (ANCHO - 2 * MARGEN - 300)
        p.append(f'<path class="edge-note" d="M{borde + 6:.0f},'
                 f'{c["y"] + c["h"] / 2:.0f} H{x - 12:.0f}"/>')
        y = c['y'] + 14
        for i, linea in enumerate(envolver(txt, 38)):
            p.append(f'<text class="t-note" x="{x:.0f}" '
                     f'y="{y + i * 15:.0f}">{html.escape(linea)}</text>')
    p.append('</svg>')
    return '\n'.join(p)


def envolver(txt, ancho):
    lineas, actual = [], ''
    for palabra in txt.split():
        if len(actual) + len(palabra) + 1 > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f'{actual} {palabra}'.strip()
    if actual:
        lineas.append(actual)
    return lineas


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arquitectura — Monitor Mercado Laboral</title>
<style>
:root{
  --ground:#E9ECEA; --surface:#F6F8F6; --surface-2:#FFFFFF; --ink:#16211E;
  --muted:#4E5C58; --line:#C3CCC8; --line-soft:#D8DFDB; --accent:#0E7A80;
  --accent-wash:#DCEBEA; --warn:#A8384E; --warn-wash:#F2DFE3;
  --humano:#8A5A12; --humano-wash:#FBF0DC;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --display:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0E1513; --surface:#16201D; --surface-2:#1B2724; --ink:#DCE5E1;
  --muted:#869993; --line:#2E3D39; --line-soft:#22302C; --accent:#4CB8C0;
  --accent-wash:#123230; --warn:#E4788C; --warn-wash:#34181F;
  --humano:#E2B464; --humano-wash:#2B2415;
}}
:root[data-theme="dark"]{
  --ground:#0E1513; --surface:#16201D; --surface-2:#1B2724; --ink:#DCE5E1;
  --muted:#869993; --line:#2E3D39; --line-soft:#22302C; --accent:#4CB8C0;
  --accent-wash:#123230; --warn:#E4788C; --warn-wash:#34181F;
  --humano:#E2B464; --humano-wash:#2B2415;
}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);
 font-size:16px;line-height:1.65;margin:0;padding:0 20px 96px;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto}
.col{max-width:62ch}
header{padding:64px 0 36px;border-bottom:1px solid var(--line);
 margin-bottom:44px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--muted);margin:0 0 18px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(32px,5vw,48px);
 line-height:1.08;letter-spacing:-.015em;margin:0 0 20px;text-wrap:balance}
.lede{font-size:18px;color:var(--muted);margin:0;max-width:60ch}
h2{font-family:var(--display);font-weight:600;font-size:25px;
 margin:52px 0 8px;letter-spacing:-.01em}
p{margin:0 0 16px}
code{font-family:var(--mono);font-size:.88em;background:var(--surface);
 border:1px solid var(--line-soft);border-radius:3px;padding:.1em .34em}
.figbox{background:var(--surface);border:1px solid var(--line);
 border-radius:4px;padding:22px 18px;overflow-x:auto;margin:30px 0 0}
.dg{display:block;width:100%;min-width:940px;height:auto;color:var(--ink)}
.dg text{font-family:var(--mono);fill:currentColor}
.t-title{font-size:12px;font-weight:600}
.t-sub{font-size:9.5px;fill:var(--muted)}
.t-band{font-size:10px;letter-spacing:.13em;fill:var(--muted)}
.t-edge{font-size:9px;fill:var(--muted)}
.t-note{font-size:9.5px;fill:var(--muted)}
.box{fill:var(--surface-2);stroke:var(--line);stroke-width:1.25}
.b-red{fill:none;stroke:var(--muted);stroke-dasharray:4 3}
.b-datos{fill:var(--accent-wash);stroke:var(--accent);stroke-width:1.4}
.b-humano{fill:var(--humano-wash);stroke:var(--humano);stroke-width:1.4}
.b-salida{fill:var(--surface-2);stroke:var(--accent);stroke-width:1.4}
.tt-datos,.tt-salida{fill:var(--accent)}
.tt-humano{fill:var(--humano)}
.edge{fill:none;stroke:var(--line);stroke-width:1.25;marker-end:url(#ah)}
.edge-strong{fill:none;stroke:var(--accent);stroke-width:1.5;
 marker-end:url(#ah)}
.edge-soft{fill:none;stroke:var(--muted);stroke-width:1.1;
 stroke-dasharray:4 3;marker-end:url(#ahs)}
.edge-note{fill:none;stroke:var(--line-soft);stroke-width:1}
.ah-fill{fill:var(--accent)}
.ahs-fill{fill:var(--muted)}
.leyenda{display:flex;gap:22px;flex-wrap:wrap;font-family:var(--mono);
 font-size:11px;color:var(--muted);margin-top:18px}
.sw{display:inline-block;width:13px;height:9px;border-radius:2px;
 vertical-align:0;margin-right:5px;border:1px solid var(--line)}
.sw-datos{background:var(--accent-wash);border-color:var(--accent)}
.sw-humano{background:var(--humano-wash);border-color:var(--humano)}
.sw-red{background:none;border-style:dashed;border-color:var(--muted)}
.note{border-left:2px solid var(--accent);background:var(--surface);
 padding:16px 20px;margin:26px 0 0;border-radius:0 3px 3px 0}
.note p{margin:0 0 10px;font-size:15px}
.note p:last-child{margin:0}
.tag{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--accent);display:block;
 margin-bottom:6px}
footer{border-top:1px solid var(--line);padding-top:22px;margin-top:64px;
 font-family:var(--mono);font-size:12px;color:var(--muted)}
</style></head><body>
<div class="wrap">
<header>
  <p class="eyebrow">Monitor Mercado Laboral Chile</p>
  <h1>Qué archivo produce qué</h1>
  <p class="lede">Todos los archivos del proyecto y sus conexiones: de la
  API y los catálogos oficiales hasta las maestras y las páginas que se
  abren con doble clic.</p>
</header>

<div class="figbox">__SVG__</div>
<div class="leyenda">
  <span><span class="sw sw-red"></span>fuera del proyecto</span>
  <span><span class="sw"></span>código, en el repo</span>
  <span><span class="sw sw-datos"></span>datos, en Drive</span>
  <span><span class="sw sw-humano"></span>decisión humana, editable a mano</span>
</div>

<section class="col">
  <h2>Las tres separaciones que sostienen todo</h2>
  <p><b>Captura y derivación son etapas distintas.</b> El crudo guarda el
  JSON íntegro de la API, así que cualquier cambio de criterio se
  reprocesa desde disco. Se usó cuatro veces en un solo día durante el
  desarrollo. <b>Nunca se re-scrapea por un cambio de parseo.</b></p>

  <p><b>El código vive en el repo; los datos, en Drive.</b> Los catálogos
  —SIES, ISCED-F, programas propios— son código: cambian cuando cambia un
  criterio, no cuando llegan avisos nuevos. El crudo y las maestras están
  en <code>.gitignore</code>.</p>

  <p><b>La homologación es la excepción, y a propósito.</b> Es un CSV que
  se edita a mano y vive con los datos. <code>consolidar.py</code> no la
  decide: la aplica. Si el archivo no está, lo dice en pantalla y sigue
  sin escribir <code>aviso_programa.csv</code> — import blando, nunca
  falla en silencio.</p>

  <div class="note">
    <span class="tag">Dónde queda cada salida</span>
    <p>Las páginas HTML se escriben en
    <code>&lt;datos&gt;/visualizaciones/</code>, junto a los datos y no en
    el repo: son producto de una corrida, no código. <code>.gitignore</code>
    las excluye por si alguna cae en el repo por correr un script sin
    <code>--salida</code>.</p>
    <p><code>DICCIONARIO.md</code> es la excepción: ése sí se commitea,
    porque cambia cuando cambia el <b>código</b> y sirve de control en el
    diff.</p>
  </div>
</section>

<footer>Generado por <code>arquitectura.py</code> · repositorio
monitor-mercado-laboral</footer>
</div></body></html>
"""


def main(salida):
    doc = PAGINA.replace('__SVG__', svg())
    carpeta = os.path.dirname(os.path.abspath(salida))
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(doc)
    cajas = sum(len(i) for _, i in BANDAS)
    print(f"\n  {len(BANDAS)} bandas · {cajas} archivos · "
          f"{len(FLECHAS)} conexiones")
    print(f"  → {os.path.abspath(salida)}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', default='arquitectura.html')
    main(ap.parse_args().salida)
