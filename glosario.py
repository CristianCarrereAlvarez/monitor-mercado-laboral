"""
Glosas de las columnas — la parte escrita a mano del diccionario
================================================================

Esto es lo único del diccionario que una persona escribe. `diccionario.py`
lee los datos reales, los cruza con este archivo y emite DICCIONARIO.md
marcando qué está descrito, qué no, y qué sobra.

POR QUÉ UN MÓDULO DE PYTHON Y NO UN CSV
  La homologación de carreras es un CSV porque son 528 filas de trabajo
  repetitivo que se hace mejor en una planilla. Esto es lo contrario:
  prosa, de pocas líneas por entrada, que se escribe una vez y se lee
  en el editor al lado del código que produce la columna. Un CSV con
  párrafos adentro se vuelve ilegible en git y obliga a escapar comillas.

REGLA AL ESCRIBIR UNA GLOSA
  Solo se documenta lo verificado. Si no sabés qué significa una
  columna, **no inventes una glosa**: dejala afuera y el diccionario la
  va a listar como SIN DOCUMENTAR, que es información verdadera. Una
  glosa plausible pero falsa es peor que un hueco visible.

QUÉ PONER
  Qué es, de dónde sale, y la trampa si la tiene. Lo que un lector
  necesita para no usarla mal. Las advertencias importan más que las
  definiciones: `modalidad` no se entiende sin saber que 'No informado'
  es deliberado.
"""

# Metadatos por tabla: grano y clave. Se usan en el encabezado de cada
# sección del documento.
TABLAS = {
    'avisos.csv': ('1 fila por aviso', 'aviso_id'),
    'aviso_carrera.csv': ('1 fila por (aviso × carrera declarada)',
                          'aviso_id + carrera_trabajando'),
    'aviso_termino.csv': ('1 fila por (aviso × término de búsqueda)',
                          'aviso_id + termino_busqueda'),
    'aviso_habilidad.csv': ('1 fila por (aviso × habilidad)',
                            'aviso_id + habilidad'),
    'aviso_institucion.csv': ('1 fila por (aviso × institución)',
                              'aviso_id + id_institucion'),
    'empresas.csv': ('1 fila por empresa', 'empresa_id'),
    'carreras_trabajando.csv': ('1 fila por nombre de carrera observado',
                                'carrera_trabajando'),
    'instituciones.csv': ('1 fila por institución', 'id_institucion'),
    'homologacion_carreras.csv': (
        '1 fila por (nombre de carrera × nivel)',
        'carrera_trabajando + nivel_condicion'),
}

# Tablas que admiten columnas manuales: cualquier columna que no esté en
# el esquema del código se preserva por clave entre corridas. En estas,
# una columna "manual" es una función, no una anomalía.
CON_COLUMNAS_MANUALES = {
    'empresas.csv', 'carreras_trabajando.csv', 'instituciones.csv',
    'homologacion_carreras.csv',
}


GLOSAS = {

    # ══════════════════════════════════════════════════════════════
    'avisos.csv': {

        # ── identidad ──
        'aviso_id':
            "Identificador del aviso en trabajando.cl (`idOferta`). "
            "**Estable entre corridas**: es lo que permite el panel "
            "longitudinal y lo que deduplica un mismo aviso encontrado "
            "en varias áreas.",
        'url':
            "URL pública del aviso, con la forma "
            "`/trabajo/{id}-{titulo-normalizado}`. La API trae `slug` "
            "solo en el 7% de los avisos; para el resto se reconstruye "
            "desde el título con `slugificar()`. La regla se validó "
            "contra los 676 que sí lo traen y lo reproduce en el "
            "**100%**. Vacía cuando el título no deja ningún carácter "
            "utilizable — mejor sin URL que con una rota. (Hasta agosto "
            "2026 se emitía `/trabajo/{id}` a secas, que no resuelve: "
            "nueve de cada diez URLs apuntaban a ninguna parte.)",

        # ── panel longitudinal ──
        'primera_vez_visto':
            "Primera `fecha_scraping` en que el aviso apareció en algún "
            "crudo.",
        'ultima_vez_visto':
            "Última `fecha_scraping` en que apareció.",
        'n_corridas_visto':
            "**Cuenta observaciones, no corridas.** Incrementa una vez "
            "por registro de crudo, y un mismo aviso aparece en varias "
            "áreas de la misma corrida: en agosto 2026, 5.910 avisos "
            "tenían >1 con una sola corrida mensual hecha. Para contar "
            "corridas reales, usar `periodos_visto`.",
        'periodos_visto':
            "Períodos `YYYY_MM` en que se vio el aviso, separados por "
            "` | `. **Es la columna longitudinal correcta.**",
        'estado_primero':
            "`estadoOferta` en la primera observación: PUBLICADA o "
            "DESACTIVADA.",
        'estado_ultimo':
            "`estadoOferta` en la última observación. La búsqueda "
            "devuelve avisos ya cerrados, así que DESACTIVADA aparece "
            "desde el primer avistamiento.",
        'fecha_desactivacion_detectada':
            "Primera fecha de scraping en que se vio DESACTIVADA. **No "
            "es la fecha real de baja**: está acotada por el intervalo "
            "entre corridas.",
        'dias_publicado_hasta_baja':
            "Días entre `fecha_publicacion` y "
            "`fecha_desactivacion_detectada`. **Sin leer "
            "`calidad_duracion` este número no significa nada.**",
        'calidad_duracion':
            "Tres valores que NO se deben mezclar: `observada` (se vio "
            "PUBLICADA y después DESACTIVADA — única medición real), "
            "`cota_superior` (ya estaba de baja al primer avistamiento; "
            "es un techo) y `censurada` (seguía viva). Promediarlos "
            "juntos sesga la mediana hacia arriba.",
        'censurado':
            "True si nunca se detectó la desactivación. Equivale a "
            "`calidad_duracion == 'censurada'`.",

        # ── contenido ──
        'titulo':      "`nombreCargo` del detalle.",
        'descripcion': "`descripcionOferta`, con el HTML removido.",
        'requisitos':  "`requisitosMinimos`, con el HTML removido.",
        'hash_contenido':
            "SHA-1 (16 hex) de `empresa_id` + título normalizado + los "
            "primeros 2.000 caracteres de la descripción normalizada. "
            "Permite detectar avisos de contenido equivalente con "
            "distinto `aviso_id` (republicaciones). Ningún análisis lo "
            "usa todavía.",

        # ── empresa ──
        'empresa_id':
            "`idCompany` del detalle. Es la clave de empresa y la que "
            "aparece en `urlLogo`. Sirve para acumular información sobre "
            "empresas; **no para desanonimizar avisos confidenciales en "
            "una publicación**.",
        'empresa_id_alt':
            "`idEmpresa`, la segunda clave que expone la API. Biyectiva "
            "con `empresa_id` en la muestra observada (n=40).",
        'empresa_nombre':
            "`nombreEmpresaFantasia`, o el nombre del listado. **Vacío a "
            "propósito cuando el aviso es confidencial**, aunque la API "
            "sí lo devuelva.",
        'empresa_confidencial':
            "`ofertaConfidencial` del detalle. Si no hubo detalle, se "
            "infiere de que el nombre sea literalmente 'Empresa "
            "Confidencial'.",

        # ── fechas ──
        'fecha_publicacion':
            "Fecha de publicación declarada por la API, en ISO. Viene "
            "exacta en cada aviso, así que no se pierde aunque el "
            "monitor empiece a observar tarde.",
        'fecha_expiracion':
            "Fecha de expiración declarada, en ISO.",
        'vigencia_declarada_dias':
            "Días entre publicación y expiración declarada. **No es "
            "duración de vacante**: las bajas ocurren mucho antes del "
            "vencimiento (mediana declarada: 59 días).",

        # ── cargo ──
        'tipo_cargo':  "`nombreTipoCargo` del detalle.",
        'area_funcional':
            "`nombreArea` de la API. **Describe al empleador, no el área "
            "del monitor**: el 80% dice 'Otra Área' y en Derecho el "
            "segundo valor más frecuente fue 'Estimulación temprana' "
            "(Fundación Integra). No confundir con `areas_scraping`.",
        'vacantes':    "`cantidadVacantes`.",

        # ── ubicación ──
        'region':
            "`ubicacion.nombreRegion` del detalle; si falta, la segunda "
            "parte del texto de ubicación del listado partido por comas.",
        'comuna':
            "`ubicacion.nombreComuna`; si falta, la primera parte del "
            "texto de ubicación del listado.",
        'direccion':     "`ubicacion.direccion`.",
        'codigo_postal': "`ubicacion.codigoPostal`.",
        'latitud':
            "Latitud, **ya en el orden correcto**. En el crudo, "
            "`ubicacion.coordenadas` dice `type: Point` pero trae "
            "[lat, lon], al revés de GeoJSON; `consolidar.py` lo "
            "desarma bien. Verificado con Antofagasta.",
        'longitud':
            "Longitud, ya en el orden correcto. Ver `latitud`.",

        # ── condiciones ──
        'jornada':
            "`nombreJornada` tal cual viene. **Mezcla tres dimensiones**: "
            "extensión horaria (Completa, Part Time), modalidad "
            "(Teletrabajo, Mixta) y tipo de contrato (Práctica, "
            "Reemplazo, Free Lance). Por eso hay dos columnas derivadas.",
        'modalidad':
            "Derivada de `jornada`. Solo dice Híbrido, Remoto o "
            "Presencial cuando la jornada lo informa; el resto es **'No "
            "informado', nunca 'Presencial' por defecto**. v7 mapeaba "
            "'Jornada Completa' a Presencial y eso inventaba el dato "
            "para el 69% de los avisos.",
        'tipo_contrato':
            "Derivada de `jornada`: Práctica, Reemplazo, Freelance o "
            "Comisionista. Vacía cuando la jornada no menciona ninguna.",
        'sueldo_liquido':
            "`sueldo`, y solo si `mostrarSueldo` es verdadero y el monto "
            "es mayor que cero. Vacío en la enorme mayoría de los avisos "
            "(2,9% los muestra).",
        'muestra_sueldo': "`mostrarSueldo` del detalle.",
        'moneda':
            "`nombreMoneda`. Siempre 'Pesos Chilenos' en lo observado.",

        # ── requisitos ──
        'exp_operador':
            "`nombreOperadorExperiencia` (p. ej. 'Sin experiencia', "
            "'Más de'). Antes iba concatenado con los años en un string "
            "infiltrable; ahora son tres columnas.",
        'exp_anios':
            "`aniosExperiencia`, como número.",
        'exp_inconsistente':
            "True cuando la API se contradice: operador 'Sin "
            "experiencia' con `exp_anios` mayor que cero. **Marcar la "
            "contradicción en el dato en vez de resolverla a ciegas.**",
        'nivel_academico':
            "`nombreNivelAcademico` (Universitaria, Técnico profesional "
            "superior…). Es el desempate disponible para los casos 1:N "
            "de la homologación, donde SIES separa 'Ingeniería en' de "
            "'Técnico en' y trabajando no.",
        'situacion_academica':
            "`nombreSituacionAcademica` (titulado, egresado, cursando…).",

        # ── conteos ──
        'n_carreras_declaradas':
            "Cuántas carreras declara el aviso. **Se guarda el entero, "
            "no un flag**: el umbral de genericidad se decide en "
            "análisis (`UMBRAL_AVISO_GENERICO`, hoy 30). Diez avisos de "
            "un mismo empleador declaran 504 carreras y aparecen en "
            "cualquier búsqueda.",
        'hash_carreras':
            "Hash (16 hex) del **conjunto** de carreras declaradas, "
            "normalizado y ordenado: dos avisos con las mismas carreras "
            "en distinto orden comparten hash. **Vacío cuando el aviso "
            "no declara ninguna** — no declarar nada no es compartir un "
            "conjunto, y meterlos todos bajo un mismo hash inventaría el "
            "grupo más grande de la tabla.",
        'n_avisos_mismo_conjunto':
            "Cuántos avisos distintos declaran exactamente ese conjunto. "
            "**Identifica los perfiles guardados sin depender del "
            "umbral**: un empleador que adjunta la misma lista a todos "
            "sus avisos no está decidiendo por vacante. Bresler sale con "
            "10, AMERICAR con 4, y un concurso multidisciplinario "
            "legítimo (Universidad Mayor) sale con 1 porque cada "
            "convocatoria trae su propia lista. Hizo falta porque el "
            "tamaño del conjunto **no** separa esos dos casos: hay "
            "plantillas de 20 carreras y concursos legítimos de 25. "
            "Se cuenta sobre avisos deduplicados, no sobre "
            "observaciones. Vacío si `hash_carreras` lo está.",
        'n_habilidades':   "Cuántas habilidades declara el aviso.",
        'n_instituciones': "Cuántas instituciones declara el aviso.",
        'postulaciones':
            "`candidadPostulaciones` — el typo es de la API, no del "
            "monitor. Viene null de forma sistemática.",
        'visualizaciones':
            "`candidadVisualizaciones`. Mismo typo, mismo problema: "
            "llega null casi siempre.",

        # ── flags ──
        'destacada':  "`ofertaDestacada` del listado.",
        'inclusiva':  "`ofertaInclusiva` del listado.",
        'tipo_curriculum':     "`tipoCurriculumAceptado` del detalle.",
        'usa_score_screening': "`usaScoreScreening` del detalle.",

        # ── auditoría de captura ──
        'areas_scraping':
            "Áreas del monitor bajo las que se capturó el aviso, "
            "separadas por ` | `. Un aviso apareció en 1,9 áreas en "
            "promedio (agosto 2026). **Es trazabilidad de captura, no "
            "clasificación del aviso.**",
        'terminos_busqueda':
            "Términos de búsqueda que trajeron este aviso, separados "
            "por ` | `. **No es atribución de carrera**: el buscador "
            "matchea por prefijo sobre el cuerpo del aviso, así que dos "
            "avisos entraron por 'Derecho' vía la frase 'la mano derecha "
            "del gerente'.",
        'n_terminos_busqueda':
            "Cuántos términos distintos trajeron el aviso.",

        # ── ruta A ──
        'sies_por_termino':
            "Carreras SIES a las que corresponden los términos que "
            "encontraron el aviso. **Sobre-atribuye por diseño**: es "
            "señal de contexto, no clasificación. En Derecho los 342 "
            "avisos quedan con 'Derecho', incluidos 120 de salas cuna.",
        'n_sies_por_termino':
            "Cuántas carreras SIES distintas salen por esa vía.",
        'areas_sies_por_termino':
            "Áreas SIES de esos términos. Más principiada que "
            "`area_funcional`, que describe al empleador.",
        'n_terminos_sin_mapeo':
            "Términos del crudo que ya no existen en el catálogo SIES. "
            "**Detector de deriva**: si el catálogo se edita después de "
            "una corrida, este número deja de ser 0.",

        # ── captura ──
        'detalle_ok':
            "True si la llamada a `/api/ofertas/{id}` respondió bien. "
            "Cuando es False, las columnas que salen del detalle vienen "
            "vacías y solo hay datos del listado.",
        'detalle_motivo':
            "Por qué falló el detalle, cuando falló.",
    },

    # ══════════════════════════════════════════════════════════════
    'aviso_carrera.csv': {
        'aviso_id': "FK a `avisos.aviso_id`.",
        'carrera_trabajando':
            "Nombre de carrera **tal como lo declara el aviso**. La API "
            "no trae ID de carrera, solo el texto. Vacío en las filas "
            "`keyword_only`.",
        'termino_busqueda':
            "Término que encontró el aviso. Solo se llena en las filas "
            "`keyword_only`; en las `declarada` va vacío.",
        'fuente':
            "`declarada` = el aviso declara esa carrera (**única "
            "evidencia válida de atribución**). `keyword_only` = solo "
            "quedó registro del término que lo encontró. **Para "
            "cualquier análisis por carrera hay que filtrar "
            "`fuente == 'declarada'`.** Cuesta caro —el 40,6% de los "
            "avisos no declara carreras— y es el precio de no inventar "
            "atribución. Las filas `keyword_only` están superseded por "
            "`aviso_termino.csv` y conviene retirarlas.",
        'n_carreras_declaradas_aviso':
            "Copia de `avisos.n_carreras_declaradas`, para poder filtrar "
            "genéricos sin hacer join.",
    },

    # ══════════════════════════════════════════════════════════════
    'aviso_termino.csv': {
        'aviso_id': "FK a `avisos.aviso_id`.",
        'termino_busqueda':
            "Término del catálogo SIES con el que se buscó.",
        'carrera_sies':
            "Carrera SIES del término. Solo 16 de los 199 pares traducen "
            "algo distinto a la identidad; el valor real de la tabla "
            "está en esos 16 y en el área.",
        'areas_sies':
            "Áreas SIES del término, separadas por ` | `.",
        'mapeado':
            "Si el término se encontró en el catálogo. False señala "
            "deriva entre el crudo y el catálogo actual.",
    },

    # ══════════════════════════════════════════════════════════════
    'aviso_habilidad.csv': {
        'aviso_id':  "FK a `avisos.aviso_id`.",
        'habilidad': "`nombreHabilidad` del detalle.",
        'nivel':
            "`nombreNivel`. Casi siempre vacío: la API lo expone pero "
            "los empleadores no lo cargan.",
    },

    # ══════════════════════════════════════════════════════════════
    'aviso_institucion.csv': {
        'aviso_id':       "FK a `avisos.aviso_id`.",
        'id_institucion': "FK a `instituciones.id_institucion`.",
        'n_carreras_declaradas_aviso':
            "Copia de `avisos.n_carreras_declaradas`. **Es un proxy "
            "imperfecto para filtrar avisos genéricos por institución**: "
            "un aviso con 19 carreras declaró 35 instituciones y cuenta "
            "como específico. Hace falta volumen para calibrar un umbral "
            "propio de instituciones.",
    },

    # ══════════════════════════════════════════════════════════════
    'empresas.csv': {
        'empresa_id':     "`idCompany`. Clave de la tabla.",
        'empresa_id_alt': "`idEmpresa`, la clave alternativa de la API.",
        'nombre_canonico':
            "El nombre más frecuente entre los observados. **Cuando una "
            "empresa usa el nombre del cliente final** (una consultora "
            "de reclutamiento, p. ej.) este valor no significa gran "
            "cosa: hay un caso con 19 variantes. Leer "
            "`nombres_observados` cuando importe.",
        'nombres_observados':
            "JSON `{nombre: veces}` con **todos** los nombres vistos, no "
            "solo el ganador. Vacío `{}` en las empresas siempre "
            "confidenciales.",
        'n_avisos_acumulados': "Avisos distintos de esta empresa.",
        'primera_vez_visto':   "Primera fecha de scraping en que apareció.",
        'ultima_vez_visto':    "Última fecha de scraping en que apareció.",
        'areas_observadas':
            "Áreas del monitor donde apareció, separadas por ` | `.",
        'siempre_confidencial':
            "True si **todos** sus avisos fueron confidenciales. En "
            "agosto 2026 eran 167, y coinciden exactamente con las 167 "
            "sin ningún nombre registrado.",
        'n_avisos_confidenciales':
            "Cuántos de sus avisos fueron confidenciales. La diferencia "
            "con `n_avisos_acumulados` es lo que hace recuperable la "
            "identidad por cruce de `empresa_id`.",
    },

    # ══════════════════════════════════════════════════════════════
    'carreras_trabajando.csv': {
        'carrera_trabajando':
            "Nombre de carrera observado. **Es la clave, y es texto**: "
            "la API no expone ID de carrera. Lista controlada, no texto "
            "libre (solo 2 colisiones al normalizar sobre 528), pero "
            "tampoco una taxonomía: mezcla niveles y fusiona sinónimos.",
        'n_avisos_acum':
            "Avisos que declaran esta carrera, **incluidos los "
            "genéricos**. Sirve de poco para priorizar: los avisos de "
            "504 carreras suman en todas.",
        'n_avisos_especificos':
            "Avisos que la declaran **excluyendo genéricos** "
            "(`n_carreras_declaradas <= UMBRAL_AVISO_GENERICO`). **Es el "
            "orden correcto para priorizar la homologación.** En "
            "Humanidades, usar este en vez del acumulado subió la "
            "cobertura del top 50 de 11,7% a 83,3%.",
        'primera_vez_visto': "Primera fecha de scraping en que se declaró.",
        'ultima_vez_visto':  "Última fecha de scraping en que se declaró.",
        'areas_observadas':
            "Áreas donde se observó. Los nombres que aparecen en las 10 "
            "áreas son, casi siempre, los del catálogo de 504 que "
            "declaran los avisos genéricos.",
    },

    # ══════════════════════════════════════════════════════════════
    'instituciones.csv': {
        'id_institucion':
            "`idInstitucion`. A diferencia de las carreras, acá la API "
            "**sí** entrega un ID.",
        'id_institucion_sqlserver':
            "`idInstitucionSqlServer`, la segunda clave de la API.",
        'nombre_institucion': "`nombreInstitucion`.",
        'n_avisos_acum':      "Avisos que la declaran, con genéricos.",
        'n_avisos_especificos':
            "Avisos que la declaran excluyendo genéricos. **Usa el "
            "umbral de carreras como proxy y es imperfecto** — ver "
            "`aviso_institucion.n_carreras_declaradas_aviso`.",
        'primera_vez_visto': "Primera fecha de scraping en que apareció.",
        'ultima_vez_visto':  "Última fecha de scraping en que apareció.",
    },

    # ══════════════════════════════════════════════════════════════
    'homologacion_carreras.csv': {
        'carrera_trabajando':
            "Nombre observado, texto exacto. Primera mitad de la clave.",
        'nivel_condicion':
            "`*` (vale para cualquier nivel), `universitaria` o "
            "`tecnica`. Segunda mitad de la clave: permite resolver los "
            "casos 1:N duplicando la fila, usando `nivel_academico` del "
            "aviso como desempate.",
        'carrera_sies':
            "**Columna manual.** El nombre SIES que le corresponde. "
            "`homologar.py` solo la completa por match exacto "
            "normalizado; nunca pisa lo ya escrito.",
        'area_sies':     "**Columna manual.** Área SIES de esa carrera.",
        'tipo_relacion':
            "**Columna manual.** `exacta`, `agregacion`, `ambigua` o "
            "`sin_equivalencia`. Este último **es una decisión, no un "
            "hueco**: deja registrado que se miró y no hay equivalente.",
        'n_avisos_especificos':
            "Copia de `carreras_trabajando.n_avisos_especificos`. Ordena "
            "la cola: 50 filas cubren del 51% al 85% de las menciones.",
        'n_avisos_acum':    "Copia de `carreras_trabajando.n_avisos_acum`.",
        'areas_observadas': "Copia de `carreras_trabajando.areas_observadas`.",
        'sugerencia':
            "Nombre SIES más parecido por solapamiento de tokens. **No "
            "es una decisión y nunca se aplica sola.** A 'Ingeniería "
            "Civil' le sugiere 'Ingeniería Civil Industrial' con 0,67, "
            "que es exactamente la confusión a evitar.",
        'score':
            "Jaccard de tokens de la sugerencia, de 0 a 1. Ordena la "
            "pantalla; no mide si la sugerencia es correcta.",
        'revisado_por':
            "**Columna manual**, salvo `auto:match_exacto`, que pone el "
            "script cuando resolvió por coincidencia exacta normalizada.",
        'fecha_revision': "**Columna manual.**",
        'nota':           "**Columna manual.** Texto libre.",
    },

    # ══════════════════════════════════════════════════════════════
    # Crudo: el envoltorio que escribe scraper_v9.py
    # ══════════════════════════════════════════════════════════════
    '_crudo': {
        'aviso_id':       "`idOferta`. Clave del registro.",
        'fecha_scraping': "Fecha de la captura, ISO. Alimenta el panel.",
        'periodo':
            "`YYYY_MM` de la captura. Es lo que agrupa las corridas en "
            "`periodos_visto`.",
        'area_scraping':
            "Área del monitor bajo la que se corrió esta captura. Un "
            "mismo aviso reaparece con distintas áreas.",
        'terminos':
            "Términos de esta área que devolvieron este aviso.",
        'detalle_ok':     "Si `/api/ofertas/{id}` respondió bien.",
        'detalle_motivo': "Por qué falló, cuando falló.",
        'listado':
            "Respuesta de `/api/searchjob` para este aviso, íntegra. "
            "Es lo que queda si el detalle falla.",
        'detalle':
            "Respuesta de `/api/ofertas/{id}`, íntegra: 51 claves. **Se "
            "guarda completa a propósito** — cada inspección de la API "
            "reveló campos valiosos que se estaban descartando, y "
            "tenerla permite reprocesar sin volver a golpear el sitio.",
    },

    # ══════════════════════════════════════════════════════════════
    # Claves de `listado`: la respuesta del buscador, no del detalle.
    # Documentadas en agosto 2026 con `--evidencia` sobre los 17.744
    # registros. Varias NO son iguales a su homónima del detalle, y esas
    # diferencias son lo que importa.
    '_crudo.listado': {
        'idOferta':
            "Id del aviso, el mismo del envoltorio y del detalle.",
        'nombreCargo':
            "Título del aviso. `consolidar.py` prefiere el del detalle y "
            "usa este de respaldo cuando el detalle falla.",
        'urlLogo':
            "Mismo valor que en el detalle: logo de la empresa, con "
            "`logo_generico_azul.jpg` cuando el aviso es confidencial.",
        'nombreEmpresa':
            "Nombre de la empresa **ya enmascarado**: en los avisos "
            "confidenciales dice literalmente `Empresa Confidencial`. La "
            "identidad no está acá sino en `idCompany` del detalle.",
        'descripcionOferta':
            "**No es la descripción completa: es el fragmento de "
            "resultados de búsqueda.** Viene recortado con puntos "
            "suspensivos y con el término buscado resaltado en "
            "`<strong>`: «…estudiante de `<strong>`Administración de "
            "Empresas`</strong>` (Técnico o…». O sea que **muestra dónde "
            "matcheó la búsqueda**, que es exactamente lo que §5.8 tuvo "
            "que inferir. `consolidar.py` usa el del detalle, que sí "
            "está completo.",
        'publicadoHace':
            "Texto de pantalla, «Hace 4 días». **Relativo al momento de "
            "la consulta**, así que envejece mal en el crudo; 85 valores "
            "distintos. Para fechas, usar `fechaPublicacion`.",
        'ubicacion':
            "Texto `Comuna, Región` — «Huechuraba, Metropolitana de "
            "Santiago». 203 valores distintos. Es un string, no el dict "
            "del detalle; `consolidar.py` lo parte por la coma cuando el "
            "detalle no trae ubicación.",
        'ofertaDestacada':
            "Booleano. Alimenta `avisos.destacada`.",
        'geolocalizacion':
            "Coordenadas como string `lat,lon` — "
            "`'-23.617728,-70.3915701'`. **Este sí está en el orden que "
            "sugiere el nombre**, a diferencia de "
            "`detalle.ubicacion.coordenadas`, que dice `Point` y viene "
            "[lat, lon]. Vacío en el 12% de los registros.",
        'nombreJornada':
            "Jornada declarada. **10 valores distintos**, más de los que "
            "se ven en una muestra chica del detalle. Mezcla extensión "
            "horaria, modalidad y tipo de contrato — de acá salen "
            "`jornada`, `modalidad` y `tipo_contrato`.",
        'ofertaInclusiva':
            "Booleano. Alimenta `avisos.inclusiva`.",
        'ofertaExclusiva':
            "**Campo muerto**: un solo valor distinto en 17.744 "
            "registros, siempre `False`.",
        'fechaPublicacion':
            "Fecha y **hora** de publicación: `'2026-08-12 12:10'`. Es "
            "más preciso que el detalle, que trae solo la fecha "
            "(`'12/08/2026'`). **El pipeline descarta la hora**: "
            "`consolidar.py` usa `fechaPublicacionFormatoIngles` del "
            "detalle, que es `aaaa-mm-dd`. Si alguna vez interesa la "
            "hora de publicación, está en el crudo.",
    },

    # Claves del detalle. Solo las que están verificadas; el resto va a
    # aparecer como SIN DOCUMENTAR, que es la respuesta honesta.
    '_crudo.detalle': {
        'estadoOferta':
            "PUBLICADA o DESACTIVADA. **La búsqueda devuelve ambos.** Es "
            "lo que habilita medir duración de vacante, la variable más "
            "valiosa del monitor.",
        'ofertaConfidencial': "Booleano explícito.",
        'idCompany':
            "Clave de empresa; es la que aparece en `urlLogo`.",
        'idEmpresa':
            "Segunda clave de empresa. Biyectiva con `idCompany` en la "
            "muestra observada (n=40).",
        'nombreEmpresaFantasia':
            "Nombre de la empresa. En avisos confidenciales dice "
            "literalmente 'Empresa Confidencial', pero **el detalle no "
            "filtra el `idCompany`**: por ahí se recupera la identidad.",
        'carreras':
            "Lista de `{nombreCarrera}`. **No trae ID**: por eso la "
            "homologación se hace contra texto.",
        'instituciones':
            "Lista de `{idInstitucion, idInstitucionSqlServer, "
            "nombreInstitucion}`. Acá sí hay ID.",
        'habilidades':
            "Lista de `{nombreHabilidad, nombreNivel}`. El nivel viene "
            "casi siempre vacío.",
        'ubicacion':
            "Dict con región, comuna, dirección y coordenadas. **`"
            "coordenadas` dice `type: Point` pero el orden es "
            "[lat, lon]**, al revés de GeoJSON: alimentarlo sin invertir "
            "a una librería geoespacial pone los puntos en Somalia.",
        'aniosExperiencia':
            "Años de experiencia. Se contradice con "
            "`nombreOperadorExperiencia` en algunos avisos.",
        'nombreOperadorExperiencia':
            "'Sin experiencia', 'Más de'… Ver `aniosExperiencia`.",
        'candidadPostulaciones':
            "Typo de la API (no `cantidad`). Viene null de forma "
            "sistemática.",
        'candidadVisualizaciones': "Ídem.",
        'slug':          "Null en ~90% de los casos.",
        'nombreMoneda':  "Siempre 'Pesos Chilenos' en lo observado.",
        'nombreArea':
            "Área declarada por el empleador. 80% dice 'Otra Área'. "
            "**Describe al empleador, no al área del monitor.**",
        'mostrarSueldo': "Si el aviso publica el sueldo. 2,9% lo hace.",

        # ── documentadas en agosto 2026 con `diccionario.py --evidencia`
        # sobre los 17.744 registros del crudo. Cada una a partir de sus
        # valores reales, no del nombre.
        'idOferta':
            "Id del aviso, el mismo que `aviso_id`. Redundante con la "
            "clave del registro.",
        'nombreCargo':
            "Título del aviso, texto libre del empleador. Es lo que "
            "alimenta `avisos.titulo`.",
        'nombreTipoCargo':
            "Familia del cargo según el empleador: Administrativo, "
            "Comercial, Analista, Práctica, Estudiante, Otro "
            "Profesional. Vocabulario chico y controlado.",
        'descripcionOferta':
            "Cuerpo del aviso, **en HTML** (`<p>`, `<ul>`, entidades y "
            "emojis escapados). `consolidar.py` lo limpia. Es el campo "
            "sobre el que el buscador hace match por prefijo, así que "
            "es el origen del ruido de los términos (§5.8).",
        'cantidadVacantes':
            "Cuántas vacantes declara el aviso. Valores observados de 1 "
            "a 10.",
        'categorias':
            "Etiquetas propias del empleador: `{idOpcionCategoria, "
            "nombreOpcionCategoria, idCategoriaPadre}`. **Solo el 6% de "
            "los avisos la trae.** Los valores observados son "
            "mayormente nombres de empresa o marca (Salcobrand, "
            "INCHCAPE, Vital Jugos) y alguno genérico (Cargos "
            "Profesionales). Inferencia, no verificado: parece una "
            "taxonomía interna de cada cliente, no del sitio.",
        'nombreJornada':
            "Jornada declarada: Jornada Completa, Part Time, Por "
            "Turnos, En terreno, Mixta (Teletrabajo + Presencial), "
            "Práctica. **Mezcla tres dimensiones** y de acá salen "
            "`jornada`, `modalidad` y `tipo_contrato`.",
        'sueldo':
            "Monto en pesos. **Vale 0 cuando el aviso no publica "
            "sueldo**, que es el 97% de los casos; por eso "
            "`avisos.sueldo_liquido` solo lo copia si `mostrarSueldo` "
            "es verdadero y el monto es mayor que cero.",
        'nombreNivelAcademico':
            "Nivel exigido: Básica, Media, Técnico medio/ colegio "
            "técnico, Técnico profesional superior, Universitaria, "
            "Magíster. Es el desempate de los casos 1:N en la "
            "homologación.",
        'nombreSituacionAcademica':
            "Situación exigida: En curso, Próximo a graduarse, "
            "Egresado, Graduado, Indiferente.",
        'requisitosMinimos':
            "Requisitos, **en HTML**. Segundo campo donde el buscador "
            "hace match, después de la descripción.",
        'preguntas':
            "Preguntas de filtro que el postulante debe responder: "
            "`{idPregunta, orden, pregunta, tipoPregunta}`. **89% de "
            "los avisos las trae** — es de los campos mejor poblados "
            "que nadie está usando. Varias piden justo lo que al "
            "monitor le falta: «¿Cuál es su carrera, casa de "
            "estudios?», «Indícanos tus estudios».",
        'ofertaInclusiva':
            "Si el aviso se declara inclusivo. Booleano.",
        'fechaPublicacion':
            "Fecha de publicación en formato chileno `dd/mm/aaaa`. "
            "`consolidar.py` prefiere `fechaPublicacionFormatoIngles`, "
            "que no tiene ambigüedad de orden.",
        'fechaExpiracion':
            "Fecha de expiración en `dd/mm/aaaa`. Ver "
            "`fechaExpiracionFormatoIngles`.",
        'fechaPublicacionFormatoIngles':
            "Fecha de publicación en ISO `aaaa-mm-dd`. **Es la que usa "
            "el pipeline.**",
        'fechaExpiracionFormatoIngles':
            "Fecha de expiración en ISO. Ojo: es la vigencia "
            "declarada, no la baja real — las bajas ocurren mucho "
            "antes.",
        'urlLogo':
            "URL del logo. **Chivato limpio de confidencialidad**: si "
            "termina en `logo_generico_azul.jpg` el aviso es "
            "confidencial; si no, la ruta incluye el id de empresa "
            "(`/company/93562/logo.png`), que coincide con "
            "`idCompany`.",
        'finalizaEn':
            "Texto para mostrar en pantalla: «Finaliza en 56 días». "
            "**Derivado y relativo al momento de la consulta**, no un "
            "dato: se calcula contra `fechaExpiracion`. No usarlo para "
            "análisis; envejece mal en el crudo.",
        'publicadoHace':
            "Texto de pantalla: «Publicada hace 4 días por». Mismo "
            "problema que `finalizaEn` — relativo al momento de la "
            "consulta. Usar `fechaPublicacionFormatoIngles`.",
        'idiomas':
            "Idiomas exigidos con nivel por destreza: `{nombreIdioma, "
            "nombreEscrito, nombreHablado, nombreLectura}`, en escala "
            "bajo/medio/alto/nativo. **Solo el 12% de los avisos.** No "
            "se está extrayendo a ninguna maestra.",
        'indicadorAtractivo':
            "Widget de marketing del sitio: `{texto, color, icono}` con "
            "valores como «Postula ahora», «Popular», «Sé uno de los "
            "primeros». Describe cómo se muestra el aviso, no el "
            "trabajo. 15% de los avisos.",
        'evaluacionesInternasOnline':
            "**Campo muerto**: 0% de relleno en los 17.744 registros. "
            "Siempre `None` o lista vacía.",
        'evaluaciones':
            "Pruebas de selección asociadas al aviso. **2% de los "
            "avisos**, y en lo observado todas del proveedor `hirint`.",
        'linkPostulacionExterno':
            "URL de postulación en un ATS externo (airavirtual.com en "
            "lo observado, a veces con subdominio del empleador). **8% "
            "de los avisos**: son los que no se postulan por "
            "trabajando.cl.",
        'tipoCurriculumAceptado':
            "`NORMAL` o `ARCHIVO`: si acepta el CV de la plataforma o "
            "un archivo subido.",
        'usaScoreScreening':
            "Si el aviso usa el puntaje automático de filtrado. "
            "Booleano.",
        'esBuscable':
            "Si el aviso aparece en búsquedas. **True en el 100% de lo "
            "observado**, lo que es esperable: todos estos avisos "
            "llegaron justamente por la búsqueda. No dice nada sobre "
            "los avisos que el monitor no ve.",

        # Campos muertos: vacíos en los 40 avisos de la sonda.
        'tiempoContrato':
            "**Campo muerto**: vacío en los 40 avisos de la sonda.",
        'documentosRequeridos':        "**Campo muerto** (sonda n=40).",
        'archivosAdjuntos':            "**Campo muerto** (sonda n=40).",
        'tieneEntrevistaIa':           "**Campo muerto** (sonda n=40).",
        'postulacionValidaInstitucion': "**Campo muerto** (sonda n=40).",
        'exclusiva':                   "**Campo muerto** (sonda n=40).",
    },
}
