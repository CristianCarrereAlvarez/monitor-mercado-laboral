"""
Sonda — estructura real de la respuesta de /api/ofertas/{id}
============================================================
Objetivo: saber qué campos devuelve el detalle antes de decidir qué
persistir en v9. En particular:

  1. ¿Los objetos de `carreras` traen un ID propio?
     → si sí, la maestra de carreras y la homologación van contra el ID,
       no contra el string (inmune a renombres y tipeos).
  2. ¿Hay algún campo de rubro / sector / tamaño de empresa?
     → `rubro_empresa` está 100% nulo desde v7 y quizá el dato sí viene
       con otro nombre.
  3. ¿Qué otros campos se están descartando?

Busca un aviso vivo, baja su detalle y dumpea la estructura.
No guarda nada: imprime y listo.

Colab:
  Celda 1 (solo la primera vez)
    !pip install playwright nest_asyncio
    !playwright install --with-deps chromium
  Celda 2
    !python sonda_detalle.py
  (o pega el contenido directo en una celda)

Pegar la salida COMPLETA de vuelta.
"""

import asyncio, json
from playwright.async_api import async_playwright

try:
    import nest_asyncio; nest_asyncio.apply()
except ImportError:
    pass

BASE       = "https://www.trabajando.cl"
API_SEARCH = f"{BASE}/api/searchjob"
API_DETAIL = BASE + "/api/ofertas/{id}"

TERMINO = "Administración de Empresas"   # cualquiera con alto volumen


def tipo(v):
    if v is None:                 return "None"
    if isinstance(v, bool):       return "bool"
    if isinstance(v, int):        return "int"
    if isinstance(v, float):      return "float"
    if isinstance(v, str):        return f"str({len(v)})"
    if isinstance(v, list):       return f"list[{len(v)}]"
    if isinstance(v, dict):       return f"dict{{{len(v)}}}"
    return type(v).__name__


def muestra(v, n=90):
    if isinstance(v, str):
        v = v.replace("\n", " ")
        return v[:n] + ("…" if len(v) > n else "")
    if isinstance(v, (list, dict)):
        return ""
    return repr(v)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
        ctx = await browser.new_context(
            user_agent=('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'),
            locale='es-CL', timezone_id='America/Santiago')
        page = await ctx.new_page()
        await page.goto(BASE, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        req = ctx.request

        # ── 1. un aviso vivo ──────────────────────────────────────
        r = await req.get(API_SEARCH, params={
            'palabraClave': TERMINO, 'pagina': 1,
            'orden': 'RANKING', 'tipoOrden': 'DESC'}, timeout=25000)
        ofertas = (await r.json()).get('ofertas', [])
        if not ofertas:
            print("Sin resultados de búsqueda. Revisar el término.")
            await browser.close(); return

        # preferir uno que declare carreras: probamos hasta 6
        elegido = None
        for o in ofertas[:6]:
            d = await (await req.get(
                API_DETAIL.format(id=o['idOferta']), timeout=25000)).json()
            if d.get('carreras'):
                elegido = d
                break
            elegido = elegido or d
            await asyncio.sleep(1)

        detalle = elegido
        await browser.close()

    print("=" * 70)
    print(f"ID {detalle.get('idOferta')} — {detalle.get('nombreCargo')}")
    print("=" * 70)

    # ── 2. claves de primer nivel ─────────────────────────────────
    print("\n### CLAVES DE PRIMER NIVEL ###\n")
    for k in sorted(detalle):
        print(f"{k:38s} {tipo(detalle[k]):14s} {muestra(detalle[k])}")

    # ── 3. carreras: LA pregunta ──────────────────────────────────
    print("\n### carreras ###\n")
    cs = detalle.get('carreras') or []
    print(f"n = {len(cs)}")
    if cs:
        print("\nprimer elemento completo:")
        print(json.dumps(cs[0], ensure_ascii=False, indent=2))
        print("\nclaves presentes en TODOS los elementos:")
        comunes = set(cs[0])
        for c in cs[1:]:
            comunes &= set(c)
        print(sorted(comunes))
        print("\nprimeros 5 elementos:")
        for c in cs[:5]:
            print("  ", json.dumps(c, ensure_ascii=False))
    else:
        print("Este aviso no declara carreras. Volver a correr la sonda.")

    # ── 4. sub-objetos ────────────────────────────────────────────
    print("\n### SUB-OBJETOS Y LISTAS ###\n")
    for k, v in sorted(detalle.items()):
        if k == 'carreras':
            continue
        if isinstance(v, dict) and v:
            print(f"--- {k} (dict) ---")
            print(json.dumps(v, ensure_ascii=False, indent=2)[:1200])
            print()
        elif isinstance(v, list) and v:
            print(f"--- {k} (list[{len(v)}]) — primer elemento ---")
            print(json.dumps(v[0], ensure_ascii=False, indent=2)[:800])
            print()

    # ── 5. cualquier cosa que huela a empresa/rubro/tamaño ────────
    print("\n### CAMPOS RELACIONADOS A EMPRESA ###\n")
    pistas = ('empresa', 'company', 'rubro', 'sector', 'industri',
              'area', 'giro', 'tamano', 'tamaño', 'size', 'holding')
    hallazgos = []
    def escanear(obj, ruta=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                r = f"{ruta}.{k}" if ruta else k
                if any(p in k.lower() for p in pistas):
                    hallazgos.append(f"{r:45s} {tipo(v):14s} {muestra(v)}")
                escanear(v, r)
        elif isinstance(obj, list) and obj:
            escanear(obj[0], f"{ruta}[0]")
    escanear(detalle)
    print("\n".join(hallazgos) if hallazgos else "(ninguno)")

    print("\n" + "=" * 70)
    print("Pegar TODA esta salida de vuelta.")
    print("=" * 70)


asyncio.run(main())
