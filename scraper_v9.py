"""
Monitor Mercado Laboral Chile — v9 (captura)
=============================================
Responsabilidad única: BAJAR Y GUARDAR EL CRUDO. Nada más.

  scraper_v9.py   → crudo_{area}_{YYYY_MM}.jsonl   (una línea por aviso)
  consolidar.py   → maestras CSV con upsert acumulado

Por qué se separó en dos:
  El detalle de la API tiene 51 claves. v7 usaba ~20. Cada vez que
  inspeccionamos la respuesta apareció algo que valía la pena y no se
  había guardado (estadoOferta, instituciones, idEmpresa, habilidades…).
  Guardando el JSON íntegro, cualquier decisión posterior — homologación
  de carreras, nuevas variables, corrección de un parseo — se reprocesa
  desde disco sin volver a golpear el sitio.

Hallazgos que motivan v9 (verificados con sondas sobre la API):
  · `carreras` NO trae ID, solo nombreCarrera → homologación por string,
    y se hace después, en consolidar.py, no acá.
  · `estadoOferta` toma valores PUBLICADA / DESACTIVADA. La búsqueda
    devuelve ambos. Capturarlo permite medir duración de vacante.
  · `ofertaConfidencial` es un booleano explícito. En avisos
    confidenciales el detalle NO filtra el nombre: nombreEmpresaFantasia
    dice literalmente "Empresa Confidencial". La identidad se recupera
    por idCompany acumulado entre corridas.
  · `idCompany` e `idEmpresa` fueron biyectivos en la muestra. Se guardan
    ambos; idCompany es la clave (es la que usa urlLogo).
  · `instituciones` SÍ trae idInstitucion, y las listas son casi todas
    distintas entre avisos → es preferencia del empleador.
  · `habilidades` viene en ~17% de los avisos, con nombreNivel casi
    siempre vacío. Se captura igual, expectativas bajas.

Uso:
  python scraper_v9.py "Administración y Comercio"
  python scraper_v9.py Salud

Colab:
  !pip install playwright nest_asyncio
  !playwright install --with-deps chromium
  !python scraper_v9.py "Administración y Comercio"

Reanudable: si se corta, volver a lanzar el mismo comando. Lee el JSONL
existente y solo baja lo que falta.
"""

import asyncio, json, os, random, re, sys, unicodedata
from datetime import datetime
from playwright.async_api import async_playwright
from carreras_sies_2026 import CARRERAS_POR_AREA

try:
    import nest_asyncio; nest_asyncio.apply()
except ImportError:
    pass


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════

PAUSA_BUSQUEDA = (1.0, 2.5)
PAUSA_DETALLE  = (0.6, 1.4)
CONCURRENCIA   = 4
MAX_REINTENTOS = 3
DIR_CRUDO      = "crudo"

BASE       = "https://www.trabajando.cl"
API_SEARCH = f"{BASE}/api/searchjob"
API_DETAIL = BASE + "/api/ofertas/{id}"


def slug(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


async def pausa(rango):
    await asyncio.sleep(random.uniform(*rango))


# ══════════════════════════════════════════════════════════
# FASE 1 — BÚSQUEDA (candidatos)
# ══════════════════════════════════════════════════════════

async def buscar_termino(req, termino, idx, total):
    avisos, pagina = [], 1
    print(f"\n  [{idx}/{total}] '{termino}'")
    while True:
        try:
            r = await req.get(API_SEARCH, params={
                'palabraClave': termino, 'pagina': pagina,
                'orden': 'RANKING', 'tipoOrden': 'DESC'}, timeout=25000)
            if r.status != 200:
                print(f"    pág {pagina}: HTTP {r.status} — corto")
                break
            data = await r.json()
            ofertas = data.get('ofertas', [])
            if not ofertas:
                break
            n_pags = data.get('cantidadPaginas', 1)
            print(f"    pág {pagina}/{n_pags}: {len(ofertas)} "
                  f"(total {data.get('cantidadRegistros','?')})")
            avisos.extend(ofertas)
            if pagina >= n_pags:
                break
            pagina += 1
            await pausa(PAUSA_BUSQUEDA)
        except Exception as e:
            print(f"    error pág {pagina}: {e}")
            break
    print(f"    → {len(avisos)}")
    return avisos


# ══════════════════════════════════════════════════════════
# FASE 2 — DETALLE
# ══════════════════════════════════════════════════════════

async def obtener_detalle(req, id_oferta):
    """(detalle|None, ok, motivo)"""
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            r = await req.get(API_DETAIL.format(id=id_oferta), timeout=25000)
            if r.status == 200:
                return await r.json(), True, None
            if r.status in (429, 500, 502, 503, 504):
                espera = 2 ** intento + random.uniform(0, 1.5)
                print(f"      {id_oferta}: HTTP {r.status}, reintento "
                      f"{intento}/{MAX_REINTENTOS} en {espera:.1f}s")
                await asyncio.sleep(espera)
                continue
            return None, False, f"http_{r.status}"
        except Exception as e:
            if intento == MAX_REINTENTOS:
                return None, False, f"exc_{type(e).__name__}"
            await asyncio.sleep(2 ** intento)
    return None, False, "max_reintentos"


def ids_ya_bajados(path):
    hechos = set()
    if not os.path.exists(path):
        return hechos
    with open(path, encoding='utf-8') as f:
        for linea in f:
            try:
                r = json.loads(linea)
                if r.get('detalle_ok'):
                    hechos.add(r['aviso_id'])
            except Exception:
                continue      # línea truncada por una caída: se reintenta
    print(f"  Crudo existente: {len(hechos)} avisos completos")
    return hechos


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

async def main(area):
    if area not in CARRERAS_POR_AREA:
        print(f"Área desconocida: {area!r}")
        print("Opciones:")
        for a in CARRERAS_POR_AREA:
            print(f"  {a}")
        sys.exit(1)

    terminos = list(CARRERAS_POR_AREA[area].keys())
    inicio   = datetime.now()
    periodo  = inicio.strftime('%Y_%m')
    fecha    = inicio.strftime('%Y-%m-%d')

    os.makedirs(DIR_CRUDO, exist_ok=True)
    path = os.path.join(DIR_CRUDO, f"crudo_{slug(area)}_{periodo}.jsonl")

    print("\n" + "=" * 64)
    print("  MONITOR MERCADO LABORAL — v9 (captura)")
    print(f"  {inicio.strftime('%Y-%m-%d %H:%M')}  |  {area}")
    print(f"  {len(terminos)} términos  →  {path}")
    print("=" * 64)

    hechos = ids_ya_bajados(path)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
        ctx = await browser.new_context(
            user_agent=('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'),
            locale='es-CL', timezone_id='America/Santiago',
            viewport={'width': 1280, 'height': 800})
        page = await ctx.new_page()

        print("\n  Estableciendo sesión...")
        await page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        try:
            link = await page.query_selector('.cookies-msg a')
            if link and await link.is_visible():
                await link.click(); await page.wait_for_timeout(500)
                print("  ✓ cookies")
        except Exception:
            pass

        req = ctx.request

        # ── FASE 1 ────────────────────────────────────────────
        print(f"\n{'='*64}\n  FASE 1 — búsqueda\n{'='*64}")
        listado, por_termino = {}, {}
        for i, t in enumerate(terminos, 1):
            for o in await buscar_termino(req, t, i, len(terminos)):
                idf = o.get('idOferta')
                if idf is None:
                    continue
                listado.setdefault(idf, o)
                por_termino.setdefault(idf, set()).add(t)
            await pausa(PAUSA_BUSQUEDA)

        ids = [i for i in listado if i not in hechos]
        print(f"\n  Candidatos únicos : {len(listado)}")
        print(f"  Ya en crudo       : {len(listado) - len(ids)}")
        print(f"  Por bajar         : {len(ids)}")

        # ── FASE 2 ────────────────────────────────────────────
        print(f"\n{'='*64}\n  FASE 2 — detalle (concurrencia {CONCURRENCIA})"
              f"\n{'='*64}")

        sem  = asyncio.Semaphore(CONCURRENCIA)
        lock = asyncio.Lock()
        fh   = open(path, 'a', encoding='utf-8')
        n    = {'hechos': 0, 'fallos': 0, 'desact': 0}

        async def worker(idf):
            async with sem:
                detalle, ok, motivo = await obtener_detalle(req, idf)
                registro = {
                    'aviso_id':       idf,
                    'fecha_scraping': fecha,
                    'periodo':        periodo,
                    'area_scraping':  area,
                    'terminos':       sorted(por_termino.get(idf, [])),
                    'detalle_ok':     ok,
                    'detalle_motivo': motivo,
                    'listado':        listado[idf],
                    'detalle':        detalle,
                }
                async with lock:
                    fh.write(json.dumps(registro, ensure_ascii=False) + '\n')
                    fh.flush()
                    n['hechos'] += 1
                    if not ok:
                        n['fallos'] += 1
                    elif (detalle or {}).get('estadoOferta') == 'DESACTIVADA':
                        n['desact'] += 1
                    if n['hechos'] % 50 == 0 or n['hechos'] == len(ids):
                        print(f"    {n['hechos']}/{len(ids)}  "
                              f"(fallos {n['fallos']}, desactivadas {n['desact']})")
                await pausa(PAUSA_DETALLE)

        await asyncio.gather(*(worker(i) for i in ids))
        fh.close()
        await browser.close()

    mins = int((datetime.now() - inicio).total_seconds() // 60)
    print(f"\n{'='*64}")
    print(f"  CAPTURA COMPLETA — {area}   ({mins} min)")
    print(f"  Avisos bajados en esta corrida : {n['hechos']}")
    print(f"    fallidos                     : {n['fallos']}")
    print(f"    DESACTIVADA                  : {n['desact']}")
    print(f"  Archivo: {path}  "
          f"({os.path.getsize(path)/1024/1024:.1f} MB)")
    print(f"\n  Siguiente paso:  python consolidar.py")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scraper_v9.py \"<Área>\"\n")
        print("Áreas disponibles:")
        for a, c in CARRERAS_POR_AREA.items():
            print(f"  {len(c):3d} términos  {a}")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
