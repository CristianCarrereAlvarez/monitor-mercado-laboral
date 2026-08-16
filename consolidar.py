"""
Consolidación — crudo JSONL → maestras CSV acumuladas
======================================================
Lee todos los crudo_*.jsonl y hace UPSERT sobre siete tablas.
Es idempotente y reprocesable: se puede correr las veces que sea, y si
mañana cambia un criterio de parseo, se vuelve a correr sobre el mismo
crudo sin tocar la red.

Tablas (directorio maestras/):

  avisos.csv               1 fila por aviso_id — panel longitudinal
  aviso_carrera.csv        1 fila por (aviso × carrera declarada)
  aviso_habilidad.csv      1 fila por (aviso × habilidad)
  aviso_institucion.csv    1 fila por (aviso × institución)
  empresas.csv             1 fila por empresa_id  ← columnas manuales
  carreras_trabajando.csv  1 fila por nombre      ← columnas manuales
  instituciones.csv        1 fila por id_institucion

COLUMNAS MANUALES
  Las columnas que el script no gestiona se PRESERVAN en el upsert.
  Si agregás `rubro` o `tamano` a empresas.csv a mano, sobreviven a las
  corridas siguientes. Lo mismo con la homologación en
  carreras_trabajando.csv. Las columnas gestionadas se sobrescriben.

HOMOLOGACIÓN
  No se hace acá. `carreras_trabajando.csv` acumula la taxonomía
  observada con su frecuencia, para completarla a mano una vez que estén
  las 10 áreas. Las carreras NO traen ID en la API, así que la clave es
  el nombre exacto.

PANEL / DURACIÓN DE VACANTE
  aviso_id es estable entre corridas. Con dos o más corridas se obtiene:
    primera_vez_visto, ultima_vez_visto, n_corridas_visto
    fecha_desactivacion_detectada  (primera corrida con DESACTIVADA)
    dias_publicado_hasta_baja      (desactivación − fecha_publicacion)
    censurado                      (True = nunca se vio DESACTIVADA)
  Precisión de la baja = frecuencia de corridas. Con corridas mensuales,
  la fecha de desactivación tiene error de hasta un mes.

Uso:
  python consolidar.py
  python consolidar.py --crudo crudo --maestras maestras
"""

import argparse, csv, glob, json, os, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import datetime

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# ══════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════

def normalizar(s):
    if not isinstance(s, str):
        return ''
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


def strip_html(s):
    if not s:
        return None
    txt = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s,
                 flags=re.S | re.I)
    txt = re.sub(r'<br\s*/?>|</p>|</li>|</div>', ' ', txt, flags=re.I)
    txt = re.sub(r'<[^>]+>', '', txt)
    txt = (txt.replace('&nbsp;', ' ').replace('&amp;', '&')
              .replace('&lt;', '<').replace('&gt;', '>')
              .replace('&quot;', '"').replace('&#39;', "'"))
    return re.sub(r'\s+', ' ', txt).strip() or None


def derivar_modalidad(jornada):
    """
    La API no expone modalidad como campo propio. Solo algunos valores de
    `jornada` la informan; el resto queda 'No informado' — NO 'Presencial'.
    (En agosto 2026, 69% de los avisos tenía "Jornada Completa", que no
    dice nada sobre modalidad.)
    """
    if not jornada:
        return None
    j = normalizar(jornada)
    if 'mixta' in j or 'hibrid' in j:
        return 'Híbrido'
    if 'teletrabajo' in j or 'remoto' in j or 'telepresencial' in j:
        return 'Remoto'
    if 'terreno' in j:
        return 'Presencial'
    return 'No informado'


def derivar_tipo_contrato(jornada):
    if not jornada:
        return None
    j = normalizar(jornada)
    for clave, val in (('practica', 'Práctica'), ('reemplazo', 'Reemplazo'),
                       ('free lance', 'Freelance'), ('freelance', 'Freelance'),
                       ('comisionista', 'Comisionista')):
        if clave in j:
            return val
    return None


def parsear_experiencia(d):
    """(operador, anios, inconsistente). La API a veces se contradice:
    operador 'Sin experiencia' con aniosExperiencia > 0."""
    anios = d.get('aniosExperiencia')
    oper  = d.get('nombreOperadorExperiencia')
    if anios is None and oper is None:
        return None, None, None
    incons = bool(oper and normalizar(oper).startswith('sin experiencia')
                  and isinstance(anios, (int, float)) and anios > 0)
    return oper, anios, incons


def coordenadas(detalle, listado):
    """
    OJO: detalle.ubicacion.coordenadas dice type "Point" pero el orden es
    [lat, lon], al revés de GeoJSON (que especifica [lon, lat]).
    Verificado con Antofagasta: [-23.61, -70.39].
    """
    coords = (((detalle or {}).get('ubicacion') or {})
              .get('coordenadas') or {}).get('coordinates')
    if isinstance(coords, list) and len(coords) >= 2:
        try:
            return float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            pass
    geo = (listado or {}).get('geolocalizacion') or ''
    if ',' in geo:
        try:
            a, b = geo.split(',')[:2]
            return float(a), float(b)
        except ValueError:
            pass
    return None, None


def fecha_iso(s):
    """'2026-08-12 12:10' o '12/08/2026' → '2026-08-12'."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def dias_entre(a, b):
    if not a or not b:
        return None
    try:
        return (datetime.strptime(b, '%Y-%m-%d')
                - datetime.strptime(a, '%Y-%m-%d')).days
    except ValueError:
        return None


def minimo(a, b):
    return b if a is None else (a if b is None else min(a, b))


def maximo(a, b):
    return b if a is None else (a if b is None else max(a, b))


# ══════════════════════════════════════════════════════════
# IO CON PRESERVACIÓN DE COLUMNAS MANUALES
# ══════════════════════════════════════════════════════════

def leer_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def escribir_csv(path, filas, gestionadas, clave):
    """
    Upsert conservando columnas manuales. `gestionadas` son las columnas
    que este script controla; cualquier otra columna existente en el CSV
    se arrastra por clave.
    """
    previas = {r[clave]: r for r in leer_csv(path) if r.get(clave)}
    manuales = []
    for r in previas.values():
        for c in r:
            if c not in gestionadas and c not in manuales:
                manuales.append(c)

    salida = []
    for fila in filas:
        k = str(fila[clave])
        prev = previas.get(k, {})
        completa = {c: fila.get(c) for c in gestionadas}
        for c in manuales:
            completa[c] = prev.get(c, '')
        salida.append(completa)

    # filas que existían y ya no aparecen: se conservan intactas
    vistos = {str(f[clave]) for f in filas}
    for k, prev in previas.items():
        if k not in vistos:
            salida.append({c: prev.get(c, '') for c in gestionadas + manuales})

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=gestionadas + manuales,
                           extrasaction='ignore')
        w.writeheader()
        w.writerows(salida)
    return len(salida), len(manuales)


def escribir_csv_simple(path, filas, campos):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)
    return len(filas)


# ══════════════════════════════════════════════════════════
# ESQUEMAS
# ══════════════════════════════════════════════════════════

COLS_AVISOS = [
    'aviso_id', 'url',
    # panel
    'primera_vez_visto', 'ultima_vez_visto', 'n_corridas_visto',
    'periodos_visto', 'estado_primero', 'estado_ultimo',
    'fecha_desactivacion_detectada', 'dias_publicado_hasta_baja',
    'calidad_duracion', 'censurado',
    # contenido
    'titulo', 'descripcion', 'requisitos', 'hash_contenido',
    # empresa
    'empresa_id', 'empresa_id_alt', 'empresa_nombre', 'empresa_confidencial',
    # fechas
    'fecha_publicacion', 'fecha_expiracion', 'vigencia_declarada_dias',
    # cargo
    'tipo_cargo', 'area_funcional', 'vacantes',
    # ubicación
    'region', 'comuna', 'direccion', 'codigo_postal', 'latitud', 'longitud',
    # condiciones
    'jornada', 'modalidad', 'tipo_contrato',
    'sueldo_liquido', 'muestra_sueldo', 'moneda',
    # requisitos
    'exp_operador', 'exp_anios', 'exp_inconsistente',
    'nivel_academico', 'situacion_academica',
    # conteos
    'n_carreras_declaradas', 'n_habilidades', 'n_instituciones',
    'postulaciones', 'visualizaciones',
    # flags
    'destacada', 'inclusiva', 'tipo_curriculum', 'usa_score_screening',
    # auditoría
    'areas_scraping', 'terminos_busqueda', 'n_terminos_busqueda',
    'detalle_ok', 'detalle_motivo',
]

COLS_EMPRESAS = [
    'empresa_id', 'empresa_id_alt', 'nombre_canonico', 'nombres_observados',
    'n_avisos_acumulados', 'primera_vez_visto', 'ultima_vez_visto',
    'areas_observadas', 'siempre_confidencial', 'n_avisos_confidenciales',
]

COLS_CARRERAS = [
    'carrera_trabajando', 'n_avisos_acum', 'n_avisos_especificos',
    'primera_vez_visto', 'ultima_vez_visto', 'areas_observadas',
]

# Un aviso que declara más carreras que esto está tildando media
# taxonomía y no informa nada sobre qué carrera busca de verdad.
# Observado: hay avisos que declaran las 504 carreras del catálogo.
# `n_avisos_especificos` cuenta solo los avisos por debajo del umbral,
# y es el orden correcto para priorizar la homologación manual.
UMBRAL_AVISO_GENERICO = 20

COLS_INSTITUCIONES = [
    'id_institucion', 'id_institucion_sqlserver', 'nombre_institucion',
    'n_avisos_acum', 'primera_vez_visto', 'ultima_vez_visto',
]


# ══════════════════════════════════════════════════════════
# TRANSFORMACIÓN
# ══════════════════════════════════════════════════════════

def aplanar(reg):
    """Un registro crudo → dict plano del aviso (sin campos de panel)."""
    listado = reg.get('listado') or {}
    detalle = reg.get('detalle') or {}
    ubic_txt = [p.strip() for p in (listado.get('ubicacion') or '').split(',')
                if p.strip()]
    ubic = detalle.get('ubicacion') or {}
    jornada = detalle.get('nombreJornada') or listado.get('nombreJornada')
    oper, anios, incons = parsear_experiencia(detalle)
    lat, lon = coordenadas(detalle, listado)

    nombre = (detalle.get('nombreEmpresaFantasia')
              or listado.get('nombreEmpresa') or '').strip()
    confid = bool(detalle.get('ofertaConfidencial')) if detalle else \
        (normalizar(nombre) in ('empresa confidencial', 'confidencial'))

    f_pub = fecha_iso(detalle.get('fechaPublicacionFormatoIngles')
                      or listado.get('fechaPublicacion'))
    f_exp = fecha_iso(detalle.get('fechaExpiracionFormatoIngles'))
    desc  = strip_html(detalle.get('descripcionOferta')
                       or listado.get('descripcionOferta'))
    idf   = reg['aviso_id']
    slug_url = detalle.get('slug')

    return {
        'aviso_id': idf,
        'url': (f"https://www.trabajando.cl/trabajo/{slug_url}" if slug_url
                else f"https://www.trabajando.cl/trabajo/{idf}"),
        'titulo': detalle.get('nombreCargo') or listado.get('nombreCargo'),
        'descripcion': desc,
        'requisitos': strip_html(detalle.get('requisitosMinimos')),

        'empresa_id': detalle.get('idCompany'),
        'empresa_id_alt': detalle.get('idEmpresa'),
        'empresa_nombre': None if confid else (nombre or None),
        'empresa_confidencial': confid,

        'fecha_publicacion': f_pub,
        'fecha_expiracion': f_exp,
        'vigencia_declarada_dias': dias_entre(f_pub, f_exp),

        'tipo_cargo': detalle.get('nombreTipoCargo'),
        'area_funcional': detalle.get('nombreArea'),
        'vacantes': detalle.get('cantidadVacantes'),

        'region': ubic.get('nombreRegion')
                  or (ubic_txt[1] if len(ubic_txt) > 1 else None),
        'comuna': ubic.get('nombreComuna')
                  or (ubic_txt[0] if len(ubic_txt) > 0 else None),
        'direccion': ubic.get('direccion'),
        'codigo_postal': ubic.get('codigoPostal'),
        'latitud': lat, 'longitud': lon,

        'jornada': jornada,
        'modalidad': derivar_modalidad(jornada),
        'tipo_contrato': derivar_tipo_contrato(jornada),
        'sueldo_liquido': (detalle.get('sueldo')
                           if detalle.get('mostrarSueldo')
                           and (detalle.get('sueldo') or 0) > 0 else None),
        'muestra_sueldo': detalle.get('mostrarSueldo'),
        'moneda': detalle.get('nombreMoneda'),

        'exp_operador': oper, 'exp_anios': anios, 'exp_inconsistente': incons,
        'nivel_academico': detalle.get('nombreNivelAcademico'),
        'situacion_academica': detalle.get('nombreSituacionAcademica'),

        'n_carreras_declaradas': len(detalle.get('carreras') or []),
        'n_habilidades': len(detalle.get('habilidades') or []),
        'n_instituciones': len(detalle.get('instituciones') or []),
        'postulaciones': detalle.get('candidadPostulaciones'),
        'visualizaciones': detalle.get('candidadVisualizaciones'),

        'destacada': listado.get('ofertaDestacada'),
        'inclusiva': listado.get('ofertaInclusiva'),
        'tipo_curriculum': detalle.get('tipoCurriculumAceptado'),
        'usa_score_screening': detalle.get('usaScoreScreening'),

        'detalle_ok': reg.get('detalle_ok'),
        'detalle_motivo': reg.get('detalle_motivo'),
        '_estado': detalle.get('estadoOferta'),
        '_fecha': reg.get('fecha_scraping'),
        '_periodo': reg.get('periodo'),
        '_area': reg.get('area_scraping'),
        '_terminos': reg.get('terminos') or [],
        '_carreras': [c.get('nombreCarrera')
                      for c in (detalle.get('carreras') or [])
                      if c.get('nombreCarrera')],
        '_habilidades': detalle.get('habilidades') or [],
        '_instituciones': detalle.get('instituciones') or [],
    }


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def main(dir_crudo, dir_maestras):
    archivos = sorted(glob.glob(os.path.join(dir_crudo, 'crudo_*.jsonl')))
    if not archivos:
        print(f"Sin archivos crudo_*.jsonl en {dir_crudo}/")
        sys.exit(1)

    print("=" * 64)
    print(f"  CONSOLIDACIÓN  —  {len(archivos)} archivos de crudo")
    print("=" * 64)

    registros = []
    for path in archivos:
        n = 0
        with open(path, encoding='utf-8') as f:
            for linea in f:
                try:
                    registros.append(json.loads(linea))
                    n += 1
                except Exception:
                    continue
        print(f"  {os.path.basename(path):48s} {n:6d}")

    # orden cronológico: el upsert asume que lo último pisa a lo anterior
    registros.sort(key=lambda r: (r.get('fecha_scraping') or '',
                                  r.get('aviso_id') or 0))
    print(f"\n  Observaciones totales: {len(registros)}")

    avisos       = {}
    pares_car    = {}
    pares_hab    = {}
    pares_inst   = {}
    emp_nombres  = defaultdict(Counter)
    emp_meta     = {}
    car_meta     = {}
    inst_meta    = {}

    for reg in registros:
        p = aplanar(reg)
        idf, fecha = p['aviso_id'], p['_fecha']
        estado = p['_estado']

        prev = avisos.get(idf)
        panel = {
            'primera_vez_visto': minimo(prev and prev['primera_vez_visto'], fecha),
            'ultima_vez_visto':  maximo(prev and prev['ultima_vez_visto'], fecha),
            'n_corridas_visto':  (prev['n_corridas_visto'] if prev else 0) + 1,
            'estado_primero':    (prev['estado_primero'] if prev else estado),
            'estado_ultimo':     estado,
            'fecha_desactivacion_detectada': (
                (prev.get('fecha_desactivacion_detectada') if prev else None)
                or (fecha if estado == 'DESACTIVADA' else None)),
        }
        periodos = set((prev.get('_periodos') if prev else set()))
        periodos.add(p['_periodo'])
        areas = set((prev.get('_areas') if prev else set()))
        areas.add(p['_area'])
        terms = set((prev.get('_terms') if prev else set()))
        terms.update(p['_terminos'])

        p.update(panel)
        p['_periodos'] = periodos
        p['_areas'] = areas
        p['_terms'] = terms
        p['periodos_visto']   = ' | '.join(sorted(x for x in periodos if x))
        p['areas_scraping']   = ' | '.join(sorted(x for x in areas if x))
        p['terminos_busqueda'] = ' | '.join(sorted(terms))
        p['n_terminos_busqueda'] = len(terms)
        p['censurado'] = p['fecha_desactivacion_detectada'] is None
        p['dias_publicado_hasta_baja'] = dias_entre(
            p['fecha_publicacion'], p['fecha_desactivacion_detectada'])
        # Tres calidades muy distintas que no se deben mezclar:
        #   observada     → se vio PUBLICADA y después DESACTIVADA.
        #                   La fecha de baja está acotada por el intervalo
        #                   entre corridas. Es la única medición real.
        #   cota_superior → la primera vez que lo vimos ya estaba
        #                   DESACTIVADA. Murió en algún momento antes;
        #                   el número es un techo, no una duración.
        #   censurada     → seguía viva en la última observación.
        if p['censurado']:
            p['calidad_duracion'] = 'censurada'
        elif p['estado_primero'] == 'DESACTIVADA':
            p['calidad_duracion'] = 'cota_superior'
        else:
            p['calidad_duracion'] = 'observada'
        p['hash_contenido'] = __import__('hashlib').sha1(
            f"{p['empresa_id']}|{normalizar(p['titulo'])}|"
            f"{normalizar((p['descripcion'] or '')[:2000])}"
            .encode('utf-8')).hexdigest()[:16]
        avisos[idf] = p

        # ── tablas puente (clave compuesta: sobrescribe, no duplica) ──
        for nombre in p['_carreras']:
            pares_car[(idf, nombre)] = {
                'aviso_id': idf, 'carrera_trabajando': nombre,
                'termino_busqueda': None, 'fuente': 'declarada',
                'n_carreras_declaradas_aviso': p['n_carreras_declaradas']}
            m = car_meta.setdefault(nombre, {
                'carrera_trabajando': nombre, 'n_avisos_acum': 0,
                'primera_vez_visto': None,
                'ultima_vez_visto': None, '_areas': set()})
            m['primera_vez_visto'] = minimo(m['primera_vez_visto'], fecha)
            m['ultima_vez_visto'] = maximo(m['ultima_vez_visto'], fecha)
            m['_areas'].add(p['_area'])

        if not p['_carreras'] and p['detalle_ok']:
            for t in p['_terminos']:
                pares_car[(idf, f"[kw] {t}")] = {
                    'aviso_id': idf, 'carrera_trabajando': None,
                    'termino_busqueda': t, 'fuente': 'keyword_only',
                    'n_carreras_declaradas_aviso': 0}

        for h in p['_habilidades']:
            nom = h.get('nombreHabilidad')
            if not nom:
                continue
            pares_hab[(idf, nom)] = {
                'aviso_id': idf, 'habilidad': nom,
                'nivel': h.get('nombreNivel') or None}

        for i in p['_instituciones']:
            iid = i.get('idInstitucion')
            if iid is None:
                continue
            pares_inst[(idf, iid)] = {'aviso_id': idf, 'id_institucion': iid}
            m = inst_meta.setdefault(iid, {
                'id_institucion': iid,
                'id_institucion_sqlserver': i.get('idInstitucionSqlServer'),
                'nombre_institucion': i.get('nombreInstitucion'),
                'n_avisos_acum': 0, 'primera_vez_visto': None,
                'ultima_vez_visto': None})
            m['primera_vez_visto'] = minimo(m['primera_vez_visto'], fecha)
            m['ultima_vez_visto'] = maximo(m['ultima_vez_visto'], fecha)

        # ── empresas ──
        eid = p['empresa_id']
        if eid is not None:
            if p['empresa_nombre']:
                emp_nombres[eid][p['empresa_nombre']] += 1
            m = emp_meta.setdefault(eid, {
                'empresa_id': eid, 'empresa_id_alt': p['empresa_id_alt'],
                '_avisos': set(), 'primera_vez_visto': None,
                'ultima_vez_visto': None, '_areas': set()})
            m['_avisos'].add(idf)
            m['primera_vez_visto'] = minimo(m['primera_vez_visto'], fecha)
            m['ultima_vez_visto'] = maximo(m['ultima_vez_visto'], fecha)
            m['_areas'].add(p['_area'])

    # ══ conteos sobre pares deduplicados ════════════════════════
    # Un aviso observado en varias corridas es UN aviso, no N. Los
    # contadores se derivan de las claves compuestas, no del loop.
    n_por_carrera = Counter(f['carrera_trabajando'] for f in pares_car.values()
                            if f['fuente'] == 'declarada')
    n_especifico  = Counter(
        f['carrera_trabajando'] for f in pares_car.values()
        if f['fuente'] == 'declarada'
        and (f['n_carreras_declaradas_aviso'] or 0) <= UMBRAL_AVISO_GENERICO)
    n_por_inst    = Counter(f['id_institucion'] for f in pares_inst.values())
    conf_por_emp  = Counter(a['empresa_id'] for a in avisos.values()
                            if a['empresa_confidencial']
                            and a['empresa_id'] is not None)

    # ══ escritura ═══════════════════════════════════════════════
    M = lambda n: os.path.join(dir_maestras, n)

    # nombre canónico de empresa: variante no confidencial más frecuente,
    # acumulada sobre TODAS las áreas y periodos del crudo
    filas_emp = []
    for eid, m in emp_meta.items():
        nombres = emp_nombres.get(eid, Counter())
        filas_emp.append({
            'empresa_id': eid,
            'empresa_id_alt': m['empresa_id_alt'],
            'nombre_canonico': nombres.most_common(1)[0][0] if nombres else None,
            'nombres_observados': json.dumps(dict(nombres), ensure_ascii=False),
            'n_avisos_acumulados': len(m['_avisos']),
            'primera_vez_visto': m['primera_vez_visto'],
            'ultima_vez_visto': m['ultima_vez_visto'],
            'areas_observadas': ' | '.join(sorted(x for x in m['_areas'] if x)),
            'siempre_confidencial': not bool(nombres),
            'n_avisos_confidenciales': conf_por_emp.get(eid, 0),
        })

    filas_car = []
    for nombre, m in car_meta.items():
        m['n_avisos_acum'] = n_por_carrera.get(nombre, 0)
        m['n_avisos_especificos'] = n_especifico.get(nombre, 0)
        m['areas_observadas'] = ' | '.join(sorted(x for x in m.pop('_areas') if x))
        filas_car.append(m)
    filas_car.sort(key=lambda r: (-r['n_avisos_especificos'], -r['n_avisos_acum']))

    for iid, m in inst_meta.items():
        m['n_avisos_acum'] = n_por_inst.get(iid, 0)
    filas_inst = sorted(inst_meta.values(), key=lambda r: -r['n_avisos_acum'])

    n_av = escribir_csv_simple(M('avisos.csv'), list(avisos.values()),
                               COLS_AVISOS)
    n_ac = escribir_csv_simple(M('aviso_carrera.csv'), list(pares_car.values()),
                               ['aviso_id', 'carrera_trabajando',
                                'termino_busqueda', 'fuente',
                                'n_carreras_declaradas_aviso'])
    n_ah = escribir_csv_simple(M('aviso_habilidad.csv'), list(pares_hab.values()),
                               ['aviso_id', 'habilidad', 'nivel'])
    n_ai = escribir_csv_simple(M('aviso_institucion.csv'),
                               list(pares_inst.values()),
                               ['aviso_id', 'id_institucion'])
    n_em, man_em = escribir_csv(M('empresas.csv'), filas_emp,
                                COLS_EMPRESAS, 'empresa_id')
    n_ca, man_ca = escribir_csv(M('carreras_trabajando.csv'), filas_car,
                                COLS_CARRERAS, 'carrera_trabajando')
    n_in, man_in = escribir_csv(M('instituciones.csv'), filas_inst,
                                COLS_INSTITUCIONES, 'id_institucion')

    # ══ resumen ═════════════════════════════════════════════════
    vals = list(avisos.values())
    ok   = [a for a in vals if a['detalle_ok']]
    pct  = lambda x, b: f"{x*100/b:.1f}%" if b else "-"
    est  = Counter(a['estado_ultimo'] for a in vals)
    conf = sum(1 for a in vals if a['empresa_confidencial'])
    con_id = sum(1 for a in vals if a['empresa_id'] is not None)
    recup = sum(1 for a in vals if a['empresa_confidencial']
                and emp_nombres.get(a['empresa_id']))
    obs   = [a for a in vals if a['calidad_duracion'] == 'observada']
    cota  = [a for a in vals if a['calidad_duracion'] == 'cota_superior']
    dur   = sorted(a['dias_publicado_hasta_baja'] for a in obs
                   if a['dias_publicado_hasta_baja'] is not None)
    genericos = sum(1 for a in vals
                    if (a['n_carreras_declaradas'] or 0) > UMBRAL_AVISO_GENERICO)

    print(f"\n{'='*64}\n  MAESTRAS  →  {dir_maestras}/\n{'='*64}")
    print(f"  avisos.csv              {n_av:7d}")
    print(f"  aviso_carrera.csv       {n_ac:7d}")
    print(f"  aviso_habilidad.csv     {n_ah:7d}")
    print(f"  aviso_institucion.csv   {n_ai:7d}")
    print(f"  empresas.csv            {n_em:7d}   (+{man_em} col. manuales)")
    print(f"  carreras_trabajando.csv {n_ca:7d}   (+{man_ca} col. manuales)")
    print(f"  instituciones.csv       {n_in:7d}   (+{man_in} col. manuales)")

    print(f"\n  Avisos con detalle ok  : {len(ok)}/{len(vals)}")
    print(f"  Estado (última vista)  : "
          + ', '.join(f"{k}={v}" for k, v in est.most_common()))
    print(f"  Confidenciales         : {conf} ({pct(conf, len(vals))})")
    print(f"    con empresa_id       : {con_id}")
    print(f"    identificados por id : {recup} "
          f"({pct(recup, max(conf,1))} de los confidenciales)")
    print(f"  Sin carreras declaradas: "
          f"{sum(1 for a in ok if not a['n_carreras_declaradas'])}")
    print(f"  Con habilidades        : "
          f"{sum(1 for a in ok if a['n_habilidades'])} "
          f"({pct(sum(1 for a in ok if a['n_habilidades']), max(len(ok),1))})")

    print(f"\n  PANEL")
    print(f"    vistos en >1 corrida : "
          f"{sum(1 for a in vals if a['n_corridas_visto'] > 1)}")
    print(f"    duración observada   : {len(obs)}  (PUBLICADA → DESACTIVADA)")
    print(f"    solo cota superior   : {len(cota)}  "
          f"(ya estaban de baja al primer avistamiento)")
    print(f"    censuradas           : "
          f"{sum(1 for a in vals if a['censurado'])}")
    if dur:
        print(f"    días publicado→baja  : mediana {dur[len(dur)//2]}, "
              f"p25 {dur[len(dur)//4]}, p75 {dur[3*len(dur)//4]}, "
              f"max {dur[-1]}   ← solo las observadas")
    else:
        print(f"    días publicado→baja  : sin mediciones válidas todavía "
              f"(hace falta ver el mismo aviso en dos corridas)")

    print(f"\n  TAXONOMÍA OBSERVADA")
    print(f"    carreras distintas     : {len(filas_car)}")
    print(f"    instituciones distintas: {len(filas_inst)}")
    print(f"    avisos genéricos       : {genericos} "
          f"({pct(genericos, len(vals))}) — declaran >"
          f"{UMBRAL_AVISO_GENERICO} carreras")
    if filas_car:
        tot = sum(r['n_avisos_especificos'] for r in filas_car)
        print(f"    cobertura por n_avisos_especificos "
              f"(ignora los genéricos):")
        for n in (50, 100, 200):
            if len(filas_car) > n:
                acum = sum(r['n_avisos_especificos'] for r in filas_car[:n])
                print(f"      top {n:3d} carreras cubren {pct(acum, tot)}")
    print(f"\n  Siguiente: completar la homologación a mano en "
          f"{M('carreras_trabajando.csv')}")
    print(f"  (agregar columnas carrera_sies / tipo_relacion / revisado_por;")
    print(f"   sobreviven a las corridas siguientes)")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--crudo', default='crudo')
    ap.add_argument('--maestras', default='maestras')
    a = ap.parse_args()
    main(a.crudo, a.maestras)
