"""
Las variables de las maestras, en una página
=============================================

Genera un HTML con las columnas de las tablas maestras y qué es
cada una. Se abre con doble clic y queda en Drive: sin terminal y sin
servidor. Lo único que pide a la red son las tipografías (Google Fonts);
sin conexión cae a las del sistema y se lee igual.

QUÉ LO DISTINGUE DE `DICCIONARIO.md`
  El diccionario es el documento de control: cruza las glosas con los
  datos reales y con los esquemas, y marca lo que falta (SIN DOCUMENTAR,
  HUÉRFANA), el relleno de cada columna y el crudo. Sirve para descubrir
  huecos, y por eso hay que correrlo con las maestras a mano.

  Esta página es lo contrario: solo la referencia, para consultar
  mientras se trabaja. No lee ni maestras ni crudo — sale entera de
  `consolidar.py`, `homologar.py` y `glosario.py`—, así que corre en
  cualquier máquina y no depende de que haya datos capturados.

  El texto de las glosas es el mismo objeto en los dos casos:
  `glosario.py`. Un solo lugar donde escribir.

LA BANDA DE CAUTELA
  Las columnas marcadas son las que tienen una glosa escrita sobre todo
  para evitar una mala lectura: `n_corridas_visto` no cuenta corridas,
  `sies_por_termino` sobre-atribuye por diseño, `calidad_duracion` tiene
  tres valores que no se pueden promediar juntos. Es una lista editorial
  —`CAUTELA`, acá abajo—, no una heurística sobre el texto: si se agrega
  una glosa de ese tipo, hay que sumarla a mano.

Uso:
  ./variables.sh                 # genera y abre
  python variables.py --salida variables_maestras.html
"""

import argparse, html, os, re, sys

FALTA = []
ESQUEMAS = {}
try:
    import consolidar as C
    ESQUEMAS.update({
        'avisos.csv':              C.COLS_AVISOS,
        'aviso_entrada.csv':       C.COLS_AVISO_ENTRADA,
        'aviso_termino.csv':       C.COLS_AVISO_TERMINO,
        'aviso_habilidad.csv':     C.COLS_AVISO_HABILIDAD,
        'aviso_institucion.csv':   C.COLS_AVISO_INSTITUCION,
        'aviso_programa.csv':      C.COLS_AVISO_PROGRAMA,
        'empresas.csv':            C.COLS_EMPRESAS,
        'entradas_trabajando.csv': C.COLS_ENTRADAS,
        'instituciones.csv':       C.COLS_INSTITUCIONES,
    })
except Exception as e:
    FALTA.append(f'consolidar.py ({e})')

try:
    import homologar as H
    ESQUEMAS['homologacion_carreras.csv'] = H.COLUMNAS
    MANUALES = set(H.MANUALES)
except Exception as e:
    FALTA.append(f'homologar.py ({e})')
    MANUALES = set()

try:
    from glosario import GLOSAS, TABLAS, CON_COLUMNAS_MANUALES
except Exception as e:
    FALTA.append(f'glosario.py ({e})')
    GLOSAS, TABLAS, CON_COLUMNAS_MANUALES = {}, {}, set()

if FALTA:
    print("\n  ⛔  No pude importar: " + ', '.join(FALTA))
    print("     Corré esto con PYTHONPATH apuntando al repo, o desde el "
          "repo.\n")
    sys.exit(1)

# Columnas cuya glosa existe sobre todo para evitar una mala lectura.
# Decisión editorial: si escribís una glosa de ese tipo, agregala acá.
CAUTELA = {
    'avisos.csv': {
        'url', 'n_corridas_visto', 'dias_publicado_hasta_baja',
        'calidad_duracion', 'empresa_id', 'empresa_nombre',
        'vigencia_declarada_dias', 'area_funcional', 'latitud', 'longitud',
        'jornada', 'modalidad', 'exp_inconsistente', 'nivel_academico',
        'n_entradas_declaradas', 'postulaciones', 'visualizaciones',
        'areas_scraping', 'terminos_busqueda', 'sies_por_termino',
        'n_terminos_sin_mapeo', 'hash_entradas', 'n_avisos_mismo_conjunto'},
    'aviso_entrada.csv': {'fuente'},
    'aviso_institucion.csv': {'n_entradas_declaradas_aviso'},
    'aviso_programa.csv': {'tipo_entrada', 'programa_propio',
                           'atribucion_multiple', 'n_entradas_origen',
                           'n_entradas_declaradas_aviso'},
    'empresas.csv': {'nombre_canonico'},
    'entradas_trabajando.csv': {'entrada_trabajando', 'n_avisos_acum',
                                'n_avisos_especificos'},
    'instituciones.csv': {'n_avisos_especificos'},
    'homologacion_carreras.csv': {'sugerencia', 'score', 'tipo_relacion',
                                  'nivel_condicion'},
}

SIN_GLOSA = ('<em>Sin glosa.</em> La columna existe en el esquema y '
             'todavía no está documentada en <code>glosario.py</code>.')


def rico(s):
    """Markdown mínimo de las glosas → HTML. Escapa primero."""
    s = html.escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return s.replace('\n\n', '</p><p>').replace('\n', ' ')


def construir():
    secciones, nav, n_cols, n_caut, sin_glosa = [], [], 0, 0, 0

    for tabla in TABLAS:
        cols = ESQUEMAS.get(tabla)
        if not cols:
            continue
        glosas = GLOSAS.get(tabla, {})
        manual_tabla = tabla in CON_COLUMNAS_MANUALES
        caut_tabla = CAUTELA.get(tabla, set())
        grano, llave = TABLAS[tabla]
        slug = tabla.replace('.csv', '').replace('_', '-')

        n_cols += len(cols)
        n_caut += sum(1 for c in cols if c in caut_tabla)
        nav.append(f'<a href="#{slug}"><span class="nv-n">{tabla}</span>'
                   f'<span class="nv-c">{len(cols)}</span></a>')

        filas = []
        for col in cols:
            glosa = glosas.get(col)
            if not glosa:
                sin_glosa += 1
            chip = ('<span class="chip chip-man">manual</span>'
                    if manual_tabla and col in MANUALES else '')
            filas.append(
                f'<div class="fila{" cauto" if col in caut_tabla else ""}">'
                f'<div class="nom"><code class="col">{html.escape(col)}</code>'
                f'{chip}</div>'
                f'<div class="def"><p>'
                f'{rico(glosa) if glosa else SIN_GLOSA}</p></div></div>')

        aviso_man = ('<p class="tnota">Preserva columnas manuales: cualquier '
                     'columna fuera del esquema se arrastra por clave entre '
                     'corridas, y las filas que dejan de aparecer en el crudo '
                     'no se borran.</p>') if manual_tabla else ''
        secciones.append(
            f'<section id="{slug}"><header class="th">'
            f'<h2>{tabla}</h2>'
            f'<p class="meta"><span>{html.escape(grano)}</span>'
            f'<span class="sep">·</span>clave '
            f'<code>{html.escape(llave)}</code>'
            f'<span class="sep">·</span>{len(cols)} columnas</p>'
            f'{aviso_man}</header>{"".join(filas)}</section>')

    return secciones, nav, n_cols, n_caut, sin_glosa


CABEZA = """<title>Variables del Monitor Laboral</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>
:root{
  --papel:#f6f8f7; --sup:#fff; --tinta:#16211f; --tenue:#5d6b68;
  --linea:#dde4e2; --linea2:#eef2f1; --acento:#0f6b5c; --acento-sup:#e7f1ee;
  --caut:#8a5a12; --caut-sup:#fdf3e0; --caut-borde:#e3c48a;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --papel:#101615; --sup:#17201e; --tinta:#e6ecea; --tenue:#96a5a1;
    --linea:#27312f; --linea2:#1d2725; --acento:#5cc4ad; --acento-sup:#15302a;
    --caut:#e2b464; --caut-sup:#2b2415; --caut-borde:#5a4820;
  }
}
:root[data-theme="dark"]{
  --papel:#101615; --sup:#17201e; --tinta:#e6ecea; --tenue:#96a5a1;
  --linea:#27312f; --linea2:#1d2725; --acento:#5cc4ad; --acento-sup:#15302a;
  --caut:#e2b464; --caut-sup:#2b2415; --caut-borde:#5a4820;
}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
 font:400 15.5px/1.62 "IBM Plex Sans",system-ui,-apple-system,sans-serif;
 -webkit-font-smoothing:antialiased}
.envoltura{max-width:1180px;margin:0 auto;padding:0 28px}

header.top{padding:56px 0 26px;border-bottom:1px solid var(--linea)}
h1{font:500 40px/1.1 Newsreader,Georgia,serif;margin:0 0 10px;
 letter-spacing:-.012em;text-wrap:balance}
.bajada{margin:0;max-width:60ch;color:var(--tenue);font-size:16px}
.cifras{display:flex;flex-wrap:wrap;gap:26px;margin-top:26px;
 font-variant-numeric:tabular-nums}
.cifra b{display:block;font:500 26px/1 Newsreader,Georgia,serif}
.cifra span{font-size:12px;letter-spacing:.08em;text-transform:uppercase;
 color:var(--tenue)}
.cifra.al b{color:var(--caut)}

.barra{position:sticky;top:0;z-index:9;background:var(--papel);
 border-bottom:1px solid var(--linea);padding:12px 0}
.barra .envoltura{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
#q{flex:1;min-width:230px;padding:9px 13px;font:400 14.5px/1.4 inherit;
 color:var(--tinta);background:var(--sup);border:1px solid var(--linea);
 border-radius:7px}
#q:focus{outline:2px solid var(--acento);outline-offset:1px}
#cuenta{font-size:13px;color:var(--tenue);font-variant-numeric:tabular-nums}

.cuerpo{display:grid;grid-template-columns:214px minmax(0,1fr);gap:44px;
 padding:34px 0 90px;align-items:start}
nav{position:sticky;top:74px;display:flex;flex-direction:column;gap:1px}
nav a{display:flex;justify-content:space-between;gap:10px;padding:6px 9px;
 border-radius:6px;text-decoration:none;color:var(--tenue);font-size:13px}
nav a:hover{background:var(--acento-sup);color:var(--acento)}
.nv-n{font-family:"IBM Plex Mono",monospace;font-size:12px;
 overflow:hidden;text-overflow:ellipsis}
.nv-c{font-variant-numeric:tabular-nums;opacity:.65}

section{margin-bottom:52px;scroll-margin-top:76px}
.th{padding-bottom:12px;border-bottom:2px solid var(--tinta);margin-bottom:6px}
h2{font:500 15px/1.3 "IBM Plex Mono",monospace;margin:0 0 6px;
 letter-spacing:-.01em}
.meta{margin:0;font-size:13px;color:var(--tenue)}
.sep{padding:0 7px;opacity:.5}
.tnota{margin:10px 0 0;font-size:13px;color:var(--tenue);max-width:66ch;
 border-left:2px solid var(--linea);padding-left:11px}

.fila{display:grid;grid-template-columns:250px minmax(0,1fr);gap:26px;
 padding:13px 0 13px 13px;border-bottom:1px solid var(--linea2);
 border-left:2px solid transparent}
.fila.cauto{border-left-color:var(--caut-borde);background:
 linear-gradient(90deg,var(--caut-sup),transparent 62%)}
.nom{display:flex;flex-wrap:wrap;gap:6px;align-items:baseline}
code.col{font:500 13px/1.5 "IBM Plex Mono",monospace;color:var(--acento);
 word-break:break-word}
.def p{margin:0 0 9px;max-width:66ch}
.def p:last-child{margin-bottom:0}
.def code{font:400 12.5px/1.5 "IBM Plex Mono",monospace;
 background:var(--linea2);padding:1px 5px;border-radius:4px}
.chip{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
 padding:2px 7px;border-radius:20px;background:var(--acento-sup);
 color:var(--acento);white-space:nowrap}
.leyenda{display:flex;gap:20px;flex-wrap:wrap;font-size:12.5px;
 color:var(--tenue);margin-top:16px;align-items:center}
.mues{display:inline-block;width:16px;height:11px;border-radius:2px;
 border-left:2px solid var(--caut-borde);background:var(--caut-sup);
 vertical-align:-1px;margin-right:5px}
.vacio{padding:60px 0;color:var(--tenue);text-align:center}
@media (max-width:860px){
  .cuerpo{grid-template-columns:1fr;gap:20px}
  nav{position:static;flex-direction:row;overflow-x:auto;gap:4px;
   padding-bottom:6px}
  nav a{flex:none;background:var(--sup);border:1px solid var(--linea)}
  .nv-c{display:none}
  .fila{grid-template-columns:1fr;gap:6px}
}
</style>
"""


def cuerpo(secciones, nav, n_cols, n_caut, n_tablas):
    return f"""<div class="envoltura">
<header class="top">
  <h1>Variables del Monitor Laboral</h1>
  <p class="bajada">Las {n_cols} columnas de las {n_tablas} tablas maestras,
  con qué es cada una, de dónde sale y cómo se lee mal. Generado desde
  <code>glosario.py</code>, que es la fuente en el repositorio.</p>
  <div class="cifras">
    <div class="cifra"><b>{n_tablas}</b><span>tablas</span></div>
    <div class="cifra"><b>{n_cols}</b><span>columnas</span></div>
    <div class="cifra al"><b>{n_caut}</b><span>con advertencia</span></div>
  </div>
  <div class="leyenda">
    <span><span class="mues"></span>la glosa existe para evitar una mala
    lectura</span>
    <span><span class="chip">manual</span> la completa una persona; se
    preserva entre corridas</span>
  </div>
</header>
</div>

<div class="barra"><div class="envoltura">
  <input type="search" id="q" placeholder="Buscar columna o texto de la definición…" autocomplete="off">
  <span id="cuenta"></span>
</div></div>

<div class="envoltura"><div class="cuerpo">
  <nav>{''.join(nav)}</nav>
  <main>{''.join(secciones)}<div class="vacio" id="vacio" style="display:none">Ninguna columna coincide.</div></main>
</div></div>

<script>
const q = document.getElementById('q'), cuenta = document.getElementById('cuenta');
const filas = [...document.querySelectorAll('.fila')];
const secs = [...document.querySelectorAll('section')];
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
filas.forEach(f => f.dataset.t = norm(f.textContent));
function filtrar(){{
  const t = norm(q.value.trim());
  let n = 0;
  filas.forEach(f => {{
    const ok = !t || f.dataset.t.includes(t);
    f.style.display = ok ? '' : 'none';
    if(ok) n++;
  }});
  secs.forEach(s => {{
    const vis = [...s.querySelectorAll('.fila')].some(f => f.style.display !== 'none');
    s.style.display = vis ? '' : 'none';
  }});
  cuenta.textContent = t ? n + ' de {n_cols}' : '{n_cols} columnas';
  document.getElementById('vacio').style.display = n ? 'none' : 'block';
}}
q.addEventListener('input', filtrar);
filtrar();
</script>
"""


def main(salida):
    secciones, nav, n_cols, n_caut, sin_glosa = construir()
    if not secciones:
        print("\n  ⛔  No hay ninguna tabla con esquema y glosas.\n")
        sys.exit(1)

    doc = ('<!doctype html>\n<html lang="es">\n<head>\n'
           '<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,'
           'initial-scale=1">\n'
           + CABEZA + '</head>\n<body>\n'
           + cuerpo(secciones, nav, n_cols, n_caut, len(secciones))
           + '</body>\n</html>\n')

    carpeta = os.path.dirname(os.path.abspath(salida))
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(doc)

    print(f"\n  {len(secciones)} tablas · {n_cols} columnas · "
          f"{n_caut} con advertencia")
    if sin_glosa:
        print(f"  ⚠  {sin_glosa} columnas sin glosa — escribilas en "
              f"glosario.py")
    print(f"  → {salida}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--salida', default='variables_maestras.html')
    main(ap.parse_args().salida)
