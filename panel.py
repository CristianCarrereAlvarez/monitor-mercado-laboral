"""
Panel de homologación: una página HTML con la evidencia ya calculada
====================================================================

Genera `panel_homologacion.html`, un archivo autocontenido que se abre
con doble clic y muestra los 528 nombres de `carrera_trabajando` con
todo lo que hace falta para decidir a qué carrera SIES corresponde cada
uno.

POR QUÉ UNA PÁGINA Y NO UNA CONSULTA
  `mirar.py` contesta la pregunta de a un nombre por vez. Pero la
  homologación es la MISMA pregunta 405 veces, así que conviene
  calcularla toda de una y tenerla al lado de la planilla. Sin terminal,
  sin entorno que levantar, sin internet, y sobrevive a apagar la
  máquina.

  La contra: es una foto. Cuando llegue la corrida de septiembre hay que
  regenerarla. No es grave, porque la taxonomía saturó en 528 nombres.

QUÉ MUESTRA, Y POR QUÉ ESO
  Lo decisivo son las **carreras co-declaradas**: si un nombre aparece
  una y otra vez junto a otros de la misma familia, el empleador está
  diciendo a cuál pertenece. Eso es evidencia. El parecido de strings no
  lo es — la columna `sugerencia` le propone "Ingeniería Civil
  Industrial" a "Ingeniería Civil", que son carreras distintas.

  El nivel académico está para decidir `nivel_condicion`: si un nombre
  se reparte entre universitaria y técnica, probablemente sea un caso
  1:N y haya que partir la fila.

  Los avisos genéricos quedan fuera de todos los conteos. Uno que
  declara 504 carreras volvería a todas co-declaradas de todo.

Uso:
  ./panel.sh
  python panel.py --maestras <dir> --salida <archivo.html>
"""

import argparse, csv, html, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30

try:
    from carreras_sies_2026 import CARRERAS_POR_AREA
except Exception:
    CARRERAS_POR_AREA = {}

TOPE_CO, TOPE_CARGO, TOPE_EMP, TOPE_EJ = 15, 10, 8, 5


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


def leer(path, obligatorio=True):
    if not os.path.exists(path):
        if obligatorio:
            print(f"⛔  No existe {path}")
            sys.exit(1)
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def construir(dir_maestras):
    M = lambda n: os.path.join(dir_maestras, n)
    ac = leer(M('aviso_carrera.csv'))
    hom = {r['carrera_trabajando']: r
           for r in leer(M('homologacion_carreras.csv'), obligatorio=False)
           if r.get('nivel_condicion', '*') in ('*', '')}

    # pares declarados de avisos específicos
    decl = defaultdict(set)       # nombre -> ids
    decl_tot = Counter()          # nombre -> avisos totales (con genéricos)
    por_aviso = defaultdict(set)  # id -> nombres
    for f in ac:
        if f.get('fuente') != 'declarada':
            continue
        nombre = f.get('carrera_trabajando') or ''
        if not nombre:
            continue
        decl_tot[nombre] += 1
        if entero(f.get('n_carreras_declaradas_aviso')) > UMBRAL:
            continue
        decl[nombre].add(f['aviso_id'])
        por_aviso[f['aviso_id']].add(nombre)

    # datos del aviso: streaming, avisos.csv pesa decenas de MB
    interesan = set(por_aviso)
    info = {}
    with open(M('avisos.csv'), encoding='utf-8-sig', newline='') as f:
        for a in csv.DictReader(f):
            if a['aviso_id'] in interesan:
                info[a['aviso_id']] = (
                    a.get('titulo') or '',
                    a.get('nivel_academico') or '',
                    a.get('empresa_nombre')
                    or f"[confidencial {a.get('empresa_id')}]",
                    a.get('url') or '',
                    a.get('areas_scraping') or '')

    sies = sorted({s for c in CARRERAS_POR_AREA.values() for s in c.values()})
    sies_norm = {normalizar(s): s for s in sies}

    fichas = []
    for nombre, ids in decl.items():
        co = Counter()
        for i in ids:
            for otro in por_aviso[i]:
                if otro != nombre:
                    co[otro] += 1
        niv, carg, emp, area = Counter(), Counter(), Counter(), Counter()
        ejemplos = []
        for i in sorted(ids):
            d = info.get(i)
            if not d:
                continue
            t, n_, e, u, ars = d
            niv[n_ or '(sin nivel)'] += 1
            carg[t] += 1
            emp[e] += 1
            for x in ars.split('|'):
                if x.strip():
                    area[x.strip()] += 1
            if len(ejemplos) < TOPE_EJ:
                ejemplos.append({'t': t, 'n': n_, 'u': u})

        h = hom.get(nombre, {})
        fichas.append({
            'nombre': nombre,
            'esp': len(ids),
            'tot': decl_tot[nombre],
            'sies': h.get('carrera_sies', ''),
            'area_sies': h.get('area_sies', ''),
            'rel': h.get('tipo_relacion', ''),
            'quien': h.get('revisado_por', ''),
            'sug': h.get('sugerencia', ''),
            'score': h.get('score', ''),
            'exacto': sies_norm.get(normalizar(nombre), ''),
            'co': co.most_common(TOPE_CO),
            'niv': niv.most_common(),
            'carg': carg.most_common(TOPE_CARGO),
            'emp': emp.most_common(TOPE_EMP),
            'area': area.most_common(),
            'ej': ejemplos,
        })

    # nombres que solo aparecen en avisos genéricos: no tienen evidencia
    for nombre, n in decl_tot.items():
        if nombre not in decl:
            h = hom.get(nombre, {})
            fichas.append({
                'nombre': nombre, 'esp': 0, 'tot': n,
                'sies': h.get('carrera_sies', ''),
                'area_sies': h.get('area_sies', ''),
                'rel': h.get('tipo_relacion', ''),
                'quien': h.get('revisado_por', ''),
                'sug': h.get('sugerencia', ''),
                'score': h.get('score', ''),
                'exacto': sies_norm.get(normalizar(nombre), ''),
                'co': [], 'niv': [], 'carg': [], 'emp': [], 'area': [],
                'ej': [],
            })

    fichas.sort(key=lambda f: (bool(f['sies']), -f['esp'], f['nombre']))
    return fichas, sies


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel de homologación — Monitor Mercado Laboral</title>
<style>
:root{--bg:#fbfaf8;--fg:#22201d;--tenue:#6b6560;--linea:#e5e0d8;
      --tarjeta:#fff;--acento:#7a4f2b;--ok:#2f6b46;--okbg:#e8f3ec;
      --pend:#8a5a00;--pendbg:#fdf2dc;--barra:#d9cfc0}
@media (prefers-color-scheme:dark){
 :root{--bg:#191715;--fg:#eae6e0;--tenue:#a09890;--linea:#33302c;
       --tarjeta:#211f1c;--acento:#d2a679;--ok:#8fd0a8;--okbg:#1e2f26;
       --pend:#e0b25f;--pendbg:#332a17;--barra:#4a443c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);
 border-bottom:1px solid var(--linea);padding:14px 20px 10px}
h1{margin:0 0 2px;font-size:17px;letter-spacing:.01em}
.meta{color:var(--tenue);font-size:12.5px;margin-bottom:10px}
.controles{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input[type=search]{flex:1;min-width:220px;padding:8px 11px;font-size:14px;
 border:1px solid var(--linea);border-radius:7px;background:var(--tarjeta);
 color:var(--fg)}
button{padding:7px 12px;font-size:13px;border:1px solid var(--linea);
 border-radius:7px;background:var(--tarjeta);color:var(--fg);cursor:pointer}
button.on{background:var(--acento);color:var(--bg);border-color:var(--acento)}
main{max-width:920px;margin:0 auto;padding:16px 20px 60px}
.ficha{background:var(--tarjeta);border:1px solid var(--linea);
 border-radius:10px;margin-bottom:9px;overflow:hidden}
.cab{display:flex;gap:12px;align-items:baseline;padding:11px 14px;
 cursor:pointer}
.cab:hover{background:rgba(125,125,125,.06)}
.n{font-weight:600;flex:1}
.cnt{color:var(--tenue);font-variant-numeric:tabular-nums;font-size:13px;
 white-space:nowrap}
.tag{font-size:11.5px;padding:2px 7px;border-radius:20px;white-space:nowrap}
.t-ok{background:var(--okbg);color:var(--ok)}
.t-pend{background:var(--pendbg);color:var(--pend)}
.cuerpo{display:none;padding:2px 14px 16px;border-top:1px solid var(--linea)}
.ficha.abierta .cuerpo{display:block}
h3{font-size:11.5px;text-transform:uppercase;letter-spacing:.07em;
 color:var(--tenue);margin:16px 0 6px;font-weight:600}
.fila{display:grid;grid-template-columns:46px 42px 1fr;gap:8px;
 align-items:center;padding:1px 0;font-size:13.5px}
.fila b{font-weight:600;font-variant-numeric:tabular-nums;text-align:right}
.fila i{color:var(--tenue);font-style:normal;font-variant-numeric:tabular-nums;
 text-align:right;font-size:12px}
.bar{height:13px;display:flex;align-items:center;gap:7px}
.bar span{display:block;height:7px;background:var(--barra);border-radius:2px;
 flex:none}
.txt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nota{color:var(--tenue);font-size:12.5px;margin:6px 0 0}
a{color:var(--acento)}
code{background:rgba(125,125,125,.14);padding:1px 5px;border-radius:4px;
 font-size:12.5px}
.vacio{color:var(--tenue);padding:30px 4px;text-align:center}
.sies{columns:2;column-gap:22px;font-size:13px;margin-top:6px}
.sies div{break-inside:avoid;padding:1px 0}
details{margin-top:22px;border-top:1px solid var(--linea);padding-top:12px}
summary{cursor:pointer;font-size:13px;color:var(--tenue)}
</style></head><body>
<header>
  <h1>Panel de homologación</h1>
  <div class="meta">__META__</div>
  <div class="controles">
    <input type="search" id="q" placeholder="Buscar nombre de carrera…"
           autocomplete="off">
    <button id="f-pend" class="on">Pendientes</button>
    <button id="f-todo">Todas</button>
    <button id="f-res">Resueltas</button>
    <span class="cnt" id="cuenta"></span>
  </div>
</header>
<main>
  <div id="lista"></div>
  <div class="vacio" id="vacio" style="display:none">Nada coincide.</div>
  <details>
    <summary>Las __NSIES__ carreras SIES, para copiar el nombre exacto</summary>
    <div class="sies">__SIES__</div>
  </details>
</main>
<script>
const D = __DATOS__;
const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')
                   .toLowerCase();
const esc = s => String(s).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function barras(pares, total){
  if(!pares.length) return '<p class="nota">Sin datos.</p>';
  const max = pares[0][1];
  return pares.map(([k,v]) =>
    `<div class="fila"><b>${v}</b><i>${(v*100/total).toFixed(0)}%</i>
     <div class="bar"><span style="width:${Math.max(3,v*90/max)}px"></span>
     <div class="txt">${esc(k)}</div></div></div>`).join('');
}

function cuerpo(f){
  let h = '';
  if(f.exacto) h += `<p class="nota">Coincide exactamente con la carrera
     SIES <code>${esc(f.exacto)}</code>.</p>`;
  if(f.sug) h += `<p class="nota">Sugerencia automática:
     <code>${esc(f.sug)}</code> (score ${esc(f.score)}) —
     <b>no es una decisión</b>, solo parecido de palabras.</p>`;
  if(f.sies) h += `<p class="nota">Ya homologada a
     <code>${esc(f.sies)}</code> · ${esc(f.area_sies)} ·
     ${esc(f.rel)} ${f.quien ? '· ' + esc(f.quien) : ''}</p>`;
  if(!f.esp){
    h += `<p class="nota">Solo aparece en avisos genéricos, que declaran
      medio catálogo. No hay evidencia para decidir.</p>`;
    return h;
  }
  h += `<h3>Se declara junto con</h3>` + barras(f.co, f.esp);
  h += `<p class="nota">Es la evidencia más fuerte: con qué familia la
    agrupan los propios empleadores.</p>`;
  h += `<h3>Nivel académico</h3>` + barras(f.niv, f.esp);
  if(f.niv.length > 1) h += `<p class="nota">Si se reparte entre
    universitaria y técnica, puede necesitar dos filas con
    <code>nivel_condicion</code> distinto.</p>`;
  h += `<h3>Cargos reales</h3>` + barras(f.carg, f.esp);
  h += `<h3>Empleadores</h3>` + barras(f.emp, f.esp);
  h += `<h3>Áreas del monitor</h3>` + barras(f.area, f.esp);
  h += `<h3>Avisos de ejemplo</h3>` + f.ej.map(e =>
    `<div class="fila" style="grid-template-columns:1fr">
     <div><a href="${esc(e.u)}" target="_blank">${esc(e.t)}</a>
     <span class="cnt"> · ${esc(e.n||'sin nivel')}</span></div></div>`
    ).join('');
  return h;
}

let filtro = 'pend';
function pinta(){
  const q = norm(document.getElementById('q').value.trim());
  const vis = D.filter(f => {
    if(filtro==='pend' && f.sies) return false;
    if(filtro==='res' && !f.sies) return false;
    return !q || norm(f.nombre).includes(q);
  });
  document.getElementById('cuenta').textContent =
    vis.length + ' de ' + D.length;
  document.getElementById('vacio').style.display = vis.length ? 'none':'block';
  document.getElementById('lista').innerHTML = vis.map((f,i) =>
    `<div class="ficha" data-i="${D.indexOf(f)}">
       <div class="cab">
         <span class="n">${esc(f.nombre)}</span>
         <span class="tag ${f.sies?'t-ok':'t-pend'}">${
            f.sies ? 'homologada' : 'pendiente'}</span>
         <span class="cnt">${f.esp} avisos</span>
       </div>
       <div class="cuerpo"></div>
     </div>`).join('');
}

document.addEventListener('click', ev => {
  const cab = ev.target.closest('.cab');
  if(!cab) return;
  const ficha = cab.parentElement;
  const c = ficha.querySelector('.cuerpo');
  if(!ficha.classList.contains('abierta') && !c.innerHTML)
    c.innerHTML = cuerpo(D[+ficha.dataset.i]);
  ficha.classList.toggle('abierta');
});
document.getElementById('q').addEventListener('input', pinta);
for(const [id,v] of [['f-pend','pend'],['f-todo','todo'],['f-res','res']])
  document.getElementById(id).addEventListener('click', e => {
    filtro = v;
    document.querySelectorAll('.controles button')
            .forEach(b => b.classList.remove('on'));
    e.target.classList.add('on');
    pinta();
  });
pinta();
</script></body></html>
"""


def main(dir_maestras, salida):
    fichas, sies = construir(dir_maestras)
    pend = [f for f in fichas if not f['sies']]
    tot_esp = sum(f['esp'] for f in fichas) or 1

    s_p = '' if len(pend) == 1 else 's'
    s_h = '' if len(fichas) - len(pend) == 1 else 's'
    meta = (f"{len(fichas)} nombres de carrera · "
            f"{len(fichas) - len(pend)} homologada{s_h} · "
            f"<b>{len(pend)} pendiente{s_p}</b> · "
            f"genéricos excluidos (más de {UMBRAL} carreras declaradas) · "
            f"generado desde {html.escape(os.path.abspath(dir_maestras))}")

    datos = json.dumps(fichas, ensure_ascii=False).replace('</', '<\\/')
    pagina = (PAGINA
              .replace('__META__', meta)
              .replace('__NSIES__', str(len(sies)))
              .replace('__SIES__',
                       ''.join(f'<div>{html.escape(s)}</div>' for s in sies))
              .replace('__DATOS__', datos))

    os.makedirs(os.path.dirname(os.path.abspath(salida)) or '.', exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(pagina)

    acum, hitos = 0, {}
    for i, f in enumerate(sorted(pend, key=lambda x: -x['esp']), 1):
        acum += f['esp']
        if i in (25, 50, 100, 200):
            hitos[i] = acum
    ya = tot_esp - sum(f['esp'] for f in pend)

    print("=" * 64)
    print("  PANEL DE HOMOLOGACIÓN")
    print("=" * 64)
    print(f"  nombres        : {len(fichas)}")
    print(f"  homologadas    : {len(fichas) - len(pend)}")
    print(f"  pendientes     : {len(pend)}")
    print(f"  cobertura ya resuelta: {ya * 100 / tot_esp:.1f}% "
          f"de las menciones específicas")
    if hitos:
        print(f"\n  si revisás las primeras N pendientes:")
        for n, a in hitos.items():
            print(f"    {n:>4} filas  →  {(ya + a) * 100 / tot_esp:5.1f}%")
    print(f"\n  Archivo: {os.path.abspath(salida)}")
    print(f"  Abrilo con doble clic. No necesita internet ni servidor.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--salida', default='panel_homologacion.html')
    a = ap.parse_args()
    main(a.maestras, a.salida)
