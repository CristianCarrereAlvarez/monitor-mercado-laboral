"""
Monitor Mercado Laboral Chile — v7
===================================
Cambios respecto a v6:
  ✓ formato largo: 1 fila por (aviso × carrera que lo encontró)
    → un aviso relevante para 3 carreras genera 3 filas
    → el detalle se descarga 1 sola vez por aviso (sin requests extra)
  ✓ modalidad derivada de jornada
  ✓ experiencia_minima con calificador: "Desde 2 años"
  ✓ flag_aviso_generico: True si aviso lista >20 carreras
  ✓ habilidades eliminado
  ✗ rubro_empresa: endpoint /api/empresas no existe (devuelve 404)

APIs confirmadas:
  Búsqueda: GET /api/searchjob?palabraClave={}&pagina={}&orden=RANKING&tipoOrden=DESC
  Detalle:  GET /api/ofertas/{idOferta}

Archivos necesarios en el mismo directorio:
  scraper_v7.py          ← este archivo
  carreras_sies_2026.py  ← diccionario de carreras (editar para ajustar qué buscar)

Colab — sube ambos archivos y luego:
  Celda 1 (solo la primera vez):
    !pip install playwright nest_asyncio beautifulsoup4
    !playwright install --with-deps chromium
"""

import asyncio, csv, json, re, random, time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from carreras_sies_2026 import CARRERAS_POR_AREA

try:
    import nest_asyncio; nest_asyncio.apply()
except ImportError:
    pass


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN — nada que editar aquí
# Las áreas y carreras vienen todas de carreras_sies_2026.py
# ══════════════════════════════════════════════════════════

MAX_PAGINAS_POR_CARRERA = 10
PAUSA_ENTRE_CALLS       = (1.0, 2.5)
UMBRAL_AVISO_GENERICO   = 20

TIMESTAMP = datetime.now().strftime('%Y_%m')
CSV_FILE  = f"mercado_laboral_{TIMESTAMP}.csv"
JSON_FILE = f"mercado_laboral_{TIMESTAMP}.json"

API_SEARCH = "https://www.trabajando.cl/api/searchjob"
API_DETAIL = "https://www.trabajando.cl/api/ofertas/{id}"
BASE_URL   = "https://www.trabajando.cl"


# ══════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════

def esperar():
    time.sleep(random.uniform(*PAUSA_ENTRE_CALLS))

def strip_html(html_str):
    if not html_str:
        return None
    try:
        return BeautifulSoup(html_str, 'html.parser').get_text(separator=' ', strip=True)
    except:
        return re.sub(r'<[^>]+>', ' ', html_str).strip()

def parsear_geolocalizacion(geo_str):
    if not geo_str or ',' not in geo_str:
        return None, None
    try:
        partes = geo_str.split(',')
        return float(partes[0]), float(partes[1])
    except:
        return None, None

def derivar_modalidad(jornada):
    """
    Modalidad de trabajo derivada del campo jornada.
    El API de trabajando.cl no expone modalidad como campo independiente.

    Mapeo (basado en valores observados en los datos):
      "Teletrabajo"                    → Remoto
      "Mixta (Teletrabajo + Presencial)"→ Híbrido
      "En terreno"                     → Presencial  (trabajo de campo, ej. agropecuaria)
      cualquier otro                   → Presencial  (default)

    Limitación: "Jornada Completa" podría ser remota si el empleador
    no seleccionó "Teletrabajo" en la jornada. Sin campo propio en el API,
    esta inferencia es el mejor proxy disponible.
    """
    if not jornada:
        return None
    j = jornada.lower()
    if 'mixta' in j or 'híbrido' in j:
        return 'Híbrido'
    if 'teletrabajo' in j or 'remoto' in j or 'telepresencial' in j:
        return 'Remoto'
    return 'Presencial'   # "Jornada Completa", "Part Time", "En terreno", "Por Turnos", etc.


# ══════════════════════════════════════════════════════════
# FASE 1: BÚSQUEDA VÍA API
# ══════════════════════════════════════════════════════════

async def buscar_carrera(page, termino, carrera_sies, idx, total=0):
    avisos = []
    total_str = f"/{total}" if total else ""
    print(f"\n  [{idx}{total_str}] '{termino}'")

    for pagina in range(1, MAX_PAGINAS_POR_CARRERA + 1):
        try:
            resp = await page.request.get(
                API_SEARCH,
                params={'palabraClave': termino, 'pagina': pagina,
                        'orden': 'RANKING', 'tipoOrden': 'DESC'},
                timeout=20000,
            )
            if resp.status != 200:
                print(f"    Pág {pagina}: HTTP {resp.status}")
                break

            data       = await resp.json()
            ofertas_pag = data.get('ofertas', [])
            if not ofertas_pag:
                break

            n_pags = data.get('cantidadPaginas', 1)
            print(f"    Pág {pagina}/{n_pags}: {len(ofertas_pag)} avisos "
                  f"(total: {data.get('cantidadRegistros','?')})")

            for o in ofertas_pag:
                o['_carrera_busqueda'] = termino
                o['_carrera_sies']     = carrera_sies
            avisos.extend(ofertas_pag)

            if pagina >= n_pags:
                break
            esperar()

        except Exception as e:
            print(f"    Error en pág {pagina}: {e}")
            break

    print(f"    → {len(avisos)} avisos totales para '{termino}'")
    return avisos


# ══════════════════════════════════════════════════════════
# FASE 2: DETALLE VÍA API
# ══════════════════════════════════════════════════════════

async def obtener_detalle(page, id_oferta):
    try:
        resp = await page.request.get(API_DETAIL.format(id=id_oferta), timeout=20000)
        if resp.status == 200:
            return await resp.json()
    except:
        pass
    return None


def transformar_registro(oferta_search, detalle):
    """
    Combina datos del listado + detalle en un registro plano.
    Orden de campos = orden de tu listado de variables.
    """
    ubicacion_raw = oferta_search.get('ubicacion', '')
    partes_ubic   = [p.strip() for p in ubicacion_raw.split(',')] if ubicacion_raw else []
    lat, lon      = parsear_geolocalizacion(oferta_search.get('geolocalizacion', ''))
    jornada       = oferta_search.get('nombreJornada')

    # ── Trazabilidad ──────────────────────────────────────────────────
    reg = {
        'aviso_id':              oferta_search.get('idOferta'),
        'carrera_busqueda':      oferta_search.get('_carrera_busqueda'),
        'carrera_generica_sies': oferta_search.get('_carrera_sies'),
        'area_conocimiento':     oferta_search.get('_area', ''),
        'fecha_scraping':        datetime.now().strftime('%Y-%m-%d'),

        # ── Tu listado de variables: Oferta ───────────────────────────
        'titulo':                oferta_search.get('nombreCargo'),
        'empresa':               oferta_search.get('nombreEmpresa'),
        'rubro_empresa':         None,           # pendiente /api/empresas endpoint
        'fecha_publicacion':     oferta_search.get('fechaPublicacion'),
        'descripcion':           None,           # se rellena desde detalle abajo

        # ── Tu listado: Detalle oferta ────────────────────────────────
        'tipo_cargo':            None,
        'vacantes':              None,
        'region':                partes_ubic[1] if len(partes_ubic) > 1 else None,
        'comuna':                partes_ubic[0] if len(partes_ubic) > 0 else None,
        'jornada':               jornada,
        'modalidad':             derivar_modalidad(jornada),   # ← derivada

        # ── Tu listado: Requisitos ────────────────────────────────────
        'requisitos':            None,
        'experiencia_minima':    None,           # ← "Desde 2 años" (con calificador)
        'nivel_academico':       None,
        'situacion_academica':   None,
        'carreras_requeridas':   None,
        # habilidades → eliminado

        # ── Control de calidad ────────────────────────────────────────
        'flag_aviso_generico':   False,          # True si > 20 carreras listadas

        # ── Bonus útiles ──────────────────────────────────────────────
        'sueldo_liquido':        None,
        'muestra_sueldo':        None,
        'fecha_expiracion':      None,
        'postulaciones':         None,
        'visualizaciones':       None,
        'destacada':             oferta_search.get('ofertaDestacada', False),
        'inclusiva':             oferta_search.get('ofertaInclusiva', False),
        'idiomas':               None,
        'latitud':               lat,
        'longitud':              lon,
        'empresa_id':            None,
        'url':                   None,
    }

    # ── Enriquecer desde detalle ───────────────────────────────────────
    if detalle:
        carreras_lista = detalle.get('carreras', [])
        n_carreras     = len(carreras_lista)
        anios_exp      = detalle.get('aniosExperiencia')
        operador_exp   = detalle.get('nombreOperadorExperiencia', 'Desde')

        reg.update({
            'empresa_id':       detalle.get('idCompany'),
            'tipo_cargo':       detalle.get('nombreTipoCargo'),
            'vacantes':         detalle.get('cantidadVacantes'),
            'muestra_sueldo':   detalle.get('mostrarSueldo', False),
            'sueldo_liquido': (
                detalle.get('sueldo')
                if detalle.get('mostrarSueldo') and (detalle.get('sueldo') or 0) > 0
                else None
            ),

            # Experiencia con calificador: "Desde 2 años"
            'experiencia_minima': (
                f"{operador_exp} {anios_exp} año{'s' if anios_exp != 1 else ''}"
                if anios_exp is not None else None
            ),

            'nivel_academico':     detalle.get('nombreNivelAcademico'),
            'situacion_academica': detalle.get('nombreSituacionAcademica'),
            'fecha_expiracion':    detalle.get('fechaExpiracionFormatoIngles'),
            'postulaciones':       detalle.get('candidadPostulaciones'),
            'visualizaciones':     detalle.get('candidadVisualizaciones'),

            # Carreras requeridas como lista separada por |
            'carreras_requeridas': (
                ' | '.join(c['nombreCarrera'] for c in carreras_lista)
                or None
            ),

            # Flag de aviso genérico
            'flag_aviso_generico': n_carreras > UMBRAL_AVISO_GENERICO,

            # Idiomas con nivel
            'idiomas': (
                ' | '.join(
                    f"{i['nombreIdioma']}:hablado={i.get('nombreHablado','?')}"
                    for i in detalle.get('idiomas', [])
                ) or None
            ),

            # Descripción completa (texto libre del cuerpo del aviso)
            'descripcion': strip_html(detalle.get('descripcionOferta')),
            'requisitos':  strip_html(detalle.get('requisitosMinimos')),

            # Ubicación más precisa desde detalle
            'region': (
                detalle.get('ubicacion', {}).get('nombreRegion')
                or reg['region']
            ),
            'comuna': (
                detalle.get('ubicacion', {}).get('nombreComuna')
                or reg['comuna']
            ),

            # Jornada y modalidad del detalle (puede diferir del listado)
            'jornada': detalle.get('nombreJornada') or reg['jornada'],

            # URL canónica
            'url': (
                f"{BASE_URL}/trabajo/{detalle['idOferta']}-{detalle['slug']}"
                if detalle.get('slug')
                else f"{BASE_URL}/trabajo/{detalle['idOferta']}"
            ),
        })

        # Recalcular modalidad si jornada vino del detalle
        if detalle.get('nombreJornada'):
            reg['modalidad'] = derivar_modalidad(detalle['nombreJornada'])

    return reg


# ══════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════

async def main():
    print("\n" + "="*60)
    print("  MONITOR MERCADO LABORAL — v7")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Áreas: {len(CARRERAS_POR_AREA)} | Carreras: {sum(len(c) for c in CARRERAS_POR_AREA.values())}")
    print("="*60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
        )
        ctx  = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'
            ),
            locale='es-CL', timezone_id='America/Santiago',
            viewport={'width': 1280, 'height': 800},
        )
        page = await ctx.new_page()

        # Sesión (una sola carga para obtener cookies)
        print("\n  Estableciendo sesión...")
        await page.goto(BASE_URL, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        try:
            link = await page.query_selector('.cookies-msg a')
            if link and await link.is_visible():
                await link.click(); await page.wait_for_timeout(500)
                print("  ✓ Cookies aceptadas")
        except:
            pass

        # ── Estructuras globales (compartidas entre todas las áreas) ──
        aviso_datos    = {}   # aviso_id → datos del listado (primera aparición)
        aviso_detalles = {}   # aviso_id → JSON del detalle (1 fetch por aviso único)

        # (area, aviso_id) → set de carrera_sies que lo encontraron en esa área
        registros_por_area = {}

        # Mapa inverso global: carrera_sies → término de búsqueda
        sies_a_termino = {sies: term
                          for area_carreras in CARRERAS_POR_AREA.values()
                          for term, sies in area_carreras.items()}

        # ════════════════════════════════════════════════════
        # FASE 1 — Búsqueda: todas las áreas, todas las carreras
        # ════════════════════════════════════════════════════
        total_carreras = sum(len(c) for c in CARRERAS_POR_AREA.values())
        print(f"\n{'='*60}")
        print(f"  FASE 1: Búsqueda")
        print(f"  {len(CARRERAS_POR_AREA)} áreas / {total_carreras} carreras")
        print(f"{'='*60}")

        idx_global = 0
        for area, carreras in CARRERAS_POR_AREA.items():
            print(f"\n  ── {area} ({len(carreras)} carreras) ──")
            registros_por_area[area] = {}   # aviso_id → set(carrera_sies)

            for termino, carrera_sies in carreras.items():
                idx_global += 1
                avisos = await buscar_carrera(page, termino, carrera_sies, idx_global, total_carreras)
                for a in avisos:
                    id_ = a['idOferta']
                    if id_ not in aviso_datos:
                        aviso_datos[id_] = a
                    registros_por_area[area].setdefault(id_, set()).add(carrera_sies)
                esperar()

        n_unicos = len(aviso_datos)
        n_pares  = sum(len(c)
                       for area_dict in registros_por_area.values()
                       for c in area_dict.values())
        print(f"\n  Avisos únicos:       {n_unicos}")
        print(f"  Pares aviso×carrera: {n_pares}")

        # ════════════════════════════════════════════════════
        # FASE 2 — Detalle: 1 sola llamada por aviso_id único
        #          (si el mismo aviso aparece en Agropecuaria y Salud,
        #           se descarga una sola vez)
        # ════════════════════════════════════════════════════
        print(f"\n{'='*60}")
        print(f"  FASE 2: Detalle ({n_unicos} avisos únicos)")
        print(f"  Tiempo estimado: ~{n_unicos*1.5/60:.0f} min")
        print(f"{'='*60}\n")

        for i, (id_oferta, oferta) in enumerate(aviso_datos.items(), 1):
            titulo = oferta.get('nombreCargo', '')[:40]
            print(f"  [{i:4d}/{n_unicos}] {id_oferta} | {titulo}", end='  ')

            detalle = await obtener_detalle(page, id_oferta)
            aviso_detalles[id_oferta] = detalle

            sueldo = (f"${detalle.get('sueldo'):,}"
                      if detalle and detalle.get('mostrarSueldo')
                      and detalle.get('sueldo', 0) > 0 else '-')
            flag = (' [GENÉRICO]'
                    if detalle and len(detalle.get('carreras', [])) > UMBRAL_AVISO_GENERICO
                    else '')
            print(f"→ {sueldo}{flag}")
            esperar()

        await browser.close()

    # ════════════════════════════════════════════════════
    # FASE 3 — Expandir: 1 fila por (área × aviso × carrera)
    # ════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  FASE 3: Generando filas")
    print(f"{'='*60}")

    resultados = []
    for area, aviso_carreras in registros_por_area.items():
        for id_oferta, carreras_set in aviso_carreras.items():
            oferta  = aviso_datos[id_oferta]
            detalle = aviso_detalles.get(id_oferta)

            for carrera_sies in sorted(carreras_set):
                oferta_copia = dict(oferta)
                oferta_copia['_area']            = area
                oferta_copia['_carrera_sies']    = carrera_sies
                oferta_copia['_carrera_busqueda'] = sies_a_termino.get(carrera_sies, carrera_sies)

                resultados.append(transformar_registro(oferta_copia, detalle))

    print(f"  Filas totales: {len(resultados)}  "
          f"({n_unicos} avisos únicos / {len(CARRERAS_POR_AREA)} áreas)")

    # GUARDAR
    if not resultados:
        print("\n✗ Sin resultados."); return

    campos = list(resultados[0].keys())
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader(); w.writerows(resultados)

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    # RESUMEN
    from collections import Counter
    n         = len(resultados)
    pct       = lambda x: f"{x*100//n}%"
    genericos = sum(1 for r in resultados if r.get('flag_aviso_generico'))

    print(f"\n{'='*60}")
    print(f"  COMPLETADO v7 — Mercado Laboral Chile")
    print(f"  Filas totales       : {n}  (avisos únicos: {n_unicos})")
    print(f"  Con sueldo visible  : {sum(1 for r in resultados if r.get('sueldo_liquido'))} ({pct(sum(1 for r in resultados if r.get('sueldo_liquido')))})")
    print(f"  Con carreras reqrd. : {sum(1 for r in resultados if r.get('carreras_requeridas'))} ({pct(sum(1 for r in resultados if r.get('carreras_requeridas')))})")
    print(f"  flag_aviso_generico : {genericos} ({pct(genericos)})")
    print(f"\n  Por área de conocimiento:")
    for area, cnt in Counter(r['area_conocimiento'] for r in resultados).most_common():
        gen = sum(1 for r in resultados if r['area_conocimiento']==area and r.get('flag_aviso_generico'))
        print(f"    {cnt:5d} ({gen:3d} gen.)  {area}")
    print(f"\n  Archivos: {CSV_FILE}  /  {JSON_FILE}")
    print(f"{'='*60}\n")


asyncio.run(main())
