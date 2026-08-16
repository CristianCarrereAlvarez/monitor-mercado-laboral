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
  python scraper_v9.py Salud --sin-navegador

DOS MODOS DE SESIÓN
  Playwright se usaba solo para conseguir cookies; las llamadas siempre
  fueron HTTP. Medido en agosto 2026: la API responde 200 a una petición
  común desde una IP residencial, sin cookies. Así que el navegador es
  opcional.

    navegador  (por defecto)  Chromium headless establece la sesión.
    directo    --sin-navegador  urllib de la stdlib, sin dependencias.

  Si Playwright no está instalado o no soporta la plataforma, cae solo al
  modo directo y lo avisa. Chromium no corre en macOS 12, por ejemplo.

SI EL SITIO RECHAZA
  Akamai bloquea rangos de datacenter — Colab entre ellos — con 403 en
  todo, incluida la portada. Antes esa corrida terminaba anunciando
  "CAPTURA COMPLETA" con cero avisos. Ahora aborta con código 2 y dice
  qué pasó. Un área legítimamente vacía no es lo mismo que un rechazo.

Reanudable: si se corta, volver a lanzar el mismo comando. Lee el JSONL
existente y solo baja lo que falta.
"""

import asyncio, http.cookiejar, json, os, random, re, sys, unicodedata
import urllib.error, urllib.parse, urllib.request
from datetime import datetime
from carreras_sies_2026 import CARRERAS_POR_AREA

# Playwright es opcional: si falta, se usa el cliente HTTP directo.
try:
    from playwright.async_api import async_playwright
    HAY_PLAYWRIGHT = True
except ImportError:
    async_playwright = None
    HAY_PLAYWRIGHT = False

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

class CapturaAbortada(Exception):
    """Corta la corrida con un código de salida propio.

    No se usa sys.exit() adentro de la corrutina: bajo nest_asyncio eso
    deja un SystemExit sin recoger y estampa veinte líneas de traceback
    justo después del mensaje de error, que es lo contrario de lo que se
    busca. Se propaga esta y __main__ traduce a código de salida."""

    def __init__(self, codigo):
        super().__init__(f"captura abortada (código {codigo})")
        self.codigo = codigo


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36')


# ══════════════════════════════════════════════════════════
# CLIENTE HTTP SIN NAVEGADOR
# ══════════════════════════════════════════════════════════
# Expone la misma interfaz mínima que ctx.request de Playwright
# (.get(url, params=, timeout=) → objeto con .status y await .json()),
# así el resto del código no distingue con cuál de los dos corre.
# Solo stdlib: nada que instalar.

class RespuestaHTTP:
    def __init__(self, status, cuerpo):
        self.status = status
        self._cuerpo = cuerpo

    async def json(self):
        return json.loads(self._cuerpo)

    async def text(self):
        return self._cuerpo


class ClienteHTTP:
    """Cliente directo con cookie jar. Sin navegador, sin dependencias."""

    def __init__(self, user_agent=USER_AGENT):
        self._cookies = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookies))
        self._headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-CL,es;q=0.9',
            'Referer': BASE + '/',
        }

    def _get_sync(self, url, params, timeout_ms):
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        pedido = urllib.request.Request(url, headers=self._headers)
        try:
            with self._opener.open(pedido, timeout=timeout_ms / 1000) as r:
                return RespuestaHTTP(r.status,
                                     r.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError as e:
            # 4xx/5xx no son excepción acá: son un status más, como en
            # Playwright. Se lee el cuerpo porque suele explicar el motivo.
            cuerpo = ''
            try:
                cuerpo = e.read().decode('utf-8', 'replace')
            except Exception:
                pass
            return RespuestaHTTP(e.code, cuerpo)

    async def get(self, url, params=None, timeout=25000):
        return await asyncio.to_thread(self._get_sync, url, params, timeout)

    async def establecer_sesion(self):
        """Visita la portada para recoger cookies. Devuelve el status."""
        pedido = urllib.request.Request(
            BASE + '/', headers={**self._headers, 'Accept': 'text/html'})
        try:
            with self._opener.open(pedido, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return None


def slug(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


async def pausa(rango):
    await asyncio.sleep(random.uniform(*rango))


# ══════════════════════════════════════════════════════════
# FASE 1 — BÚSQUEDA (candidatos)
# ══════════════════════════════════════════════════════════

def clasificar_error(e):
    """Etiqueta corta para el diagnóstico. Un fallo de red local y un
    rechazo del servidor no son lo mismo y no se deben reportar igual."""
    txt = str(e)
    if 'CERTIFICATE_VERIFY_FAILED' in txt or 'SSLCertVerification' in txt:
        return 'SSL_CERT'
    if 'nodename nor servname' in txt or 'Name or service not known' in txt \
            or 'Temporary failure in name resolution' in txt:
        return 'DNS'
    if 'timed out' in txt.lower() or 'TimeoutError' in type(e).__name__:
        return 'TIMEOUT'
    if 'Connection refused' in txt or 'Network is unreachable' in txt:
        return 'SIN_RED'
    return type(e).__name__


async def buscar_termino(req, termino, idx, total):
    """(avisos, fallo). `fallo` es None si la búsqueda llegó bien al final;
    si no, describe por qué se cortó. Un término sin resultados NO es un
    fallo: devuelve ([], None). La diferencia importa — ver main()."""
    avisos, pagina, fallo = [], 1, None
    print(f"\n  [{idx}/{total}] '{termino}'")
    while True:
        try:
            r = await req.get(API_SEARCH, params={
                'palabraClave': termino, 'pagina': pagina,
                'orden': 'RANKING', 'tipoOrden': 'DESC'}, timeout=25000)
            if r.status != 200:
                print(f"    pág {pagina}: HTTP {r.status} — corto")
                fallo = f"HTTP {r.status}"
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
            fallo = clasificar_error(e)
            break
    print(f"    → {len(avisos)}")
    return avisos, fallo


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

async def capturar(req, area, terminos, path, hechos, fecha, periodo):
    """Fases 1 y 2 sobre un cliente ya listo. Devuelve el contador."""

    # ── FASE 1 ────────────────────────────────────────────
    print(f"\n{'='*64}\n  FASE 1 — búsqueda\n{'='*64}")
    listado, por_termino, fallos = {}, {}, []
    for i, t in enumerate(terminos, 1):
        avisos, fallo = await buscar_termino(req, t, i, len(terminos))
        if fallo:
            fallos.append((t, fallo))
        for o in avisos:
            idf = o.get('idOferta')
            if idf is None:
                continue
            listado.setdefault(idf, o)
            por_termino.setdefault(idf, set()).add(t)
        await pausa(PAUSA_BUSQUEDA)

    # ── ¿rechazo o área vacía? ────────────────────────────
    # Son cosas distintas y antes se confundían: la corrida terminaba
    # anunciando "CAPTURA COMPLETA" con cero avisos en los dos casos.
    if fallos and not listado:
        motivos = sorted({f for _, f in fallos})
        red = [m for m in motivos if not m.startswith('HTTP')]
        uno  = len(fallos) == 1
        sust = "término falló" if uno else "términos fallaron"
        print(f"\n{'='*64}")
        print(f"  ⛔  CAPTURA ABORTADA — {area}")
        print(f"{'='*64}")
        print(f"  {len(fallos)} de {len(terminos)} {sust} y no hay ni un")
        print(f"  candidato. Esto NO es un área sin avisos.")
        print(f"  Motivos: {', '.join(motivos)}")
        print()

        # Distinguir "el servidor me rechazó" de "no salí de mi máquina".
        # Meter los dos en la misma bolsa fue un error de la v9 inicial:
        # decía "rechazo del sitio" ante un fallo de TLS local.
        if 'SSL_CERT' in red:
            print(f"  Es un problema LOCAL de certificados, no del sitio:")
            print(f"  tu Python no pudo verificar la cadena TLS. Pasa con")
            print(f"  el Python de python.org en macOS, que no usa el")
            print(f"  llavero del sistema. Se arregla una sola vez:")
            print()
            print(f"      /Applications/Python\\ 3.x/Install\\ Certificates.command")
            print()
            print(f"  o bien:")
            print(f"      python3 -m pip install --upgrade certifi")
            print(f"      export SSL_CERT_FILE=\"$(python3 -m certifi)\"")
        elif 'DNS' in red or 'SIN_RED' in red:
            print(f"  No hubo conexión: no se resolvió el nombre o la red")
            print(f"  no responde. Revisá tu conexión antes de reintentar.")
        elif 'TIMEOUT' in red:
            print(f"  Todas las peticiones expiraron. Puede ser tu red o el")
            print(f"  sitio muy lento. Reintentá más tarde.")
        elif red:
            print(f"  Los fallos son de red local, no respuestas del sitio.")
            print(f"  El servidor no llegó a contestar.")
        else:
            print(f"  Son respuestas del servidor: te está rechazando.")
            if any(m.endswith('403') for m in motivos):
                print()
                print(f"  Un 403 en todos los términos suele ser bloqueo por")
                print(f"  IP. Akamai deniega rangos de datacenter — Colab")
                print(f"  entre ellos — con 403 hasta en la portada.")
                print(f"  Comprobalo abriendo {BASE} en un navegador normal:")
                print(f"  si carga ahí y acá no, es la IP. Correr desde una")
                print(f"  red doméstica.")
        print()
        print(f"  No se escribió nada. El crudo existente quedó intacto.")
        print(f"{'='*64}\n")
        raise CapturaAbortada(2)

    ids = [i for i in listado if i not in hechos]
    print(f"\n  Candidatos únicos : {len(listado)}")
    print(f"  Ya en crudo       : {len(listado) - len(ids)}")
    print(f"  Por bajar         : {len(ids)}")
    if fallos:
        print(f"  ⚠  términos fallidos: {len(fallos)}/{len(terminos)} — "
              f"la cobertura de esta corrida es parcial")
        for t, f in fallos[:5]:
            print(f"       {f}  {t}")
        if len(fallos) > 5:
            print(f"       ... y {len(fallos) - 5} más")

    # ── FASE 2 ────────────────────────────────────────────
    print(f"\n{'='*64}\n  FASE 2 — detalle (concurrencia {CONCURRENCIA})"
          f"\n{'='*64}")

    sem  = asyncio.Semaphore(CONCURRENCIA)
    lock = asyncio.Lock()
    fh   = open(path, 'a', encoding='utf-8')
    n    = {'hechos': 0, 'fallos': 0, 'desact': 0, 'parcial': len(fallos)}

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
    return n


async def main(area, usar_navegador=True):
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

    if usar_navegador and not HAY_PLAYWRIGHT:
        print("\n  Playwright no está instalado → modo directo.")
        usar_navegador = False
    modo = "navegador" if usar_navegador else "directo (sin navegador)"

    print("\n" + "=" * 64)
    print("  MONITOR MERCADO LABORAL — v9 (captura)")
    print(f"  {inicio.strftime('%Y-%m-%d %H:%M')}  |  {area}")
    print(f"  {len(terminos)} términos  |  sesión: {modo}")
    print(f"  →  {path}")
    print("=" * 64)

    hechos = ids_ya_bajados(path)

    fase = 'arranque'
    if usar_navegador:
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage',
                          '--disable-gpu'])
                ctx = await browser.new_context(
                    user_agent=USER_AGENT,
                    locale='es-CL', timezone_id='America/Santiago',
                    viewport={'width': 1280, 'height': 800})
                page = await ctx.new_page()

                print("\n  Estableciendo sesión...")
                r0 = await page.goto(BASE, wait_until='domcontentloaded',
                                     timeout=30000)
                estado = r0.status if r0 else None
                print(f"  portada: HTTP {estado}")
                if estado and estado >= 400:
                    print(f"  ⚠  la portada ya responde {estado}; "
                          f"la búsqueda va a fallar igual")
                await page.wait_for_timeout(2000)
                try:
                    link = await page.query_selector('.cookies-msg a')
                    if link and await link.is_visible():
                        await link.click(); await page.wait_for_timeout(500)
                        print("  ✓ cookies")
                except Exception:
                    pass

                fase = 'captura'
                try:
                    n = await capturar(ctx.request, area, terminos, path,
                                       hechos, fecha, periodo)
                finally:
                    await browser.close()
        except CapturaAbortada:
            raise
        except Exception as e:
            if fase == 'captura':
                # Ya se escribieron líneas: reintentar la captura entera
                # duplicaría avisos en el JSONL. Se corta y se relanza a
                # mano, que es reanudable y no duplica.
                print(f"\n  ⛔  la captura se cortó ({type(e).__name__}: {e})")
                print(f"  Lo bajado hasta acá quedó en disco. Relanzá el")
                print(f"  mismo comando: es reanudable y no duplica.")
                raise CapturaAbortada(3)
            print(f"\n  ⚠  el navegador no arrancó ({type(e).__name__}: {e})")
            print(f"  Sigo en modo directo...")
            usar_navegador = False

    if not usar_navegador:
        cliente = ClienteHTTP()
        print("\n  Estableciendo sesión (HTTP directo)...")
        estado = await cliente.establecer_sesion()
        print(f"  portada: HTTP {estado}")
        if estado and estado >= 400:
            print(f"  ⚠  la portada ya responde {estado}; "
                  f"la búsqueda va a fallar igual")
        n = await capturar(cliente, area, terminos, path,
                           hechos, fecha, periodo)

    mins = int((datetime.now() - inicio).total_seconds() // 60)
    print(f"\n{'='*64}")
    if n['parcial']:
        print(f"  CAPTURA PARCIAL — {area}   ({mins} min)")
        print(f"  ⚠  {n['parcial']} término(s) fallaron: faltan avisos")
    else:
        print(f"  CAPTURA COMPLETA — {area}   ({mins} min)")
    print(f"  Avisos bajados en esta corrida : {n['hechos']}")
    print(f"    fallidos                     : {n['fallos']}")
    print(f"    DESACTIVADA                  : {n['desact']}")
    print(f"  Archivo: {path}  "
          f"({os.path.getsize(path)/1024/1024:.1f} MB)")
    print(f"\n  Siguiente paso:  python consolidar.py")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    desconocidas = flags - {'--sin-navegador'}
    if desconocidas:
        print(f"Opción desconocida: {', '.join(sorted(desconocidas))}")
        sys.exit(1)
    if not args:
        print("Uso: python scraper_v9.py \"<Área>\" [--sin-navegador]\n")
        print("Áreas disponibles:")
        for a, c in CARRERAS_POR_AREA.items():
            print(f"  {len(c):3d} términos  {a}")
        sys.exit(1)
    try:
        asyncio.run(main(args[0],
                         usar_navegador='--sin-navegador' not in flags))
    except CapturaAbortada as e:
        sys.exit(e.codigo)
