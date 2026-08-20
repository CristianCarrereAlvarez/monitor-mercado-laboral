"""
Cómo se relacionan las áreas entre sí
======================================

Genera `visualizaciones/red_areas.html`: qué áreas aparecen pedidas en
el mismo aviso, en tres clasificaciones distintas.

QUÉ MIDE, EXACTAMENTE
  La unidad es el **aviso**, no la fila. Para cada aviso específico se
  toma el conjunto de áreas distintas a las que pertenecen los programas
  que pide, y cada par de ese conjunto suma un vínculo. Un aviso que
  pide `Ingeniería Comercial` y `Contador Auditor` —los dos en
  `041 Business and administration`— **no genera ningún vínculo**: es un
  área sola.

  De ahí sale el número que la página muestra arriba de todo y que hay
  que leer antes que el gráfico: **solo los avisos que piden más de un
  área generan un vínculo**, y son una minoría. El grosor de una cuerda
  es «cuántos avisos pidieron las dos», no «cuánta demanda hay».

LAS TRES CLASIFICACIONES
  `ISCED amplio` (11) e `ISCED estrecho` (29) son **los dos primeros
  niveles de la misma jerarquía**: 0413 ⊂ 041 ⊂ 04. Comparar el mismo
  gráfico en los dos niveles muestra qué vínculos son de verdad entre
  disciplinas y cuáles se disuelven al agregar — si dos campos estrechos
  del mismo amplio se piden juntos, el vínculo desaparece en el nivel de
  arriba.

  `Área SIES` (10) es **otra clasificación**, no un nivel de la
  anterior, y tiene una asimetría que conviene tener presente: solo la
  traen los programas. Las filas de campo ISCED —`Ingeniería`, `Diseño`—
  no tienen área SIES, así que ese gráfico se calcula sobre menos avisos.
  La página lo dice con la cifra.

ATRIBUCIÓN MÚLTIPLE
  Nueve entradas de trabajando abren a varios programas. Si esos
  programas caen en áreas distintas, la entrada sola inventa un vínculo
  que ningún empleador pidió: `Ingeniería de Diseño / Automatización
  Electrónica` toca `021 Arts` y `071 Engineering` por sí misma.

  **Por eso se excluyen por defecto**, y hay un interruptor para
  incluirlas. Es la misma lógica de `atribucion_multiple` en
  `aviso_programa.csv`: la marca está para que se pueda decidir, no para
  ignorarla.

Uso:
  ./red_areas.sh
  python red_areas.py --maestras <dir> --salida <archivo.html>
"""

import argparse, csv, html, itertools, json, os, sys
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

REPO = os.path.dirname(os.path.abspath(__file__))

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30

# (id, título, columna del código, columna/nombre legible)
NIVELES = [
    ('amplio',   'ISCED-F · campo amplio',   'isced_amplio_cod'),
    ('estrecho', 'ISCED-F · campo estrecho', 'isced_estrecho_cod'),
    ('sies',     'Área del conocimiento SIES', 'area_sies'),
]


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
    if not os.path.exists(M('aviso_programa.csv')):
        print("⛔  No existe aviso_programa.csv")
        print("    Lo escribe consolidar.py cuando encuentra "
              "maestras/homologacion.csv. Corré  ./procesar.sh\n")
        sys.exit(1)
    ap = leer(M('aviso_programa.csv'))
    isced = {r['codigo']: r['nombre']
             for r in leer(os.path.join(REPO, 'isced_f_2013.csv'), False)}

    especificos = [r for r in ap
                   if entero(r.get('n_entradas_declaradas_aviso')) <= UMBRAL]
    n_generico = len(ap) - len(especificos)

    datos = {}
    for nid, titulo, col in NIVELES:
        # dos versiones: con y sin las filas de atribución múltiple, para
        # que el interruptor no tenga que recalcular nada en el navegador.
        versiones = {}
        for etq, filas in (('sin', [r for r in especificos
                                    if r.get('atribucion_multiple') != 'True']),
                           ('con', especificos)):
            por_aviso = defaultdict(set)
            for r in filas:
                if r.get(col):
                    por_aviso[r['aviso_id']].add(r[col])
            grados = Counter()
            pares = Counter()
            for campos in por_aviso.values():
                for c in campos:
                    grados[c] += 1
                for a, b in itertools.combinations(sorted(campos), 2):
                    pares[(a, b)] += 1
            versiones[etq] = {
                'n_avisos': len(por_aviso),
                'n_multi': sum(1 for v in por_aviso.values() if len(v) > 1),
                'nodos': [{'id': c, 'nombre': isced.get(c, c), 'n': g}
                          for c, g in sorted(grados.items(),
                                             key=lambda kv: kv[0])],
                'lazos': [{'a': a, 'b': b, 'n': n}
                          for (a, b), n in sorted(pares.items(),
                                                  key=lambda kv: (-kv[1],
                                                                  kv[0]))],
            }
        datos[nid] = {'titulo': titulo, **versiones}
    return datos, len(especificos), n_generico


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relación entre áreas — Monitor Mercado Laboral</title>
<style>
:root{
  --ground:#E9ECEA; --surface:#F6F8F6; --surface-2:#FFFFFF; --ink:#16211E;
  --muted:#4E5C58; --line:#C3CCC8; --line-soft:#D8DFDB; --accent:#0E7A80;
  --accent-wash:#DCEBEA; --warn:#A8384E;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --display:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0E1513; --surface:#16201D; --surface-2:#1B2724; --ink:#DCE5E1;
  --muted:#869993; --line:#2E3D39; --line-soft:#22302C; --accent:#4CB8C0;
  --accent-wash:#123230; --warn:#E4788C;
}}
:root[data-theme="dark"]{
  --ground:#0E1513; --surface:#16201D; --surface-2:#1B2724; --ink:#DCE5E1;
  --muted:#869993; --line:#2E3D39; --line-soft:#22302C; --accent:#4CB8C0;
  --accent-wash:#123230; --warn:#E4788C;
}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);
 font-size:16px;line-height:1.62;margin:0;padding:0 20px 90px;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto}
header{padding:60px 0 30px;border-bottom:1px solid var(--line);
 margin-bottom:26px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
 text-transform:uppercase;color:var(--muted);margin:0 0 16px}
h1{font-family:var(--display);font-weight:600;font-size:clamp(30px,5vw,46px);
 line-height:1.08;letter-spacing:-.015em;margin:0 0 18px;text-wrap:balance}
.lede{font-size:17.5px;color:var(--muted);margin:0;max-width:62ch}
h2{font-family:var(--display);font-weight:600;font-size:23px;
 margin:46px 0 6px;letter-spacing:-.01em}
p{margin:0 0 14px;max-width:66ch}
code{font-family:var(--mono);font-size:.88em;background:var(--surface);
 border:1px solid var(--line-soft);border-radius:3px;padding:.1em .34em}
.controles{display:flex;gap:10px;flex-wrap:wrap;align-items:center;
 margin:0 0 18px}
button{padding:7px 13px;font-size:13px;font-family:inherit;
 border:1px solid var(--line);border-radius:7px;background:var(--surface-2);
 color:var(--ink);cursor:pointer}
button.on{background:var(--accent);color:var(--surface-2);
 border-color:var(--accent)}
label.chk{font-size:13px;color:var(--muted);display:flex;gap:6px;
 align-items:center;cursor:pointer;margin-left:6px}
.lectura{border-left:3px solid var(--accent);background:var(--surface);
 padding:14px 18px;margin:0 0 22px;font-size:14.5px;border-radius:0 3px 3px 0}
.lectura b{font-variant-numeric:tabular-nums}
.panel{display:grid;grid-template-columns:minmax(0,1fr) 250px;gap:24px;
 align-items:start}
.figbox{background:var(--surface);border:1px solid var(--line);
 border-radius:4px;padding:10px}
svg{display:block;width:100%;height:auto}
.nodo{fill:var(--surface-2);stroke:var(--accent);stroke-width:1.5;
 cursor:pointer}
.nodo.apagado{stroke:var(--line);opacity:.45}
.etq{font-family:var(--mono);font-size:9.5px;fill:var(--ink);cursor:pointer}
.etq.apagado{fill:var(--muted);opacity:.5}
.etq-n{font-family:var(--mono);font-size:8.5px;fill:var(--muted)}
.lazo{fill:none;stroke:var(--accent);opacity:.3;stroke-linecap:round}
.lazo.viva{opacity:.85}
.lazo.apagado{opacity:.06}
.rank{font-size:13.5px}
.rank h3{font-family:var(--mono);font-size:11px;letter-spacing:.09em;
 text-transform:uppercase;color:var(--muted);margin:0 0 10px;font-weight:600}
.rank .f{display:grid;grid-template-columns:34px 1fr;gap:8px;padding:2px 0;
 align-items:baseline;cursor:pointer}
.rank .f:hover{color:var(--accent)}
.rank .f b{font-variant-numeric:tabular-nums;text-align:right;
 font-weight:600}
.rank .f span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
 font-size:12.5px}
.rank .f i{color:var(--muted);font-style:normal}
.vacio{color:var(--muted);font-size:13.5px}
table{border-collapse:collapse;font-family:var(--mono);font-size:10px;
 margin-top:10px}
th,td{padding:0;text-align:center}
th.v{writing-mode:vertical-rl;transform:rotate(180deg);height:74px;
 padding:3px 0;color:var(--muted);font-weight:400}
th.h{text-align:right;padding-right:7px;color:var(--muted);font-weight:400;
 white-space:nowrap}
td.c{width:19px;height:19px;border:1px solid var(--surface)}
td.c span{display:block;width:100%;height:100%;border-radius:2px}
td.diag{color:var(--muted);font-size:8.5px}
.mwrap{overflow-x:auto}
footer{border-top:1px solid var(--line);padding-top:20px;margin-top:56px;
 font-family:var(--mono);font-size:12px;color:var(--muted)}
@media (max-width:900px){.panel{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
<header>
  <p class="eyebrow">Monitor Mercado Laboral Chile</p>
  <h1>Qué áreas se piden juntas</h1>
  <p class="lede">Dos áreas quedan unidas cuando un mismo aviso pide
  programas de las dos. El grosor de la cuerda es <b>cuántos avisos</b>
  las pidieron juntas — no cuánta demanda hay en ninguna de ellas.</p>
</header>

<div class="controles">
  <button data-niv="amplio" class="on">ISCED amplio</button>
  <button data-niv="estrecho">ISCED estrecho</button>
  <button data-niv="sies">Área SIES</button>
  <label class="chk"><input type="checkbox" id="multi">
    incluir atribución múltiple</label>
</div>

<div class="lectura" id="lectura"></div>

<div class="panel">
  <div class="figbox"><svg id="red" viewBox="0 0 760 640"></svg></div>
  <div class="rank">
    <h3>Los pares más frecuentes</h3>
    <div id="pares"></div>
  </div>
</div>

<p class="vacio" id="sinnombre"></p>

<h2>La matriz completa</h2>
<p>El gráfico muestra los vínculos más gruesos; la matriz los muestra
todos, incluidos los de un solo aviso. En la diagonal, en gris, va el
total de avisos que tocan esa área — no es un vínculo.</p>
<div class="mwrap" id="matriz"></div>

<h2>Cómo leerlo sin equivocarse</h2>
<p><b>Un aviso que pide dos programas de la misma área no genera ningún
vínculo.</b> Pedir <code>Ingeniería Comercial</code> y
<code>Contador Auditor</code> es pedir dos veces
<code>041 Business and administration</code>. Por eso la cifra de arriba
importa más que el dibujo: solo una minoría de los avisos aporta algo a
este gráfico.</p>
<p><b>Amplio y estrecho son dos niveles de lo mismo</b> —
<code>0413 ⊂ 041 ⊂ 04</code>— así que conviene mirarlos juntos. Un
vínculo que existe en estrecho y desaparece en amplio era, en realidad,
movimiento adentro de una misma disciplina.</p>
<p><b>El área SIES se calcula sobre menos avisos</b>, y no es un defecto
sino una consecuencia: solo la traen los programas. Cuando el aviso
nombra un campo —<code>Ingeniería</code>, <code>Diseño</code>— hay
código ISCED pero no área SIES.</p>
<p><b>La atribución múltiple está excluida por defecto.</b> Nueve
entradas de trabajando abren a varios programas, y si esos programas
caen en áreas distintas la entrada sola inventa un vínculo que ningún
empleador pidió. El interruptor las suma para ver cuánto cambian.</p>

<footer>Generado por <code>red_areas.py</code> desde
<code>aviso_programa.csv</code> · __DIR__</footer>
</div>

<script>
const D = __DATOS__;
let nivel = 'amplio', conMulti = false, foco = null;

const esc = s => String(s).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const recortar = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
const vista = () => D[nivel][conMulti ? 'con' : 'sin'];

function pinta(){
  const v = vista(), N = v.nodos, L = v.lazos;
  const pct = v.n_avisos ? (v.n_multi * 100 / v.n_avisos) : 0;
  document.getElementById('lectura').innerHTML =
    `De los <b>${v.n_avisos}</b> avisos específicos que llegan a un área en
     esta clasificación, <b>${v.n_multi}</b> —el <b>${pct.toFixed(0)}%</b>—
     piden <b>más de una</b>. Son los únicos que generan un vínculo, y de
     ellos salen los <b>${L.length}</b> pares del gráfico.`;

  // ── círculo ──────────────────────────────────────────────────
  const cx = 380, cy = 320, R = 186, W = 760;
  const pos = {}, n = N.length;
  N.forEach((d, i) => {
    const a = -Math.PI / 2 + i * 2 * Math.PI / n;
    pos[d.id] = {x: cx + R * Math.cos(a), y: cy + R * Math.sin(a), a};
  });
  // El punto de control no va al centro exacto: si va, todas las cuerdas
  // se amontonan en un mismo nudo y no se distingue ninguna. Tirando un
  // tercio hacia el punto medio, las cortas se abren y las largas siguen
  // cruzando el círculo.
  const K = 0.32;
  const maxN = Math.max(1, ...N.map(d => d.n));
  const maxL = Math.max(1, ...L.map(d => d.n));
  let s = '';
  for(const l of L){
    const p = pos[l.a], q = pos[l.b];
    if(!p || !q) continue;
    const w = 1 + 7 * Math.sqrt(l.n / maxL);
    const cls = foco ? (l.a === foco || l.b === foco ? 'viva' : 'apagado') : '';
    const mx = cx + ((p.x + q.x) / 2 - cx) * K;
    const my = cy + ((p.y + q.y) / 2 - cy) * K;
    s += `<path class="lazo ${cls}" stroke-width="${w.toFixed(1)}"
      d="M${p.x.toFixed(1)},${p.y.toFixed(1)}
         Q${mx.toFixed(1)},${my.toFixed(1)} ${q.x.toFixed(1)},${q.y.toFixed(1)}"></path>`;
  }
  for(const d of N){
    const p = pos[d.id];
    const r = 5 + 11 * Math.sqrt(d.n / maxN);
    const off = r + 9, lado = Math.cos(p.a) < -0.05 ? 'end' : 'start';
    const tx = p.x + (lado === 'end' ? -off : off);
    const cls = foco && foco !== d.id ? 'apagado' : '';
    s += `<circle class="nodo ${cls}" data-id="${esc(d.id)}"
      cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r.toFixed(1)}"></circle>`;
    // El código solo no dice nada: «04» hay que buscarlo en otra parte.
    // El recorte se calcula con el espacio REAL que queda hasta el borde
    // del lienzo, que depende de dónde cayó el nodo en el círculo. Con
    // un largo fijo, los de los costados se salían del cuadro.
    const libre = (lado === 'end' ? tx : W - tx) - 6;
    const cabe = Math.max(4, Math.floor(libre / 5.7) - d.id.length - 3);
    const corto = d.nombre === d.id ? '' : recortar(d.nombre, cabe);
    s += `<text class="etq ${cls}" data-id="${esc(d.id)}" x="${tx.toFixed(1)}"
      y="${(p.y - 1).toFixed(1)}" text-anchor="${lado}">${esc(d.id)}${
        corto ? ' · ' + esc(corto) : ''}</text>`;
    s += `<text class="etq-n" x="${tx.toFixed(1)}" y="${(p.y + 10).toFixed(1)}"
      text-anchor="${lado}">${d.n} aviso${d.n === 1 ? '' : 's'}</text>`;
  }
  if(!L.length) s += `<text class="etq-n" x="380" y="320"
     text-anchor="middle">sin vínculos en esta vista</text>`;
  document.getElementById('red').innerHTML = s;

  // ── ranking ──────────────────────────────────────────────────
  const nom = Object.fromEntries(N.map(d => [d.id, d.nombre]));
  document.getElementById('pares').innerHTML = L.length
    ? L.slice(0, 16).map(l => `<div class="f" data-id="${esc(l.a)}"
        title="${esc(nom[l.a])} ↔ ${esc(nom[l.b])}">
        <b>${l.n}</b><span>${esc(recortar(nom[l.a], 17))} <i>↔</i>
        ${esc(recortar(nom[l.b], 17))}</span></div>`).join('')
    : '<p class="vacio">Ningún aviso pidió dos áreas distintas.</p>';

  // Un código sin nombre no se inventa: se dice que falta. Hoy pasa con
  // 078, que existe en ISCED-F pero no en la copia del proyecto.
  const anon = N.filter(d => d.nombre === d.id).map(d => d.id);
  document.getElementById('sinnombre').textContent = anon.length
    ? `Sin nombre en isced_f_2013.csv: ${anon.join(', ')}. El código es `
      + `correcto; lo que falta es la fila en la tabla del proyecto.`
    : '';

  // ── matriz ───────────────────────────────────────────────────
  const M = {};
  for(const l of L){ M[l.a + '|' + l.b] = l.n; M[l.b + '|' + l.a] = l.n; }
  let t = '<table><tr><th></th>' +
    N.map(d => `<th class="v">${esc(d.id)} ${esc(d.nombre)}</th>`).join('') +
    '</tr>';
  for(const f of N){
    t += `<tr><th class="h">${esc(f.id)} ${esc(f.nombre)}</th>`;
    for(const c of N){
      if(f.id === c.id){ t += `<td class="c diag">${f.n}</td>`; continue; }
      const v2 = M[f.id + '|' + c.id] || 0;
      const o = v2 ? (0.14 + 0.86 * Math.sqrt(v2 / maxL)).toFixed(2) : 0;
      t += `<td class="c"><span title="${esc(f.id)} ↔ ${esc(c.id)}: ${v2}"
        style="background:var(--accent);opacity:${o}"></span></td>`;
    }
    t += '</tr>';
  }
  document.getElementById('matriz').innerHTML = t + '</table>';
}

document.addEventListener('click', ev => {
  const b = ev.target.closest('button[data-niv]');
  if(b){
    nivel = b.dataset.niv; foco = null;
    document.querySelectorAll('button[data-niv]')
            .forEach(x => x.classList.toggle('on', x === b));
    return pinta();
  }
  const t = ev.target.closest('[data-id]');
  if(t){ foco = foco === t.dataset.id ? null : t.dataset.id; pinta(); }
});
document.getElementById('multi').addEventListener('change', e => {
  conMulti = e.target.checked; pinta();
});
pinta();
</script></body></html>
"""


def main(dir_maestras, salida):
    datos, n_esp, n_gen = construir(dir_maestras)
    pagina = (PAGINA
              .replace('__DATOS__', json.dumps(datos, ensure_ascii=False)
                       .replace('</', '<\\/'))
              .replace('__DIR__', html.escape(os.path.abspath(dir_maestras))))
    os.makedirs(os.path.dirname(os.path.abspath(salida)) or '.', exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(pagina)

    print("=" * 64)
    print("  RELACIÓN ENTRE ÁREAS")
    print("=" * 64)
    print(f"  filas de avisos específicos : {n_esp}")
    print(f"  filas de genéricos excluidas: {n_gen}")
    for nid, titulo, _ in NIVELES:
        v = datos[nid]['sin']
        pct = v['n_multi'] * 100 / max(v['n_avisos'], 1)
        print(f"\n  {titulo}")
        print(f"    {len(v['nodos'])} áreas · {v['n_avisos']} avisos · "
              f"{v['n_multi']} con más de una ({pct:.0f}%) · "
              f"{len(v['lazos'])} pares")
        for l in v['lazos'][:3]:
            print(f"      {l['n']:4d}  {l['a']} ↔ {l['b']}")
    print(f"\n  Archivo: {os.path.abspath(salida)}")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--salida', default='red_areas.html')
    a = ap.parse_args()
    main(a.maestras, a.salida)
