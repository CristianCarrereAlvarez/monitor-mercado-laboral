# Diccionario de variables — Monitor Mercado Laboral

**Generado por `diccionario.py`. No editar a mano.**  
Las descripciones se escriben en `glosario.py`; el resto sale de los datos y de los esquemas de `consolidar.py` y `homologar.py`.

Fuente: `/tmp/claude-0/-home-user-monitor-mercado-laboral/e85ed1ac-ab18-53a7-9525-f475ddb808d9/scratchpad/dat/monitor_mercado_laboral/maestras`  
Crudo: 1 archivo, 7 registros (muestreado)

## Estado

- columnas en las maestras: **102**
- sin documentar: **1**
- glosas huérfanas: **18**
- declaradas y ausentes en el CSV: **0**
- columnas manuales detectadas: **0**
- tablas del esquema que no están en la carpeta: `homologacion_carreras.csv`

## Cómo leer esto

| origen | qué significa |
|---|---|
| `código` | la escribe `consolidar.py`/`homologar.py` |
| `manual` | la agregó una persona; se preserva entre corridas |
| `⚠ inesperada` | está en el CSV, no en el esquema, y la tabla no preserva manuales |
| `⚠ ausente` | está en el esquema y no en el CSV |

`relleno` es el porcentaje de filas con valor no vacío. Un relleno de 0% en una columna del código es un campo muerto de la API, no un bug del pipeline.


---

## Maestras

### `avisos.csv`

**Grano:** 1 fila por aviso · **Clave:** `aviso_id` · **6 filas** · 63 columnas

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `aviso_id` | código | 100% | Identificador del aviso en trabajando.cl (`idOferta`). **Estable entre corridas**: es lo que permite el panel longitudinal y lo que deduplica un mismo aviso encontrado en varias áreas. |
| `url` | código | 100% | URL pública. Se arma con `slug` cuando la API lo trae (~10% de los casos) y con `aviso_id` cuando no. |
| `primera_vez_visto` | código | 100% | Primera `fecha_scraping` en que el aviso apareció en algún crudo. |
| `ultima_vez_visto` | código | 100% | Última `fecha_scraping` en que apareció. |
| `n_corridas_visto` | código | 100% | **Cuenta observaciones, no corridas.** Incrementa una vez por registro de crudo, y un mismo aviso aparece en varias áreas de la misma corrida: en agosto 2026, 5.910 avisos tenían >1 con una sola corrida mensual hecha. Para contar corridas reales, usar `periodos_visto`. |
| `periodos_visto` | código | 100% | Períodos `YYYY_MM` en que se vio el aviso, separados por ` | `. **Es la columna longitudinal correcta.** |
| `estado_primero` | código | 100% | `estadoOferta` en la primera observación: PUBLICADA o DESACTIVADA. |
| `estado_ultimo` | código | 100% | `estadoOferta` en la última observación. La búsqueda devuelve avisos ya cerrados, así que DESACTIVADA aparece desde el primer avistamiento. |
| `fecha_desactivacion_detectada` | código | 0% | Primera fecha de scraping en que se vio DESACTIVADA. **No es la fecha real de baja**: está acotada por el intervalo entre corridas. |
| `dias_publicado_hasta_baja` | código | 0% | Días entre `fecha_publicacion` y `fecha_desactivacion_detectada`. **Sin leer `calidad_duracion` este número no significa nada.** |
| `calidad_duracion` | código | 100% | Tres valores que NO se deben mezclar: `observada` (se vio PUBLICADA y después DESACTIVADA — única medición real), `cota_superior` (ya estaba de baja al primer avistamiento; es un techo) y `censurada` (seguía viva). Promediarlos juntos sesga la mediana hacia arriba. |
| `censurado` | código | 100% | True si nunca se detectó la desactivación. Equivale a `calidad_duracion == 'censurada'`. |
| `titulo` | código | 100% | `nombreCargo` del detalle. |
| `descripcion` | código | 0% | `descripcionOferta`, con el HTML removido. |
| `requisitos` | código | 0% | `requisitosMinimos`, con el HTML removido. |
| `hash_contenido` | código | 100% | SHA-1 (16 hex) de `empresa_id` + título normalizado + los primeros 2.000 caracteres de la descripción normalizada. Permite detectar avisos de contenido equivalente con distinto `aviso_id` (republicaciones). Ningún análisis lo usa todavía. |
| `empresa_id` | código | 100% | `idCompany` del detalle. Es la clave de empresa y la que aparece en `urlLogo`. Sirve para acumular información sobre empresas; **no para desanonimizar avisos confidenciales en una publicación**. |
| `empresa_id_alt` | código | 0% | `idEmpresa`, la segunda clave que expone la API. Biyectiva con `empresa_id` en la muestra observada (n=40). |
| `empresa_nombre` | código | 100% | `nombreEmpresaFantasia`, o el nombre del listado. **Vacío a propósito cuando el aviso es confidencial**, aunque la API sí lo devuelva. |
| `empresa_confidencial` | código | 100% | `ofertaConfidencial` del detalle. Si no hubo detalle, se infiere de que el nombre sea literalmente 'Empresa Confidencial'. |
| `fecha_publicacion` | código | 0% | Fecha de publicación declarada por la API, en ISO. Viene exacta en cada aviso, así que no se pierde aunque el monitor empiece a observar tarde. |
| `fecha_expiracion` | código | 0% | Fecha de expiración declarada, en ISO. |
| `vigencia_declarada_dias` | código | 0% | Días entre publicación y expiración declarada. **No es duración de vacante**: las bajas ocurren mucho antes del vencimiento (mediana declarada: 59 días). |
| `tipo_cargo` | código | 0% | `nombreTipoCargo` del detalle. |
| `area_funcional` | código | 0% | `nombreArea` de la API. **Describe al empleador, no el área del monitor**: el 80% dice 'Otra Área' y en Derecho el segundo valor más frecuente fue 'Estimulación temprana' (Fundación Integra). No confundir con `areas_scraping`. |
| `vacantes` | código | 0% | `cantidadVacantes`. |
| `region` | código | 0% | `ubicacion.nombreRegion` del detalle; si falta, la segunda parte del texto de ubicación del listado partido por comas. |
| `comuna` | código | 0% | `ubicacion.nombreComuna`; si falta, la primera parte del texto de ubicación del listado. |
| `direccion` | código | 0% | `ubicacion.direccion`. |
| `codigo_postal` | código | 0% | `ubicacion.codigoPostal`. |
| `latitud` | código | 0% | Latitud, **ya en el orden correcto**. En el crudo, `ubicacion.coordenadas` dice `type: Point` pero trae [lat, lon], al revés de GeoJSON; `consolidar.py` lo desarma bien. Verificado con Antofagasta. |
| `longitud` | código | 0% | Longitud, ya en el orden correcto. Ver `latitud`. |
| `jornada` | código | 0% | `nombreJornada` tal cual viene. **Mezcla tres dimensiones**: extensión horaria (Completa, Part Time), modalidad (Teletrabajo, Mixta) y tipo de contrato (Práctica, Reemplazo, Free Lance). Por eso hay dos columnas derivadas. |
| `modalidad` | código | 0% | Derivada de `jornada`. Solo dice Híbrido, Remoto o Presencial cuando la jornada lo informa; el resto es **'No informado', nunca 'Presencial' por defecto**. v7 mapeaba 'Jornada Completa' a Presencial y eso inventaba el dato para el 69% de los avisos. |
| `tipo_contrato` | código | 0% | Derivada de `jornada`: Práctica, Reemplazo, Freelance o Comisionista. Vacía cuando la jornada no menciona ninguna. |
| `sueldo_liquido` | código | 0% | `sueldo`, y solo si `mostrarSueldo` es verdadero y el monto es mayor que cero. Vacío en la enorme mayoría de los avisos (2,9% los muestra). |
| `muestra_sueldo` | código | 0% | `mostrarSueldo` del detalle. |
| `moneda` | código | 0% | `nombreMoneda`. Siempre 'Pesos Chilenos' en lo observado. |
| `exp_operador` | código | 0% | `nombreOperadorExperiencia` (p. ej. 'Sin experiencia', 'Más de'). Antes iba concatenado con los años en un string infiltrable; ahora son tres columnas. |
| `exp_anios` | código | 0% | `aniosExperiencia`, como número. |
| `exp_inconsistente` | código | 0% | True cuando la API se contradice: operador 'Sin experiencia' con `exp_anios` mayor que cero. **Marcar la contradicción en el dato en vez de resolverla a ciegas.** |
| `nivel_academico` | código | 0% | `nombreNivelAcademico` (Universitaria, Técnico profesional superior…). Es el desempate disponible para los casos 1:N de la homologación, donde SIES separa 'Ingeniería en' de 'Técnico en' y trabajando no. |
| `situacion_academica` | código | 0% | `nombreSituacionAcademica` (titulado, egresado, cursando…). |
| `n_carreras_declaradas` | código | 100% | Cuántas carreras declara el aviso. **Se guarda el entero, no un flag**: el umbral de genericidad se decide en análisis (`UMBRAL_AVISO_GENERICO`, hoy 30). Diez avisos de un mismo empleador declaran 504 carreras y aparecen en cualquier búsqueda. |
| `hash_carreras` | código | 83% | Hash (16 hex) del **conjunto** de carreras declaradas, normalizado y ordenado: dos avisos con las mismas carreras en distinto orden comparten hash. **Vacío cuando el aviso no declara ninguna** — no declarar nada no es compartir un conjunto, y meterlos todos bajo un mismo hash inventaría el grupo más grande de la tabla. |
| `n_avisos_mismo_conjunto` | código | 83% | Cuántos avisos distintos declaran exactamente ese conjunto. **Identifica los perfiles guardados sin depender del umbral**: un empleador que adjunta la misma lista a todos sus avisos no está decidiendo por vacante. Bresler sale con 10, AMERICAR con 4, y un concurso multidisciplinario legítimo (Universidad Mayor) sale con 1 porque cada convocatoria trae su propia lista. Hizo falta porque el tamaño del conjunto **no** separa esos dos casos: hay plantillas de 20 carreras y concursos legítimos de 25. Se cuenta sobre avisos deduplicados, no sobre observaciones. Vacío si `hash_carreras` lo está. |
| `n_habilidades` | código | 100% | Cuántas habilidades declara el aviso. |
| `n_instituciones` | código | 100% | Cuántas instituciones declara el aviso. |
| `postulaciones` | código | 0% | `candidadPostulaciones` — el typo es de la API, no del monitor. Viene null de forma sistemática. |
| `visualizaciones` | código | 0% | `candidadVisualizaciones`. Mismo typo, mismo problema: llega null casi siempre. |
| `destacada` | código | 0% | `ofertaDestacada` del listado. |
| `inclusiva` | código | 0% | `ofertaInclusiva` del listado. |
| `tipo_curriculum` | código | 0% | `tipoCurriculumAceptado` del detalle. |
| `usa_score_screening` | código | 0% | `usaScoreScreening` del detalle. |
| `areas_scraping` | código | 100% | Áreas del monitor bajo las que se capturó el aviso, separadas por ` | `. Un aviso apareció en 1,9 áreas en promedio (agosto 2026). **Es trazabilidad de captura, no clasificación del aviso.** |
| `terminos_busqueda` | código | 100% | Términos de búsqueda que trajeron este aviso, separados por ` | `. **No es atribución de carrera**: el buscador matchea por prefijo sobre el cuerpo del aviso, así que dos avisos entraron por 'Derecho' vía la frase 'la mano derecha del gerente'. |
| `n_terminos_busqueda` | código | 100% | Cuántos términos distintos trajeron el aviso. |
| `sies_por_termino` | código | 100% | Carreras SIES a las que corresponden los términos que encontraron el aviso. **Sobre-atribuye por diseño**: es señal de contexto, no clasificación. En Derecho los 342 avisos quedan con 'Derecho', incluidos 120 de salas cuna. |
| `n_sies_por_termino` | código | 100% | Cuántas carreras SIES distintas salen por esa vía. |
| `areas_sies_por_termino` | código | 100% | Áreas SIES de esos términos. Más principiada que `area_funcional`, que describe al empleador. |
| `n_terminos_sin_mapeo` | código | 100% | Términos del crudo que ya no existen en el catálogo SIES. **Detector de deriva**: si el catálogo se edita después de una corrida, este número deja de ser 0. |
| `detalle_ok` | código | 100% | True si la llamada a `/api/ofertas/{id}` respondió bien. Cuando es False, las columnas que salen del detalle vienen vacías y solo hay datos del listado. |
| `detalle_motivo` | código | 0% | Por qué falló el detalle, cuando falló. |

### `aviso_carrera.csv`

**Grano:** 1 fila por (aviso × carrera declarada) · **Clave:** `aviso_id + carrera_trabajando` · **14 filas** · 5 columnas

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `aviso_id` | código | 100% | FK a `avisos.aviso_id`. |
| `carrera_trabajando` | código | 93% | Nombre de carrera **tal como lo declara el aviso**. La API no trae ID de carrera, solo el texto. Vacío en las filas `keyword_only`. |
| `termino_busqueda` | código | 7% | Término que encontró el aviso. Solo se llena en las filas `keyword_only`; en las `declarada` va vacío. |
| `fuente` | código | 100% | `declarada` = el aviso declara esa carrera (**única evidencia válida de atribución**). `keyword_only` = solo quedó registro del término que lo encontró. **Para cualquier análisis por carrera hay que filtrar `fuente == 'declarada'`.** Cuesta caro —el 40,6% de los avisos no declara carreras— y es el precio de no inventar atribución. Las filas `keyword_only` están superseded por `aviso_termino.csv` y conviene retirarlas. |
| `n_carreras_declaradas_aviso` | código | 100% | Copia de `avisos.n_carreras_declaradas`, para poder filtrar genéricos sin hacer join. |

### `aviso_termino.csv`

**Grano:** 1 fila por (aviso × término de búsqueda) · **Clave:** `aviso_id + termino_busqueda` · **6 filas** · 5 columnas

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `aviso_id` | código | 100% | FK a `avisos.aviso_id`. |
| `termino_busqueda` | código | 100% | Término del catálogo SIES con el que se buscó. |
| `carrera_sies` | código | 100% | Carrera SIES del término. Solo 16 de los 199 pares traducen algo distinto a la identidad; el valor real de la tabla está en esos 16 y en el área. |
| `areas_sies` | código | 100% | Áreas SIES del término, separadas por ` | `. |
| `mapeado` | código | 100% | Si el término se encontró en el catálogo. False señala deriva entre el crudo y el catálogo actual. |

### `aviso_habilidad.csv`

**Grano:** 1 fila por (aviso × habilidad) · **Clave:** `aviso_id + habilidad` · **0 filas** · 3 columnas

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `aviso_id` | código | — | FK a `avisos.aviso_id`. |
| `habilidad` | código | — | `nombreHabilidad` del detalle. |
| `nivel` | código | — | `nombreNivel`. Casi siempre vacío: la API lo expone pero los empleadores no lo cargan. |

### `aviso_institucion.csv`

**Grano:** 1 fila por (aviso × institución) · **Clave:** `aviso_id + id_institucion` · **0 filas** · 3 columnas

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `aviso_id` | código | — | FK a `avisos.aviso_id`. |
| `id_institucion` | código | — | FK a `instituciones.id_institucion`. |
| `n_carreras_declaradas_aviso` | código | — | Copia de `avisos.n_carreras_declaradas`. **Es un proxy imperfecto para filtrar avisos genéricos por institución**: un aviso con 19 carreras declaró 35 instituciones y cuenta como específico. Hace falta volumen para calibrar un umbral propio de instituciones. |

### `empresas.csv`

**Grano:** 1 fila por empresa · **Clave:** `empresa_id` · **3 filas** · 10 columnas

> Preserva columnas manuales: cualquier columna fuera del esquema se arrastra por clave entre corridas, y las filas que dejan de aparecer en el crudo no se borran.

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `empresa_id` | código | 100% | `idCompany`. Clave de la tabla. |
| `empresa_id_alt` | código | 0% | `idEmpresa`, la clave alternativa de la API. |
| `nombre_canonico` | código | 100% | El nombre más frecuente entre los observados. **Cuando una empresa usa el nombre del cliente final** (una consultora de reclutamiento, p. ej.) este valor no significa gran cosa: hay un caso con 19 variantes. Leer `nombres_observados` cuando importe. |
| `nombres_observados` | código | 100% | JSON `{nombre: veces}` con **todos** los nombres vistos, no solo el ganador. Vacío `{}` en las empresas siempre confidenciales. |
| `n_avisos_acumulados` | código | 100% | Avisos distintos de esta empresa. |
| `primera_vez_visto` | código | 100% | Primera fecha de scraping en que apareció. |
| `ultima_vez_visto` | código | 100% | Última fecha de scraping en que apareció. |
| `areas_observadas` | código | 100% | Áreas del monitor donde apareció, separadas por ` | `. |
| `siempre_confidencial` | código | 100% | True si **todos** sus avisos fueron confidenciales. En agosto 2026 eran 167, y coinciden exactamente con las 167 sin ningún nombre registrado. |
| `n_avisos_confidenciales` | código | 100% | Cuántos de sus avisos fueron confidenciales. La diferencia con `n_avisos_acumulados` es lo que hace recuperable la identidad por cruce de `empresa_id`. |

### `carreras_trabajando.csv`

**Grano:** 1 fila por nombre de carrera observado · **Clave:** `carrera_trabajando` · **5 filas** · 6 columnas

> Preserva columnas manuales: cualquier columna fuera del esquema se arrastra por clave entre corridas, y las filas que dejan de aparecer en el crudo no se borran.

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `carrera_trabajando` | código | 100% | Nombre de carrera observado. **Es la clave, y es texto**: la API no expone ID de carrera. Lista controlada, no texto libre (solo 2 colisiones al normalizar sobre 528), pero tampoco una taxonomía: mezcla niveles y fusiona sinónimos. |
| `n_avisos_acum` | código | 100% | Avisos que declaran esta carrera, **incluidos los genéricos**. Sirve de poco para priorizar: los avisos de 504 carreras suman en todas. |
| `n_avisos_especificos` | código | 100% | Avisos que la declaran **excluyendo genéricos** (`n_carreras_declaradas <= UMBRAL_AVISO_GENERICO`). **Es el orden correcto para priorizar la homologación.** En Humanidades, usar este en vez del acumulado subió la cobertura del top 50 de 11,7% a 83,3%. |
| `primera_vez_visto` | código | 100% | Primera fecha de scraping en que se declaró. |
| `ultima_vez_visto` | código | 100% | Última fecha de scraping en que se declaró. |
| `areas_observadas` | código | 100% | Áreas donde se observó. Los nombres que aparecen en las 10 áreas son, casi siempre, los del catálogo de 504 que declaran los avisos genéricos. |

### `instituciones.csv`

**Grano:** 1 fila por institución · **Clave:** `id_institucion` · **0 filas** · 7 columnas

> Preserva columnas manuales: cualquier columna fuera del esquema se arrastra por clave entre corridas, y las filas que dejan de aparecer en el crudo no se borran.

| columna | origen | relleno | descripción |
|---|---|---:|---|
| `id_institucion` | código | — | `idInstitucion`. A diferencia de las carreras, acá la API **sí** entrega un ID. |
| `id_institucion_sqlserver` | código | — | `idInstitucionSqlServer`, la segunda clave de la API. |
| `nombre_institucion` | código | — | `nombreInstitucion`. |
| `n_avisos_acum` | código | — | Avisos que la declaran, con genéricos. |
| `n_avisos_especificos` | código | — | Avisos que la declaran excluyendo genéricos. **Usa el umbral de carreras como proxy y es imperfecto** — ver `aviso_institucion.n_carreras_declaradas_aviso`. |
| `primera_vez_visto` | código | — | Primera fecha de scraping en que apareció. |
| `ultima_vez_visto` | código | — | Última fecha de scraping en que apareció. |

---

## Crudo (`crudo_*.jsonl`)

> Leído con `--muestra 100`: **el relleno es aproximado**. Sin la opción, es exacto.

Una línea por (aviso × corrida × área). Append-only: el JSON se guarda íntegro para poder reprocesar sin volver a golpear el sitio.


### Envoltorio del registro

9 claves observadas.

| clave | relleno | descripción |
|---|---:|---|
| `aviso_id` | 100% | `idOferta`. Clave del registro. |
| `fecha_scraping` | 100% | Fecha de la captura, ISO. Alimenta el panel. |
| `periodo` | 100% | `YYYY_MM` de la captura. Es lo que agrupa las corridas en `periodos_visto`. |
| `area_scraping` | 100% | Área del monitor bajo la que se corrió esta captura. Un mismo aviso reaparece con distintas áreas. |
| `terminos` | 100% | Términos de esta área que devolvieron este aviso. |
| `detalle_ok` | 100% | Si `/api/ofertas/{id}` respondió bien. |
| `detalle_motivo` | 0% | Por qué falló, cuando falló. |
| `listado` | 100% | Respuesta de `/api/searchjob` para este aviso, íntegra. Es lo que queda si el detalle falla. |
| `detalle` | 100% | Respuesta de `/api/ofertas/{id}`, íntegra: 51 claves. **Se guarda completa a propósito** — cada inspección de la API reveló campos valiosos que se estaban descartando, y tenerla permite reprocesar sin volver a golpear el sitio. |

### Claves de `detalle`

6 claves observadas.

| clave | relleno | descripción |
|---|---:|---|
| `estadoOferta` | 100% | PUBLICADA o DESACTIVADA. **La búsqueda devuelve ambos.** Es lo que habilita medir duración de vacante, la variable más valiosa del monitor. |
| `ofertaConfidencial` | 100% | Booleano explícito. |
| `idCompany` | 100% | Clave de empresa; es la que aparece en `urlLogo`. |
| `nombreEmpresaFantasia` | 100% | Nombre de la empresa. En avisos confidenciales dice literalmente 'Empresa Confidencial', pero **el detalle no filtra el `idCompany`**: por ahí se recupera la identidad. |
| `nombreCargo` | 100% | **SIN DOCUMENTAR** |
| `carreras` | 86% | Lista de `{nombreCarrera}`. **No trae ID**: por eso la homologación se hace contra texto. |

⚠ Glosas huérfanas: `idEmpresa`, `instituciones`, `habilidades`, `ubicacion`, `aniosExperiencia`, `nombreOperadorExperiencia`, `candidadPostulaciones`, `candidadVisualizaciones`, `slug`, `nombreMoneda`, `nombreArea`, `mostrarSueldo`, `tiempoContrato`, `documentosRequeridos`, `archivosAdjuntos`, `tieneEntrevistaIa`, `postulacionValidaInstitucion`, `exclusiva`


---

## Pendientes de documentar

Escribir la glosa en `glosario.py` y volver a generar. **Si no sabés qué es una columna, dejala acá**: un hueco visible es información; una glosa inventada, no.


**_crudo.detalle**
- `nombreCargo`
