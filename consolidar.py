"""
Consolidación — crudo JSONL → maestras CSV acumuladas
======================================================
Lee todos los crudo_*.jsonl y hace UPSERT sobre nueve tablas.
Es idempotente y reprocesable: se puede correr las veces que sea, y si
mañana cambia un criterio de parseo, se vuelve a correr sobre el mismo
crudo sin tocar la red.

Tablas (directorio maestras/):

  avisos.csv               1 fila por aviso_id — panel longitudinal
  aviso_carrera.csv        1 fila por (aviso × carrera declarada)
  aviso_termino.csv        1 fila por (aviso × término de búsqueda)
  aviso_habilidad.csv      1 fila por (aviso × habilidad)
  aviso_institucion.csv    1 fila por (aviso × institución)
  aviso_programa.csv       1 fila por (aviso × programa o campo ISCED)
  empresas.csv             1 fila por empresa_id  ← columnas manuales
  carreras_trabajando.csv  1 fila por nombre      ← columnas manuales
  instituciones.csv        1 fila por id_institucion

COLUMNAS MANUALES
  Las columnas que el script no gestiona se PRESERVAN en el upsert.
  Si agregás `rubro` o `tamano` a empresas.csv a mano, sobreviven a las
  corridas siguientes. Lo mismo con la homologación en
  carreras_trabajando.csv. Las columnas gestionadas se sobrescriben.

HOMOLOGACIÓN
  No se decide acá: se APLICA. `maestras/homologacion.csv` es trabajo
  humano —qué programa propio o qué campo ISCED nombra cada una de las
  528 carreras de trabajando— y este script solo la cuelga de cada
  aviso, en `aviso_programa.csv`. Si el archivo no está, esa tabla no se
  escribe y se avisa; el resto de la consolidación no cambia.

  El cruce pasa siempre por `homologacion.clave()`, que colapsa espacios
  y mayúsculas. Las carreras NO traen ID en la API, así que la clave es
  el nombre, y el nombre viene con espacios de más en once de los 528.

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

# Los catálogos (programas propios, ISCED-F) viven junto al código, no
# con los datos: cambian cuando cambia el criterio, no cuando llegan
# avisos nuevos.
REPO = os.path.dirname(os.path.abspath(__file__))

# Ruta A (término de búsqueda → SIES). Import blando: si el módulo no
# está, el resto de la consolidación sigue funcionando y las columnas
# derivadas quedan vacías, pero se avisa en pantalla. No falla en
# silencio.
try:
    from carreras_sies_2026 import TERMINO_A_SIES, TERMINO_A_AREAS
    SIES_DISPONIBLE = True
except ImportError:
    TERMINO_A_SIES, TERMINO_A_AREAS = {}, {}
    SIES_DISPONIBLE = False

# El join carrera declarada → programa propio. Mismo import blando: sin
# el módulo o sin el archivo de homologación, `aviso_programa.csv` no se
# escribe y se avisa en pantalla.
try:
    from homologacion import Homologacion
    JOIN_DISPONIBLE = True
except ImportError:
    Homologacion = None
    JOIN_DISPONIBLE = False

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


def slugificar(idf, titulo):
    """Reconstruye el slug de la URL pública: `{id}-{titulo-normalizado}`.

    POR QUÉ HACE FALTA. La API trae `slug` en solo el 7% de los avisos.
    Para el resto, v9 emitía `/trabajo/{id}` a secas — un patrón que
    nunca se probó contra el sitio y que **no resuelve**: la columna
    `url` apuntaba a ninguna parte para nueve de cada diez avisos.

    VERIFICADO, y no contra un caso. Sobre los 676 avisos que sí traen
    `slug`, esta regla reproduce el valor real en el **100%**. Por eso
    se puede aplicar al 93% restante sin volver a golpear el sitio.

    Devuelve None si el título no deja ningún carácter utilizable: es
    preferible una URL vacía a una que se sabe rota.
    """
    s = unicodedata.normalize('NFD', str(titulo or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return f"{idf}-{s}" if s else None


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
    'n_carreras_declaradas', 'hash_carreras', 'n_avisos_mismo_conjunto',
    'n_habilidades', 'n_instituciones',
    'postulaciones', 'visualizaciones',
    # flags
    'destacada', 'inclusiva', 'tipo_curriculum', 'usa_score_screening',
    # auditoría
    'areas_scraping', 'terminos_busqueda', 'n_terminos_busqueda',
    # ruta A: derivado del término de búsqueda, no de lo que declara el
    # aviso. Sobre-atribuye por diseño (ver carreras_sies_2026.py).
    'sies_por_termino', 'n_sies_por_termino', 'areas_sies_por_termino',
    'n_terminos_sin_mapeo',
    'detalle_ok', 'detalle_motivo',
]

COLS_AVISO_TERMINO = [
    'aviso_id', 'termino_busqueda', 'carrera_sies', 'areas_sies', 'mapeado',
]

# Las tablas de pares también declaran su esquema acá y no en la llamada
# a escribir_csv_simple: diccionario.py los importa para saber qué
# columna viene del código y cuál se agregó a mano.
COLS_AVISO_CARRERA = [
    'aviso_id', 'carrera_trabajando', 'termino_busqueda', 'fuente',
    'n_carreras_declaradas_aviso',
]

COLS_AVISO_HABILIDAD = ['aviso_id', 'habilidad', 'nivel']

COLS_AVISO_INSTITUCION = [
    'aviso_id', 'id_institucion', 'n_carreras_declaradas_aviso',
]

COLS_AVISO_PROGRAMA = [
    'aviso_id', 'tipo_entrada', 'programa_propio', 'area_sies',
    'isced_amplio_cod', 'isced_estrecho_cod', 'isced_detallado_cod',
    'n_carreras_origen', 'carreras_origen', 'atribucion_multiple',
    'n_carreras_declaradas_aviso',
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
# `n_avisos_especificos` cuenta solo los avisos por debajo del umbral,
# y es el orden correcto para priorizar la homologación manual.
#
# El catálogo observado en carreras_trabajando.csv llevaba 506 nombres
# distintos con dos áreas scrapeadas (agosto 2026); crece con cada área
# nueva. Hay avisos que tildan una fracción enorme de ese catálogo.
#
# Por qué 30 y no 20. La distribución observada es bimodal con un hueco
# enorme: en Humanidades y en Derecho el máximo legítimo es 25 y el
# siguiente valor es 504. Cualquier corte dentro de ese hueco da el
# mismo resultado. 20 caía FUERA del hueco y marcaba como genérico el
# aviso 6102956 (Universidad Mayor, 25 carreras), que es un concurso
# académico legítimamente multidisciplinario. Medido: pasar de 20 a 30
# solo cambia ese aviso — 25 carreras suben +1 en n_avisos_especificos
# y nada más. Revisar el corte si aparece un área que puebla el hueco.
UMBRAL_AVISO_GENERICO = 30

COLS_INSTITUCIONES = [
    'id_institucion', 'id_institucion_sqlserver', 'nombre_institucion',
    'n_avisos_acum', 'n_avisos_especificos',
    'primera_vez_visto', 'ultima_vez_visto',
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
    idf    = reg['aviso_id']
    titulo = detalle.get('nombreCargo') or listado.get('nombreCargo')
    # El slug real cuando la API lo trae; si no, se reconstruye desde el
    # título. Son equivalentes —la regla se validó contra los 676 que lo
    # traen— pero se prefiere el original por si el sitio cambia el
    # criterio en el futuro: ahí la diferencia sería la señal.
    slug_url = detalle.get('slug') or slugificar(idf, titulo)

    return {
        'aviso_id': idf,
        'url': (f"https://www.trabajando.cl/trabajo/{slug_url}"
                if slug_url else None),
        'titulo': titulo,
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

def derivar_aviso_programa(pares_car, ruta_hom, ruta_prog, ruta_isced):
    """aviso × destino de la homologación, con el campo ISCED colgado.

    GRANO. Una fila por (aviso, destino). Si dos carreras declaradas del
    mismo aviso caen en el mismo programa, es UNA fila —el aviso pide un
    programa, no dos— y `n_carreras_origen` guarda que fueron dos.

    QUÉ ENTRA. Solo `fuente == 'declarada'`: las filas `keyword_only`
    son trazabilidad del término buscado, no atribución de carrera
    (§5.6). Y solo los destinos que existen: `nivel_formativo`,
    `solo_ocupacion` y `no_informativo` **no producen fila**, porque el
    aviso no nombró ninguna formación. Son el 1,4% de las menciones y
    perderlas acá es correcto; siguen en `aviso_carrera.csv`.

    POR QUÉ INCLUYE LOS CAMPOS ISCED Y NO SOLO LOS PROGRAMAS. Dejar
    afuera `campo_iscedf` haría que un conteo por campo —el uso natural
    de esta tabla— se comiera el 5,7% de las menciones sin avisar.
    `tipo_entrada` separa los dos casos en un predicado.

    `atribucion_multiple` marca las filas que vienen de una carrera que
    abría a varios destinos: el aviso nombró algo ambiguo y esta fila es
    una de varias lecturas. Sumarlas como si fueran demanda distinta
    infla el conteo. Lección 7: la calidad del dato, en el dato.
    """
    hom = Homologacion.cargar(ruta_hom, obligatoria=False)
    if hom is None:
        return None, f"no está {ruta_hom}"
    prog = {r['programa_propio']: r for r in leer_csv(ruta_prog)}
    if not prog:
        return None, f"no está {ruta_prog}"
    jerarquia = {r['codigo']: r['jerarquia'] for r in leer_csv(ruta_isced)}

    def codigos_isced(cod):
        """amplio / estrecho / detallado a partir de un código suelto.
        La jerarquía ISCED-F es por prefijo: 0713 ⊂ 071 ⊂ 07."""
        cod = (cod or '').strip()
        if not cod or cod not in jerarquia:
            return '', '', ''
        return (cod[:2],
                cod[:3] if len(cod) >= 3 else '',
                cod if len(cod) >= 4 else '')

    filas = {}
    for par in pares_car.values():
        if par.get('fuente') != 'declarada':
            continue
        nombre = par['carrera_trabajando']
        destinos = hom.destinos(nombre)
        for d in destinos:
            programa = (d.get('programa_propio') or '').strip()
            campo = (d.get('isced_cod') or '').strip()
            if programa:
                p = prog.get(programa)
                if not p:
                    continue
                llave, area = programa, p['area_sies']
                amplio, estrecho, detallado = (p['isced_amplio_cod'],
                                               p['isced_estrecho_cod'],
                                               p['isced_detallado_cod'])
            elif campo:
                llave, area = f'isced:{campo}', ''
                amplio, estrecho, detallado = codigos_isced(campo)
            else:
                continue

            f = filas.setdefault((par['aviso_id'], llave), {
                'aviso_id': par['aviso_id'],
                'tipo_entrada': d.get('tipo_entrada'),
                'programa_propio': programa or None,
                'area_sies': area or None,
                'isced_amplio_cod': amplio or None,
                'isced_estrecho_cod': estrecho or None,
                'isced_detallado_cod': detallado or None,
                'n_carreras_origen': 0,
                '_origen': set(),
                'atribucion_multiple': False,
                'n_carreras_declaradas_aviso':
                    par.get('n_carreras_declaradas_aviso'),
            })
            f['_origen'].add(nombre)
            f['atribucion_multiple'] |= len(destinos) > 1

    for f in filas.values():
        origen = sorted(f.pop('_origen'))
        f['n_carreras_origen'] = len(origen)
        f['carreras_origen'] = ' | '.join(origen)
    return list(filas.values()), None


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
    pares_term   = {}
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

        # ── ruta A ────────────────────────────────────────────
        sies_t  = sorted({TERMINO_A_SIES[t] for t in terms
                          if t in TERMINO_A_SIES})
        areas_t = sorted({a for t in terms
                          for a in TERMINO_A_AREAS.get(t, ())})
        p['sies_por_termino']       = ' | '.join(sies_t)
        p['n_sies_por_termino']     = len(sies_t)
        p['areas_sies_por_termino'] = ' | '.join(areas_t)
        p['n_terminos_sin_mapeo']   = sum(1 for t in terms
                                          if t not in TERMINO_A_SIES)
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
        # Hash del CONJUNTO de carreras declaradas. Junto con
        # n_avisos_mismo_conjunto identifica los perfiles guardados —un
        # empleador que adjunta la misma lista a todos sus avisos— sin
        # depender de UMBRAL_AVISO_GENERICO. Medido en agosto 2026: el
        # tamaño del conjunto NO separa la plantilla del concurso
        # multidisciplinario legítimo (hay plantillas de 20 y concursos
        # de 25), así que el umbral por conteo no alcanza.
        #
        # Vacío cuando el aviso no declara carreras: 3.703 avisos sin
        # carreras no comparten un conjunto, no tienen ninguno. Meterlos
        # todos bajo el mismo hash inventaría el grupo más grande de la
        # tabla.
        p['hash_carreras'] = (
            __import__('hashlib').sha1(
                '|'.join(sorted(normalizar(c) for c in p['_carreras']))
                .encode('utf-8')).hexdigest()[:16]
            if p['_carreras'] else None)
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

        # Ruta A completa: un par por (aviso × término), declare o no
        # carreras el aviso. Es la tabla puente hacia SIES que no
        # requiere trabajo manual.
        #
        # NOTA: esta tabla supersede las filas fuente='keyword_only' de
        # aviso_carrera.csv — verificado que son subconjunto estricto
        # (151 ⊂ 342 en Derecho). Se dejan por compatibilidad con
        # análisis existentes; conviene retirarlas en una limpieza
        # posterior, no acá.
        for t in p['_terminos']:
            pares_term[(idf, t)] = {
                'aviso_id': idf,
                'termino_busqueda': t,
                'carrera_sies': TERMINO_A_SIES.get(t),
                'areas_sies': ' | '.join(TERMINO_A_AREAS.get(t, ())) or None,
                'mapeado': t in TERMINO_A_SIES}

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
            pares_inst[(idf, iid)] = {
                'aviso_id': idf, 'id_institucion': iid,
                'n_carreras_declaradas_aviso': p['n_carreras_declaradas']}
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
    # Mismo criterio que en carreras: los avisos que tildan media
    # taxonomía también tildan casi todas las instituciones.
    n_inst_espec  = Counter(
        f['id_institucion'] for f in pares_inst.values()
        if (f['n_carreras_declaradas_aviso'] or 0) <= UMBRAL_AVISO_GENERICO)
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
        m['n_avisos_especificos'] = n_inst_espec.get(iid, 0)
    filas_inst = sorted(inst_meta.values(),
                        key=lambda r: (-r['n_avisos_especificos'],
                                       -r['n_avisos_acum']))

    # Segunda pasada: cuántos avisos comparten cada conjunto de
    # carreras. Se cuenta sobre `avisos`, que ya está deduplicado por
    # aviso_id; contarlo dentro del ciclo de observaciones inflaría el
    # número tantas veces como áreas haya visto cada aviso.
    conteo_conjuntos = Counter(a['hash_carreras'] for a in avisos.values()
                               if a.get('hash_carreras'))
    for a in avisos.values():
        h = a.get('hash_carreras')
        a['n_avisos_mismo_conjunto'] = conteo_conjuntos[h] if h else None

    n_av = escribir_csv_simple(M('avisos.csv'), list(avisos.values()),
                               COLS_AVISOS)
    n_ac = escribir_csv_simple(M('aviso_carrera.csv'), list(pares_car.values()),
                               COLS_AVISO_CARRERA)
    n_at = escribir_csv_simple(M('aviso_termino.csv'),
                               list(pares_term.values()), COLS_AVISO_TERMINO)
    n_ah = escribir_csv_simple(M('aviso_habilidad.csv'), list(pares_hab.values()),
                               COLS_AVISO_HABILIDAD)
    n_ai = escribir_csv_simple(M('aviso_institucion.csv'),
                               list(pares_inst.values()),
                               COLS_AVISO_INSTITUCION)
    # Homologación: una tabla más, no una columna en las existentes.
    # El grano cambia —una carrera puede abrir a varios programas y dos
    # carreras pueden cerrar en uno—, así que colgarla de
    # aviso_carrera.csv obligaría a listas dentro de una celda.
    n_ap, aviso_prog = 0, None
    if JOIN_DISPONIBLE:
        aviso_prog, falta = derivar_aviso_programa(
            pares_car, M('homologacion.csv'),
            os.path.join(REPO, 'programas_propios.csv'),
            os.path.join(REPO, 'isced_f_2013.csv'))
        if aviso_prog is None:
            print(f"\n  ⚠  Sin aviso_programa.csv: {falta}")
        else:
            n_ap = escribir_csv_simple(M('aviso_programa.csv'), aviso_prog,
                                       COLS_AVISO_PROGRAMA)
    else:
        print("\n  ⚠  Sin aviso_programa.csv: falta homologacion.py")

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
    print(f"  aviso_termino.csv       {n_at:7d}")
    print(f"  aviso_habilidad.csv     {n_ah:7d}")
    print(f"  aviso_institucion.csv   {n_ai:7d}")
    if n_ap:
        print(f"  aviso_programa.csv      {n_ap:7d}")
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
    print(f"    instituciones distintas: {len(filas_inst)}  "
          f"(en avisos específicos: "
          f"{sum(1 for r in filas_inst if r['n_avisos_especificos'])})")
    print(f"    avisos genéricos       : {genericos} "
          f"({pct(genericos, len(vals))}) — declaran >"
          f"{UMBRAL_AVISO_GENERICO} carreras")

    # Conjuntos reutilizados: la señal que no depende del umbral.
    comp = [(n, h) for h, n in conteo_conjuntos.items() if n > 1]
    n_en_comp = sum(n for n, _ in comp)
    s_ = '' if len(comp) == 1 else 's'
    print(f"    conjuntos compartidos  : {len(comp)} conjunto{s_} en "
          f"{n_en_comp} avisos")
    if comp:
        tam = {a['hash_carreras']: a['n_carreras_declaradas']
               for a in avisos.values() if a.get('hash_carreras')}
        print(f"      los mayores (avisos × tamaño del conjunto):")
        for n, h in sorted(comp, reverse=True)[:5]:
            print(f"        {n:>4} avisos × {tam.get(h, '?')} carreras")
    if filas_car:
        tot = sum(r['n_avisos_especificos'] for r in filas_car)
        print(f"    cobertura por n_avisos_especificos "
              f"(ignora los genéricos):")
        for n in (50, 100, 200):
            if len(filas_car) > n:
                acum = sum(r['n_avisos_especificos'] for r in filas_car[:n])
                print(f"      top {n:3d} carreras cubren {pct(acum, tot)}")
    # ══ ruta A ══════════════════════════════════════════════════
    print(f"\n  RUTA A — término de búsqueda → SIES")
    if not SIES_DISPONIBLE:
        print(f"    ⚠  carreras_sies_2026.py no importable. Las columnas")
        print(f"       sies_por_termino quedaron VACÍAS. Corré consolidar.py")
        print(f"       desde el directorio del repo.")
    else:
        sin_map = sorted({f['termino_busqueda'] for f in pares_term.values()
                          if not f['mapeado']})
        con_sies = sum(1 for a in vals if a['n_sies_por_termino'])
        print(f"    avisos con ≥1 SIES por término : "
              f"{con_sies} ({pct(con_sies, len(vals))})")
        print(f"    términos sin mapeo             : {len(sin_map)}")
        for t in sin_map[:10]:
            print(f"        {t}")
        if len(sin_map) > 10:
            print(f"        ... y {len(sin_map) - 10} más")
        print(f"    Recordá: sobre-atribuye. Es contexto, no clasificación.")

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
