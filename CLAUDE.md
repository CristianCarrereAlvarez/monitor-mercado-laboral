# CLAUDE.md — Monitor Mercado Laboral Chile

Contexto completo del proyecto para continuar el trabajo. Escrito en
agosto 2026 al cerrar la sesión de rediseño v7 → v9.

**Regla de trabajo del autor: cero tolerancia a información inventada.**
Distinguir siempre entre (a) hecho verificado, (b) inferencia razonada,
(c) especulación. Si no se sabe algo, decirlo. No rellenar huecos con
algo plausible. Este documento marca explícitamente qué está verificado
y qué no; mantener esa disciplina.

---

## 1. Qué es esto

Monitor longitudinal del mercado laboral chileno construido sobre
avisos de empleo de **trabajando.cl**, cruzado con la taxonomía de
carreras **SIES** (Oferta Académica 2026, Chile).

**El objetivo NO es contar demanda actual.** El autor lo dijo
explícitamente. Interesa el comportamiento acumulado y longitudinal:
qué carreras pide el mercado, con qué requisitos, en qué regiones, y
cuánto dura una vacante publicada. También construir una base de
empresas enriquecible en el tiempo (tamaño, rubro, etc.).

**Postura ética acordada:** interesa información agregada, nunca
"la empresa X publicó el aviso Y". `empresa_id` se usa como clave para
acumular datos sobre empresas, no para desanonimizar avisos
confidenciales en una publicación. Ver §6.

---

## 2. Arquitectura

Tres etapas separadas a propósito:

```
scraper_v9.py   →  crudo/crudo_{area}_{YYYY_MM}.jsonl   (JSON íntegro, append-only)
consolidar.py   →  maestras/*.csv                        (upsert acumulado)
[análisis]      →  sobre las maestras
```

**Por qué separadas.** El detalle de la API tiene 51 claves; v7 usaba
~20. Cada inspección de la respuesta reveló campos valiosos que no se
habían guardado (`estadoOferta`, `instituciones`, `idEmpresa`,
`habilidades`). Guardando el JSON completo, cualquier decisión posterior
—homologación, nuevas variables, corrección de un parseo— se reprocesa
desde disco **sin volver a golpear el sitio**. Esta propiedad se usó
cuatro veces en un solo día durante el desarrollo.

**Corolario operativo:** si hace falta cambiar cómo se deriva un campo,
se cambia `consolidar.py` y se reconsolida. Nunca se re-scrapea por eso.

### Estado de los archivos

**GitHub es el repositorio fundamental.** Todo el código vive ahí y
Colab trabaja clonando desde ahí. Lo único que no se versiona son los
datos: `crudo/` y `maestras/` viven en Drive y están en `.gitignore`.

Lo que hay en el repo, y nada más:

| archivo | estado |
|---|---|
| `SMLab.ipynb` | **punto de entrada**; el notebook de Colab que orquesta todo |
| `mensual.sh` | corrida mensual completa: las 10 áreas en orden + consolidación |
| `capturar.sh` | envoltorio de captura; resuelve la carpeta de datos y hace imposible el error de directorio |
| `scraper_v9.py` | vigente — captura |
| `consolidar.py` | vigente — derivación |
| `homologar.py` | genera la cola editable de homologación |
| `carreras_sies_2026.py` | vigente — catálogo + índices; lo usan v9 y consolidar |
| `CLAUDE.md` | este documento |
| `.gitignore` | excluye bytecode, checkpoints de Colab, `crudo/` y `maestras/` |

Borrados del repo (agosto 2026), por si aparecen mencionados en notas
viejas: `scraper_v7.py`, `scraper_v8.py`, `sonda_detalle.py`,
`sonda_confidencial.py`. **No se conservaron.** Los hallazgos que
produjeron están en §5; el código no volvió a hacer falta.

---

## 3. Entorno

**Dos máquinas, no una.** Hasta agosto 2026 todo corría en Colab. Ya no:
Akamai bloquea los rangos de datacenter y desde Colab `trabajando.cl`
devuelve **403 en todo, incluida la portada**. Verificado con un
experimento limpio — mismo sitio, mismo minuto, la portada carga desde
una conexión doméstica y da 403 desde Colab.

| etapa | dónde corre | por qué |
|---|---|---|
| **captura** | **solo una máquina con IP residencial** | Colab está bloqueado |
| consolidación | esa misma máquina, o Colab | no toca la red |
| análisis | Colab | trae pandas instalado |

Conviene **consolidar en la misma máquina donde se captura**: los
archivos ya están ahí y no hay que esperar a que Drive termine de subir
el crudo. Las maestras viajan igual por Drive, así que el notebook las
encuentra.

El código sigue en GitHub y los datos en Google Drive; lo que cambió es
quién ejecuta qué.

### En la máquina de captura

```bash
cd ~/monitor-mercado-laboral && git pull
./mensual.sh                  # las 10 áreas + consolidación
./capturar.sh "Agropecuaria"  # una sola área
```

Los envoltorios resuelven la carpeta de datos y el modo de sesión solos.
Ver §4 para el detalle.

### En Colab

El notebook `SMLab.ipynb` está **en el repo**, no suelto en Drive: se
abre desde GitHub (hay un badge de Colab en la primera celda) y se
versiona como cualquier otro archivo. Desde que la captura se fue del
notebook, quedó organizado como herramienta de análisis: preparación,
un puntero a los comandos de captura, consolidación opcional, y seis
bloques de verificación sobre las maestras. Se guarda **con las salidas
limpias**: sin outputs no hay fuga de datos ni diffs enormes.

Rutas en Colab: código en `/content/repo` (clon efímero, se re-clona en
cada sesión) y datos en `/content/drive/MyDrive/monitor_mercado_laboral`
(persistente, con `crudo/` y `maestras/`). Separados a propósito, así
`git pull` nunca choca con archivos generados.

**Trampa conocida:** si hay archivos sin trackear en `/content/repo`
que después se suben a GitHub, el `git pull` aborta con *"untracked
working tree file would be overwritten"*. Solución: borrar el archivo
local antes del pull, o re-clonar limpio.

**Trampa peor, porque es silenciosa: el directorio de trabajo.**
`scraper_v9.py` tiene `DIR_CRUDO = "crudo"`, relativo al cwd. Corrido
desde `/content/repo` —que es lo natural después de un `os.chdir` para
clonar— el crudo aterriza en el clon efímero: se pierde al reiniciar la
sesión, `.gitignore` lo oculta de `git status` y **nada avisa**. El
síntoma aparece después: se consolida y el área recién corrida no está,
porque `consolidar.py` leyó el `crudo/` de Drive.

Por eso la celda de consolidación del notebook empieza con
`%cd $DATOS`, y por eso las de captura ya no existen ahí.

**Y por eso existe `capturar.sh`.** Documentar la trampa no alcanzó: se
repitió igual, en Colab en silencio y después en la terminal por copiar
una ruta de ejemplo. El envoltorio elimina la clase entera de error:

```bash
./capturar.sh "Agropecuaria"
```

**Trampa de macOS:** el Python de python.org no usa el llavero del
sistema, así que la primera corrida falla con
`CERTIFICATE_VERIFY_FAILED` aunque `curl` funcione. Se arregla una vez
con `/Applications/Python\ 3.x/Install\ Certificates.command`. El
scraper lo detecta y lo dice.

Resuelve la carpeta de datos sola —Drive de escritorio en macOS con «Mi
unidad» o «My Drive», Drive clásico, o `/content/drive` en Colab—, aborta
con un mensaje claro si no la encuentra o si hay más de una candidata, y
recién entonces hace `cd` y lanza el scraper. Para forzar la ruta:
`MML_DATOS=... ./capturar.sh "Salud"`.

También detecta si Playwright tiene Chromium instalado y, si no, agrega
`--sin-navegador` solo. En un Mac con macOS 12 eso es lo que hace que
funcione sin pensarlo.

### La rutina mensual

```bash
./mensual.sh                  # las 10 áreas + consolidar
./mensual.sh --desde "Salud"  # retomar sin repetir lo hecho
./mensual.sh --solo-captura   # sin consolidar
```

Corre las áreas de menor a mayor, envuelve cada una en `caffeinate` para
que el Mac no se suspenda, y deja un log por corrida en `<datos>/logs/`
más un resumen de qué se capturó y qué no.

**Corta todo ante un fallo de código 2** —rechazo del sitio o problema
local— porque las demás áreas van a fallar igual y, si es bloqueo por IP,
insistir lo empeora. Imprime el comando `--desde` para retomar. Un corte
a mitad de captura (código 3) se reintenta una vez y sigue.

Tecnología son 81 términos y tarda; conviene lanzarlo y dejarlo.

---

## 4. La API de trabajando.cl

Sin autenticación. Se usa Playwright/Chromium headless solo para
establecer cookies de sesión; después todo son llamadas HTTP vía
`ctx.request`.

```
GET /api/searchjob?palabraClave={}&pagina={}&orden=RANKING&tipoOrden=DESC
GET /api/ofertas/{idOferta}
```

`/api/empresas` **no existe** (404). Verificado en v7.

### El navegador es opcional (y el bloqueo de Akamai)

Playwright se usaba solo para establecer cookies; las llamadas siempre
fueron HTTP. **Medido en agosto 2026: la API responde 200 a un `curl`
pelado desde una IP residencial, sin cookies de ningún tipo.** El
navegador nunca fue necesario para el contenido.

Por eso `scraper_v9.py` tiene dos modos:

```
python scraper_v9.py "Salud"                  # navegador, si está
python scraper_v9.py "Salud" --sin-navegador  # urllib, sin dependencias
```

Si Playwright falta o falla al lanzar, cae solo al modo directo y lo
avisa. **Chromium no corre en macOS 12** — Playwright 1.62 responde
`does not support chromium on mac12` — así que en un Mac Monterey el
modo directo no es una comodidad, es el único camino.

**El bloqueo.** Desde Colab, todo el sitio devuelve 403 con la página de
denegación de Akamai (`errors.edgesuite.net`, "Access Denied", con
Reference #). No hay `retry-after` ni desafío: es una denegación seca por
reputación de IP. No se arregla con headers, ni con cookies, ni bajando
`CONCURRENCIA`, ni esperando — nada de eso cambia la IP de origen, que es
lo único que Akamai mira.

Corolario operativo: la captura se corre desde una red doméstica, con las
pausas puestas. Montar proxies o falsear huellas para saltar la regla es
otra cosa y no se hace.

### Campos del detalle (51 claves) — lo relevante

| campo | nota |
|---|---|
| `estadoOferta` | `PUBLICADA` / `DESACTIVADA`. **La búsqueda devuelve ambos.** |
| `ofertaConfidencial` | bool explícito |
| `idCompany` | clave de empresa; es la que aparece en `urlLogo` |
| `idEmpresa` | segunda clave; biyectiva con `idCompany` en la muestra (n=40) |
| `nombreEmpresaFantasia` | en avisos confidenciales dice literal `"Empresa Confidencial"` |
| `carreras` | lista de `{nombreCarrera}` — **NO trae ID** |
| `instituciones` | lista de `{idInstitucion, idInstitucionSqlServer, nombreInstitucion}` — **sí trae ID** |
| `habilidades` | `{nombreHabilidad, nombreNivel}`; nivel casi siempre vacío |
| `ubicacion.coordenadas` | ver trampa abajo |
| `aniosExperiencia` + `nombreOperadorExperiencia` | se contradicen a veces |
| `candidadPostulaciones` | typo de la API (no `cantidad`); viene `null` seguido |
| `candidadVisualizaciones` | idem |
| `slug` | null en ~90% de los casos |
| `nombreMoneda` | siempre "Pesos Chilenos" en lo observado |

**Trampa de coordenadas.** `ubicacion.coordenadas` dice
`"type": "Point"` pero el orden es **[lat, lon]**, al revés de GeoJSON.
Verificado con Antofagasta: `[-23.617728, -70.3915701]`. Alimentar esto
a una librería geoespacial estándar sin invertir pone los puntos en
Somalia.

### Campos muertos

`tiempoContrato`, `documentosRequeridos`, `archivosAdjuntos`,
`tieneEntrevistaIa`, `postulacionValidaInstitucion`, `exclusiva`:
vacíos en los 40 avisos de la sonda. `nombreArea` es 80% "Otra Área".

---

## 5. Hallazgos verificados

Todos medidos sobre datos reales. Los números vienen de dos fuentes:
el CSV de v7 de Administración y Comercio (agosto 2026, 24.001 filas /
6.142 avisos únicos) y la corrida v9 de Humanidades (37 avisos).

### 5.1 La búsqueda por palabra clave no discrimina carreras

En Administración y Comercio:

| par | contención | Jaccard |
|---|---|---|
| "Técnico en Administración de Empresas" ⊂ "Administración de Empresas" | **1,00** | 0,75 |
| "Ingeniería en Gestión y Control de Calidad" ⊂ "Ingeniería en Control de Gestión" | **1,00** | 0,43 |
| "Técnico en Comercio Exterior" ↔ "Ingeniería en Comercio Exterior" | 0,92 | 0,84 |

Tres términos aportaron **cero avisos exclusivos**. El 90,5% de las
filas no tenía ningún token del término en el título. El 24,1% de las
filas con `carreras_requeridas` no compartía ningún token con el
término que las encontró.

**Conclusión: el término de búsqueda no es atribución válida de
carrera.** Es solo un generador de candidatos.

**Anomalía sin explicar:** en Humanidades, "Licenciatura en Letras y
Literatura" devolvió solo 10 resultados (todos genéricos). Si el
matching fuera OR por tokens, "licenciatura" sola habría traído
cientos. El comportamiento observado en las dos áreas no es
consistente. No se investigó el mecanismo. Es especulación, pero
posiblemente pondera fuerte el campo de carreras declaradas.

### 5.2 Los avisos genéricos: Bresler

**10 avisos de un solo empleador (`empresa_id=1788`, "Crew Local
Heladería" en 10 comunas) declaran las 504 carreras del catálogo
completo, con conjunto idéntico entre ellos.** También declaran 46 de
las 56 instituciones observadas.

Consecuencias:
- Aparecen en la búsqueda de **cualquier** carrera, en todas las áreas.
- En Humanidades produjeron 5.040 de los 5.183 pares aviso×carrera.
- **Dieron gratis 504 carreras de una sola vez.** Pero ese conjunto
  **no es el catálogo completo** — ver §5.8. Sigue siendo el atajo más
  barato para tener casi toda la taxonomía sin correr las 10 áreas.

Distribución de `n_carreras_declaradas` en Humanidades:
`0,1,2,3,4,5,10,11,13,14,19,25` y después salta directo a `504`.
No hay nada entre 26 y 503. `UMBRAL_AVISO_GENERICO = 20` funciona;
cualquier valor entre 26 y 503 da lo mismo.

### 5.3 `estadoOferta`: la búsqueda devuelve avisos cerrados

13 de 40 en la sonda (muestra **no aleatoria**, no extrapolable).
1 de 37 en Humanidades.

No era detectable desde v7: solo 118 de 6.142 avisos tenían
`fecha_expiracion` vencida. Las bajas ocurren mucho antes del
vencimiento (vigencia declarada mediana: 59 días).

Habilita medir **duración de vacante**, que es probablemente la
variable más valiosa del monitor y no se podía calcular antes.

### 5.4 Identidad de empresa

- `"Empresa Confidencial"` = 1.517 avisos / **400 `empresa_id`
  distintos** en Administración. Agrupar por nombre los colapsa en uno.
- Un mismo `empresa_id` aparece con hasta **16 variantes de nombre**
  (ej. `empresa_id=3224` → "Centros Médicos y Dentales RedSalud").
- **1.028 de los 1.517 confidenciales (68%)** tienen un `empresa_id`
  que aparece identificado en otro aviso, dentro de la misma área y mes.
  Con acumulación entre áreas y meses ese número sube.
- El detalle **no filtra** el nombre en confidenciales. El cruce por
  `idCompany` es el mecanismo.
- `urlLogo` es un chivato limpio: genérico
  (`logo_generico_azul.jpg`) si es confidencial.

### 5.5 Taxonomía de carreras: no hay crosswalk

523 nombres distintos declarados en Administración; 504 en el catálogo
completo. Solo el **44,1% de las menciones** hace match exacto
normalizado contra un nombre SIES.

Los top sin mapear:
```
565  Ingeniería Civil
499  Ingeniería en Administración de Empresas
272  Administración de Empresas de Servicios
259  Ingeniería Ejecución Administración de Empresas
245  Ingeniería de Ejecución en Administración
241  Prevención de Riesgos / Seguridad Industrial
215  Administración de Ventas
208  Ingeniería
```

**La relación no es 1:1.** N:1 es el caso mayoritario (las tres
variantes de "Ingeniería en Administración" → un solo SIES). Pero
`"Prevención de Riesgos / Seguridad Industrial"` es 1:N — SIES separa
"Ingeniería en" de "Técnico en". Desempate disponible:
`nivel_academico` del aviso (Universitaria / Técnico profesional
superior).

### 5.6 Falsos positivos por término

"Filosofía" trajo 24 avisos propios en Humanidades. Revisión manual de
títulos: ~8 plausibles (docentes de ética, profesor de filosofía,
jefe de departamento de religión y filosofía) y **~16 sin relación**,
casi todos de minería e ingeniería ("Ingeniero Instrumentación",
"Especialista Faena Sierra Gorda"). Hipótesis no confirmada: la palabra
aparece en el cuerpo del aviso ("nuestra filosofía de trabajo").

Términos como "Historia", "Geografía", "Química", "Energía" son
palabras comunes y probablemente se comporten igual.

**Regla de uso derivada:** para cualquier análisis por carrera, filtrar
`fuente == 'declarada'` en `aviso_carrera.csv`. Las filas
`keyword_only` son trazabilidad, no evidencia. Costo: en Administración
el 34,5% de los avisos no declara carreras, así que se pierde un tercio
de la muestra. Es el precio de no inventar atribución.

### 5.7 Otras derivaciones que v7 hacía mal

- **`modalidad`**: v7 mapeaba "Jornada Completa" → `Presencial`. Eso es
  el 69% de los avisos, y ese valor de jornada **no informa modalidad**.
  v9 usa `No informado`.
- **`jornada`** mezcla tres dimensiones: extensión horaria (Completa,
  Part Time), modalidad (Teletrabajo, Mixta) y tipo de contrato
  (Práctica, Reemplazo, Free Lance, Comisionista). `tipo_contrato` se
  deriva aparte.
- **`experiencia_minima`** era un string concatenado, infiltrable, con
  16 casos contradictorios tipo `"Sin experiencia 2 años"`. Ahora son
  tres columnas: `exp_operador`, `exp_anios`, `exp_inconsistente`.
- **`flag_aviso_generico`** con umbral fijo marcaba 0,96% y no
  distinguía los de 504. Ahora se guarda `n_carreras_declaradas` como
  entero y el umbral se decide en análisis.
- **Formato largo**: v7 duplicaba `descripcion` 3,9 veces (42 MB de los
  74,8 MB del CSV). v9 normaliza en tablas separadas.

### 5.8 Derecho (agosto 2026): el término replica el cuerpo del aviso

Área corrida completa con v9. Un solo término de búsqueda: `"Derecho"`.
**342 avisos, 342/342 con detalle ok.** Todo lo de abajo está medido
sobre ese crudo.

**El mecanismo de matching quedó demostrado.** Los 342 avisos —el
100%— contienen la raíz `derech` en al menos uno de cuatro campos:

| campos donde aparece | avisos |
|---|---|
| solo `descripcionOferta` | 209 |
| `descripcionOferta` + `requisitosMinimos` | 70 |
| solo `carreras` | 31 |
| `carreras` + `requisitosMinimos` | 13 |
| otras combinaciones (incluyen `nombreCargo`) | 19 |

Cero avisos sin explicación. Dos casos son la prueba limpia: los avisos
`6108547` y `6085214` entraron por la frase **"ser la mano derecha del
gerente"**. No es el mismo lema ni la misma palabra — es *match por
prefijo sobre el cuerpo del aviso*. Esto confirma la hipótesis que en
§5.6 estaba marcada como no confirmada, y explica por qué el término no
sirve como atribución de carrera.

**Precisión del término: ~17,5%.** Solo 60 de 342 avisos tienen señal
jurídica profesional (44 por título, 48 por carrera declarada, 32 por
ambos). Los otros 282 entraron por usos no profesionales de la palabra:

```
 76  "corporación de derecho privado sin fines de lucro"
 42  "derecho a licencia médica"
 30  "...derechos y familia..."      (fundaciones de infancia)
 26  "...derechos y el bienestar..."
 15  "se reserva el derecho a declarar desierto el proceso"
```

**Un solo empleador aportó el 35% del área.** `idCompany=1801`
(Fundación Integra) publicó 120 avisos; 77 de ellos traen la frase
"corporación de derecho privado" en el boilerplate institucional.
Ninguno es un cargo jurídico salvo uno. Concentración general:

| | share de los 342 avisos |
|---|---|
| top 1 empleador | 35,1% |
| top 3 | 52,9% |
| top 10 | 71,6% |

69 `idCompany` distintos en total. **Un área entera del monitor puede
ser el boilerplate de una fundación.** Cualquier estadística por área
sin deduplicar por empleador es engañosa.

**Corrección a §5.2: las 504 de Bresler no son el catálogo completo.**
Derecho observó **506 nombres distintos**. Los dos que faltan en el
conjunto de Bresler son:

```
Psicopedagogía / Educación Diferencial
Trabajo Social / Servicio Social
```

Ambos vienen de **un único aviso** (`6105380`, confidencial, 6 carreras
declaradas). No son nombres raros: son compuestos con barra, y el
catálogo de Bresler ya tiene 43 de esa forma. Bresler declara
`Psicopedagogía`, `Pedagogía en Educación Diferencial`, `Trabajo Social`
y `Técnico en Servicio Social` por separado, pero no las dos formas
compuestas. La fuga es chica (2 de 506 = 0,4%) pero el corolario
importa: **hay que seguir acumulando `carreras_trabajando.csv` a medida
que se corren áreas.** No se puede congelar la taxonomía en 504.

Lo mismo, más fuerte, con instituciones: 90 observadas en Derecho, **44
fuera del conjunto de 46 de Bresler** (USS, UST, IP Los Leones, UVM,
ULAGOS…). Ahí Bresler cubre menos de la mitad.

**Bresler reaparece idéntico.** 10 avisos "Crew Local Heladería" en 10
comunas (Rancagua, Maipú, El Bosque, Estación Central, Curicó, San
Antonio, Temuco, Los Ángeles, Chillán, Quilicura), las mismas 504
carreras, las mismas 46 instituciones, conjunto exactamente idéntico
entre los 10. Es el mismo patrón de §5.2 con avisos nuevos.

**Distribución de `n_carreras_declaradas`:**
`0(151), 1(113), 2(30), 3(11), 4(7), 5(7), 6(5), 7(3), 8, 11, 15, 19, 25`
y después `504(10)`. Mismo salto que en Humanidades. El único aviso
entre 20 y 504 es `6102956` (Universidad Mayor, 25 carreras) — un
concurso académico legítimamente multidisciplinario que
`UMBRAL_AVISO_GENERICO = 20` marca como genérico. Es un falso positivo
del umbral, uno solo, y es el precio de tener un umbral.

**El resto del perfil:**

| variable | valor |
|---|---|
| `estadoOferta` | 340 PUBLICADA / 2 DESACTIVADA |
| confidenciales | 30 avisos (8,8%) / 21 `idCompany` |
| ↳ recuperables en la misma corrida | 9 avisos / 6 `idCompany` |
| sin carreras declaradas | 151 (44,2%) |
| con habilidades | 52 (15,2%) |
| `mostrarSueldo` | 10 (2,9%) |
| región Metropolitana | 211 (61,7%) |
| nivel Universitaria | 179 (52,3%) |
| `nombreArea` = "Otra Área" | 204 (59,6%) |

Nota sobre `nombreArea`: el segundo valor más frecuente es
**"Estimulación temprana" (107)**, que es Fundación Integra. Confirma
que el campo describe al empleador, no al área del monitor.

Las 2 desactivadas son `cota_superior`, no duración observada: ya
estaban de baja en el primer avistamiento. Con una sola corrida no hay
ninguna duración medida — hacen falta dos.

---

## 6. Las maestras

Todas en `maestras/`. `consolidar.py` es **idempotente**: se puede
correr las veces que sea.

| tabla | grano | clave |
|---|---|---|
| `avisos.csv` | 1 fila por aviso | `aviso_id` |
| `aviso_carrera.csv` | aviso × carrera declarada | compuesta |
| `aviso_termino.csv` | aviso × término de búsqueda | compuesta |
| `aviso_habilidad.csv` | aviso × habilidad | compuesta |
| `aviso_institucion.csv` | aviso × institución | compuesta |
| `empresas.csv` | 1 fila por empresa | `empresa_id` |
| `carreras_trabajando.csv` | 1 fila por nombre | `carrera_trabajando` |
| `instituciones.csv` | 1 fila por institución | `id_institucion` |

### Columnas manuales — CRÍTICO

`empresas.csv`, `carreras_trabajando.csv` e `instituciones.csv` usan
upsert con **preservación de columnas manuales**: cualquier columna que
el script no gestione se arrastra por clave. Las filas que dejan de
aparecer en el crudo tampoco se borran.

Probado: se agregaron `rubro`/`tamano` a empresas y
`carrera_sies`/`tipo_relacion`/`revisado_por` a carreras, se
reconsolidó, y sobrevivieron intactas.

**No romper esta propiedad.** Es lo que permite que el trabajo manual
de homologación y enriquecimiento coexista con corridas automáticas.

### Panel longitudinal

`aviso_id` es estable entre corridas. Columnas derivadas:

```
primera_vez_visto, ultima_vez_visto, n_corridas_visto, periodos_visto
estado_primero, estado_ultimo
fecha_desactivacion_detectada, dias_publicado_hasta_baja
calidad_duracion, censurado
```

**`calidad_duracion` tiene tres valores que NO se deben mezclar:**

- `observada` — se vio `PUBLICADA` y después `DESACTIVADA`. Única
  medición real. Precisión limitada por el intervalo entre corridas.
- `cota_superior` — la primera vez que se vio ya estaba de baja. El
  número es un techo, no una duración.
- `censurada` — seguía viva en la última observación.

Mezclarlas sesga la mediana hacia arriba. El resumen de
`consolidar.py` ya las separa.

### Ruta A — término de búsqueda → SIES

`carreras_sies_2026.py` expone `TERMINO_A_SIES` y `TERMINO_A_AREAS`,
índices invertidos derivados del propio catálogo. `consolidar.py` los
importa (import blando: si el módulo no está, las columnas quedan vacías
y **avisa en pantalla**, no falla en silencio) y produce:

- en `avisos.csv`: `sies_por_termino`, `n_sies_por_termino`,
  `areas_sies_por_termino`, `n_terminos_sin_mapeo`
- la tabla `aviso_termino.csv` (aviso × término, con `carrera_sies`,
  `areas_sies`, `mapeado`)

**LEER ANTES DE USAR: esto sobre-atribuye por diseño.** El término es lo
que se buscó, no lo que el aviso declara. En Derecho los 342 avisos
quedan con `sies_por_termino = "Derecho"`, incluidos los 120 de
Fundación Integra que son de salas cuna. Con el ~82% de falsos positivos
medido en §5.8, la columna es **señal de contexto, no clasificación**.
La atribución fuerte sigue siendo la homologación manual de
`carrera_trabajando` → SIES.

Qué aporta de verdad: **solo 16 de los 199 pares traducen algo distinto
a la identidad.** El valor está en normalizar esos 16 y en adjuntar el
área SIES, que es más principiada que `nombreArea` de la API (que
describe al empleador — ver §5.8).

`n_terminos_sin_mapeo` sirve como detector de deriva: si el catálogo se
edita después de una corrida, los términos viejos del crudo dejan de
mapear y el número deja de ser 0.

**Redundancia conocida:** `aviso_termino.csv` supersede las filas
`fuente == 'keyword_only'` de `aviso_carrera.csv` (verificado:
subconjunto estricto, 151 ⊂ 342 en Derecho). Se dejaron por
compatibilidad; conviene retirarlas en una limpieza posterior.

### Filtros de genericidad

- `carreras_trabajando.n_avisos_especificos` — cuenta solo avisos con
  `n_carreras_declaradas <= UMBRAL_AVISO_GENERICO` (**30** desde agosto
  2026; antes 20). Es el orden correcto para priorizar homologación.
  Efecto medido en Humanidades: la cobertura del top 50 pasó de 11,7% a
  83,3%.

  **Por qué se subió a 30.** La distribución es bimodal con un hueco
  grande: el máximo legítimo observado es 25 y el siguiente valor es
  504. Cualquier corte dentro del hueco da el mismo resultado, pero 20
  caía fuera y marcaba como genérico el aviso `6102956` (Universidad
  Mayor, 25 carreras), un concurso académico legítimamente
  multidisciplinario — el falso positivo de §5.8. Medido sobre Derecho:
  pasar de 20 a 30 cambia solo ese aviso (25 carreras suben +1 en
  `n_avisos_especificos`, nada más). Revisar el corte si aparece un área
  que puebla el hueco entre 26 y 503.
- `instituciones.n_avisos_especificos` — **usa el umbral de carreras
  como proxy y es imperfecto.** Un aviso con 19 carreras declaró 35 de
  56 instituciones y cuenta como específico. `aviso_institucion.csv`
  guarda `n_instituciones_aviso` para poder calibrar un umbral propio
  cuando haya volumen. Leer esta columna con reserva.

---

## 7. Estado actual y qué falta

### Corrido

| área | términos | estado |
|---|---|---|
| Derecho | 1 | ✅ v9, 342 avisos, consolidado (ago 2026) |
| Humanidades | 3 | ✅ v9, 37 avisos, consolidado |
| Administración y Comercio | 28 | ⚠️ solo v7 (CSV viejo, sin `estadoOferta` ni instituciones) |
| Agropecuaria | 9 | ⚠️ solo v7 |
| Las otras 6 | — | ❌ |

Derecho tardó poco: un solo término. Rinde 342 avisos, casi diez veces
Humanidades con un tercio de los términos — pero ~82% es ruido (§5.8).
**Volumen de avisos y volumen de información no son lo mismo.**

Áreas por tamaño: Derecho 1, Humanidades 3, Agropecuaria 9,
Arte y Arquitectura 12, Ciencias Sociales 14, Educación 14,
Ciencias Básicas 15, Salud 22, Administración y Comercio 28,
Tecnología 81.

Los CSV de v7 **no son convertibles a crudo v9** sin perder campos.
Decisión tomada: no re-correr Administración por ahora (tarda 42 min en
v7). Los datos viejos siguen siendo útiles como referencia. La duración
de vacante no se pierde porque se calcula contra `fecha_publicacion`,
que viene exacta de la API en cada aviso.

### Pendientes

**1. Correr las áreas restantes.** Orden sugerido: de menor a mayor.
Reanudable: si se corta, relanzar el mismo comando.

**2. Homologación carreras trabajando → SIES.** Es el cuello de botella
real y **no depende de correr más áreas**. La ruta A (§6) no la
reemplaza, porque va desde el término buscado y no desde lo que el aviso
declara.

**El andamio ya existe** (agosto 2026): `homologar.py` genera
`maestras/homologacion_carreras.csv` a partir de la taxonomía observada.
Automatiza solo el match exacto normalizado y ordena el resto por
`n_avisos_especificos`, que es la prioridad correcta. Medido sobre
Derecho: de 506 nombres, **121 se resuelven solos y cubren el 68% de los
avisos específicos** — el trabajo manual queda sobre el 32% restante.

Es idempotente y preserva las columnas manuales, incluidas las que
inventes. La clave es compuesta `(carrera_trabajando, nivel_condicion)`,
así que un caso 1:N se resuelve duplicando la fila y poniendo
`universitaria` en una y `tecnica` en la otra. Verificado.

Genera además `sugerencia` y `score` por solapamiento de tokens.
**Nunca se aplican solas.** Y conviene mirarlas con desconfianza: a
"Ingeniería Civil" le sugiere "Ingeniería Civil Industrial" con score
0,67, que es exactamente la confusión contra la que advierte §5.5. Sirven
para ordenar la pantalla, no para decidir.

Lo que sigue pendiente es el trabajo humano: abrir el CSV y completarlo.
El diseño acordado, ya implementado en el archivo:

```
homologacion_carreras.csv
  carrera_trabajando      texto exacto (no hay ID)
  nivel_condicion         * | universitaria | tecnica
  carrera_sies
  area_sies
  tipo_relacion           exacta | agregacion | ambigua | sin_equivalencia
  n_avisos_especificos    para priorizar
  revisado_por
  fecha_revision
  nota
```

Decisiones acordadas:
- CSV, no dict de Python: lo edita una persona, probablemente en
  planilla.
- `sin_equivalencia` es una fila explícita, no un hueco. Así
  "Ingeniería Civil" a secas queda como decisión tomada.
- `nivel_condicion` permite resolver los 1:N usando `nivel_academico`
  del aviso.
- **Automatizar solo match exacto normalizado.** Nada de fuzzy: en esta
  taxonomía "Ingeniería Civil" e "Ingeniería Civil Industrial" están a
  un token y son carreras distintas. `homologar.py` genera columnas
  `sugerencia`/`score` que **nunca se aplican solas**, solo ordenan la
  pantalla para revisión manual.
- La homologación **no va en el scraping**. Se hace sobre las maestras
  y se puede rehacer cuantas veces se quiera.

**3. Base de empresas enriquecida.** `empresas.csv` ya acumula
`nombre_canonico`, `nombres_observados` (contador completo, no solo el
ganador), fechas y áreas. Faltan columnas manuales: `rubro`, `tamano`,
`rut`. La API no expone rubro — verificado, hay que traerlo de otra
fuente.

Nota: `nombre_canonico` se calcula sobre todo el crudo disponible. Con
más áreas mejora la resolución de confidenciales.

**4. Validar términos de búsqueda.** Propuesta no implementada: agregar
un `estado_termino` (`validado` / `sin_resultados` /
`sospecha_falsos_positivos`) para no perder el diagnóstico. Casos
conocidos: "Licenciatura en Letras y Literatura" (0 reales),
"Filosofía" (~60% falsos positivos), **"Derecho" (~82% falsos
positivos, medido — §5.8)**.

Con Derecho el mecanismo dejó de ser hipótesis: la búsqueda matchea por
prefijo sobre el cuerpo del aviso. Eso vuelve **predecible** el
problema. Términos que son palabras corrientes del castellano
("Derecho", "Historia", "Geografía", "Química", "Energía",
"Administración", "Diseño", "Construcción") van a arrastrar ruido
proporcional a su frecuencia en prosa de RR.HH., no a la demanda
laboral real. Un diagnóstico barato por término, calculable sobre el
crudo sin volver a scrapear:

```
precision_titulo   = avisos con el término en nombreCargo / total
precision_carrera  = avisos con carrera declarada afín  / total (sin genéricos)
concentracion_top1 = share del empleador más frecuente
```

En Derecho eso da 14,3% / 14,0% / 35,1%. Los tres números juntos
señalan el problema; ninguno solo alcanza.

**5. Memoria de `consolidar.py`.** Carga todos los crudos en RAM antes
de escribir. Con 10 áreas y varios meses podría reventar en Colab.
No medido. Se arregla con streaming si llega a pasar; no optimizar
antes.

---

## 8. Advertencias operativas

- **`CONCURRENCIA = 4`** en `scraper_v9.py` no está validado contra
  carga real más allá de áreas chicas. Si aparecen muchos HTTP 429,
  bajar a 2. El retry con backoff los absorbe pero es señal.
- **Colab corta** por inactividad (~90 min) y tiene tope de 12 h. Por
  eso todo es reanudable.
- **Los avisos de Bresler reaparecen en cada área.** Es correcto:
  `aviso_id` los deduplica y `areas_scraping` acumula dónde salieron.
- **El catálogo tiene 199 carreras pero 198 términos únicos.**
  `"Ingeniería en Geomensura y Cartografía"` está en Ciencias Básicas y
  en Tecnología con el mismo nombre SIES (cero conflictos). Las dos
  corridas van a buscar el mismo término y traer los mismos candidatos;
  `aviso_id` los deduplica. Se detecta con
  `python carreras_sies_2026.py`.
- **v7 tardó 42 min en Administración.** v9 debería ser menos por la
  concurrencia en la fase de detalle, pero la búsqueda sigue siendo
  secuencial. No medido en un área grande.

---

## 9. Lecciones de diseño

1. **Separar captura de derivación.** Se usó cuatro veces en un día
   para arreglar bugs sin re-scrapear.
2. **Guardar el crudo íntegro.** Cada inspección de la API reveló
   campos valiosos que se estaban descartando.
3. **Contar sobre estructuras deduplicadas, no sobre el loop de
   observaciones.** Bug encontrado en testing: un aviso visto en dos
   corridas inflaba los contadores de carreras e instituciones.
4. **Un booleano derivado de un umbral arbitrario destruye
   información.** Guardar el entero.
5. **No presentar inferencias como datos.** `modalidad = Presencial`
   para el 69% de los avisos era una invención del mapeo.
6. **Correr primero un área chica.** Humanidades produjo cuatro
   parches en una tarde. Habría sido carísimo descubrirlos en
   Tecnología.
7. **Marcar la calidad del dato en el dato.** `calidad_duracion`,
   `fuente_atribucion`, `exp_inconsistente`, `detalle_ok`.
8. **Deduplicar por empleador antes de leer cualquier agregado.** En
   Derecho un empleador es el 35% del área y su boilerplate institucional
   es lo que la generó. El conteo de avisos mide publicación, no demanda.
9. **Un diagnóstico equivocado es casi tan malo como ninguno.** La
   primera versión del aborto decía "es un rechazo del sitio" ante un
   fallo de TLS local: el sitio nunca había sido contactado. Distinguir
   "vacío" de "fallo" no alcanza; hay que distinguir *quién* falló.
   `clasificar_error()` separa SSL, DNS, timeout y respuesta del
   servidor, y cada uno dice qué hacer.
10. **Fallar en silencio es peor que fallar.** Seis corridas anunciaron
   "CAPTURA COMPLETA" con cero avisos mientras Akamai las rechazaba, y
   el problema se descubrió por casualidad. Un pipeline tiene que
   distinguir "no encontré nada" de "me rechazaron" y decirlo fuerte.
11. **Un catálogo obtenido de un solo caso raro es una muestra, no un
   censo.** Las 504 de Bresler parecían el universo; una sola corrida
   más agregó dos nombres. La taxonomía se acumula, no se congela.
