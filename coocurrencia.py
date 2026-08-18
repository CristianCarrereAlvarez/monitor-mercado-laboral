"""
Co-ocurrencia de programas: qué se pide junto con qué
=====================================================

Genera `coocurrencia_programas.html`, un archivo autocontenido que se
abre con doble clic y muestra, para cada **programa propio**, dos cosas:

  1. con qué OTROS programas lo piden en el mismo aviso;
  2. qué nombres de `carrera_trabajando` se homologaron ahí.

LA UNIDAD CAMBIÓ, Y ESO CAMBIA LO QUE MIDE
  La versión anterior tenía como unidad `carrera_trabajando`, el texto
  que escribe trabajando.cl. Servía para decidir la homologación —a qué
  familia pertenece un nombre— y ese trabajo ya está hecho.

  Ahora la unidad es el programa formativo. `Ingeniería en Computación
  e Informática` reúne los nombres que antes estaban dispersos en
  `Ingeniería en Informática / Sistemas`, `Ingeniería en Gestión e
  Informática` y otros, así que la co-ocurrencia deja de estar partida
  por variantes de redacción y pasa a decir algo sobre **formaciones**.

  El segundo ranking existe para no perder de vista de dónde sale cada
  número: si un programa junta veinte nombres de aviso, conviene verlo.

QUÉ QUEDA AFUERA, Y CUÁNTO ES
  - **Los avisos genéricos.** Uno que declara 504 carreras volvería a
    todos los programas co-ocurrentes de todos.
  - **Los campos ISCED.** Cuando el aviso nombra `Ingeniería` o
    `Diseño` no nombra un programa, y mezclarlos como si fueran una
    unidad más pondría un campo al lado de una carrera. Es el 7,9% de
    las menciones específicas; la cifra exacta la imprime el script.
  - Los niveles sueltos (`MBA`), los cargos (`Paramédico`) y lo no
    informativo: no nombran ninguna formación.

LA BASE DE LOS PORCENTAJES
  Los avisos específicos que piden ese programa. **La columna suma más
  de 100%** y está bien: un aviso pide varios programas y cuenta en
  todos. La página lee en palabras la primera fila de cada ranking, en
  vez de explicarlo en abstracto.

Uso:
  ./coocurrencia.sh
  python coocurrencia.py --maestras <dir> --salida <archivo.html>
"""
import argparse, csv, html, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

try:
    from consolidar import UMBRAL_AVISO_GENERICO as UMBRAL
except Exception:
    UMBRAL = 30

try:
    from homologacion import Homologacion, clave
except Exception:
    Homologacion, clave = None, lambda s: s

TOPE_CO = 15


def normalizar(s):
    if not isinstance(s, str):
        return ''
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def top(contador, n=None):
    """Los mayores, con desempate alfabético.

    `Counter.most_common` desempata por orden de inserción, y acá se
    inserta recorriendo conjuntos: dos corridas sobre los mismos datos
    darían archivos distintos. Un archivo generado que cambia sin que
    cambien los datos es ruido en el diff y desconfianza en el lector.
    """
    pares = sorted(contador.items(), key=lambda kv: (-kv[1], kv[0]))
    return pares[:n] if n else pares


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
    """Lee `aviso_programa.csv` — la tabla donde ya aterrizó la
    homologación— y arma una ficha por programa.

    No vuelve a resolver el join: eso lo hizo `consolidar.py`. Acá solo
    se cuenta. Si el archivo no está, el mensaje dice qué correr.
    """
    M = lambda n: os.path.join(dir_maestras, n)
    if not os.path.exists(M('aviso_programa.csv')):
        print("⛔  No existe aviso_programa.csv")
        print("    Lo escribe consolidar.py cuando encuentra "
              "maestras/homologacion.csv.")
        print("    Corré  ./procesar.sh  y volvé a intentar.\n")
        sys.exit(1)
    ap = leer(M('aviso_programa.csv'))

    prog_por_aviso = defaultdict(set)   # aviso -> {programa}
    ids = defaultdict(set)             # programa -> {aviso}
    origen = defaultdict(Counter)      # programa -> {nombre de aviso: avisos}
    meta = {}                          # programa -> área e ISCED
    n_campo = n_generico = 0

    for f in ap:
        if entero(f.get('n_carreras_declaradas_aviso')) > UMBRAL:
            n_generico += 1
            continue
        if f.get('tipo_entrada') != 'programa_propio':
            n_campo += 1
            continue
        p, a = f['programa_propio'], f['aviso_id']
        ids[p].add(a)
        prog_por_aviso[a].add(p)
        meta.setdefault(p, (f.get('area_sies') or '',
                            f.get('isced_amplio_cod') or ''))
        for nombre in (f.get('carreras_origen') or '').split(' | '):
            if nombre.strip():
                origen[p][nombre.strip()] += 1

    # Los programas del catálogo que ningún aviso específico pide. No es
    # lo mismo que "no existen": es que no aparecieron. Se listan aparte
    # para que la ausencia se vea, en vez de faltar en silencio.
    sin_avisos = []
    if Homologacion:
        hom = Homologacion.cargar(M('homologacion.csv'), obligatoria=False)
        if hom:
            todos = {r['programa_propio'] for r in hom.filas
                     if r.get('programa_propio', '').strip()}
            sin_avisos = sorted(todos - set(ids))

    fichas = []
    for p, avisos in ids.items():
        co = Counter()
        for a in avisos:
            for otro in prog_por_aviso[a]:
                if otro != p:
                    co[otro] += 1
        area, isced = meta[p]
        fichas.append({
            'nombre': p,
            'area': area,
            'isced': isced,
            'esp': len(avisos),
            'co': top(co, TOPE_CO),
            'org': top(origen[p], TOPE_CO),
            'n_org': len(origen[p]),
        })

    fichas.sort(key=lambda f: (-f['esp'], f['nombre']))
    return fichas, sin_avisos, n_campo, n_generico


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Co-ocurrencia de programas — Monitor Mercado Laboral</title>
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
select{padding:8px 10px;font-size:13px;border:1px solid var(--linea);
 border-radius:7px;background:var(--tarjeta);color:var(--fg)}
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
.lectura{margin:2px 0 9px;font-size:13.5px;line-height:1.5;
 border-left:3px solid var(--barra);padding-left:10px}
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
  <h1>Co-ocurrencia de programas formativos</h1>
  <div class="meta">__META__</div>
  <div class="controles">
    <input type="search" id="q"
           placeholder="Buscar programa, o un nombre de aviso homologado ahí…"
           autocomplete="off">
    <select id="area"><option value="">todas las áreas</option>__AREAS__</select>
    <span class="cnt" id="cuenta"></span>
  </div>
</header>
<main>
  <div id="lista"></div>
  <div class="vacio" id="vacio" style="display:none">Nada coincide.</div>
  <details>
    <summary>__NSIN__ programas del catálogo que ningún aviso específico
      pide</summary>
    <p class="nota">No significa que no exista demanda: significa que en
      esta corrida ningún aviso los nombró de forma específica.</p>
    <div class="sies">__SIN__</div>
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
  if(f.co.length){
    const [k, v] = f.co[0];
    h += `<h3>Se pide junto con — otros programas</h3>`;
    h += `<p class="lectura">De los <b>${f.esp}</b> avisos que piden
      <b>${esc(f.nombre)}</b>, <b>${v}</b> —el
      ${(v*100/f.esp).toFixed(0)}%— piden <b>además</b> ${esc(k)}.</p>`;
    h += barras(f.co, f.esp);
  } else {
    h += `<h3>Se pide junto con — otros programas</h3>`;
    h += `<p class="nota">Ninguno: siempre se pide solo. Es señal fuerte
      de que el empleador tiene una formación concreta en mente.</p>`;
  }

  h += `<h3>Nombres de aviso homologados acá — ${f.n_org}</h3>`;
  if(f.org.length){
    const [k2, v2] = f.org[0];
    h += `<p class="lectura">De los <b>${f.esp}</b> avisos, <b>${v2}</b>
      llegaron acá porque el empleador escribió <b>${esc(k2)}</b>.</p>`;
    h += barras(f.org, f.esp);
  }
  if(f.n_org > f.org.length)
    h += `<p class="nota">… y ${f.n_org - f.org.length} nombres más, con
      menos avisos.</p>`;
  return h;
}

function pinta(){
  const q = norm(document.getElementById('q').value.trim());
  const ar = document.getElementById('area').value;
  // La búsqueda entra también por los nombres de aviso: el usuario
  // suele acordarse de "Analista Programador", no del programa.
  const vis = D.filter(f => {
    if(ar && f.area !== ar) return false;
    if(!q) return true;
    return norm(f.nombre).includes(q) ||
           f.org.some(([k]) => norm(k).includes(q));
  });
  document.getElementById('cuenta').textContent =
    vis.length + ' de ' + D.length;
  document.getElementById('vacio').style.display = vis.length ? 'none':'block';
  document.getElementById('lista').innerHTML = vis.map(f =>
    `<div class="ficha" data-i="${D.indexOf(f)}">
       <div class="cab">
         <span class="n">${esc(f.nombre)}</span>
         <span class="tag t-ok">${esc(f.area)}</span>
         <span class="cnt">${f.esp} avisos · ${f.n_org} nombres</span>
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
document.getElementById('area').addEventListener('change', pinta);
pinta();
</script></body></html>
"""


def main(dir_maestras, salida):
    fichas, sin_avisos, n_campo, n_generico = construir(dir_maestras)
    tot_esp = sum(f['esp'] for f in fichas) or 1
    areas = sorted({f['area'] for f in fichas if f['area']})

    meta = (f"{len(fichas)} programas · {tot_esp} pares aviso×programa · "
            f"genéricos excluidos (más de {UMBRAL} carreras declaradas) · "
            f"campos ISCED excluidos ({n_campo} filas) · "
            f"generado desde {html.escape(os.path.abspath(dir_maestras))}")

    datos = json.dumps(fichas, ensure_ascii=False).replace('</', '<\\/')
    pagina = (PAGINA
              .replace('__META__', meta)
              .replace('__AREAS__', ''.join(
                  f'<option>{html.escape(a)}</option>' for a in areas))
              .replace('__NSIN__', str(len(sin_avisos)))
              .replace('__SIN__', ''.join(
                  f'<div>{html.escape(p)}</div>' for p in sin_avisos))
              .replace('__DATOS__', datos))

    os.makedirs(os.path.dirname(os.path.abspath(salida)) or '.', exist_ok=True)
    with open(salida, 'w', encoding='utf-8') as f:
        f.write(pagina)

    print("=" * 64)
    print("  CO-OCURRENCIA DE PROGRAMAS FORMATIVOS")
    print("=" * 64)
    print(f"  programas con avisos   : {len(fichas)}")
    print(f"  sin ningún aviso       : {len(sin_avisos)}")
    print(f"  pares aviso×programa   : {tot_esp}")
    print(f"  filas de campo ISCED excluidas   : {n_campo}")
    print(f"  filas de avisos genéricos excluidas: {n_generico}")
    print(f"\n  los más pedidos:")
    for f in fichas[:10]:
        print(f"    {f['esp']:5d}  {f['nombre'][:44]:44s} "
              f"({f['n_org']} nombres de aviso)")
    print(f"\n  Archivo: {os.path.abspath(salida)}")
    print(f"  Abrilo con doble clic. No necesita internet ni servidor.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--maestras', default='maestras')
    ap.add_argument('--salida', default='coocurrencia_programas.html')
    a = ap.parse_args()
    main(a.maestras, a.salida)
