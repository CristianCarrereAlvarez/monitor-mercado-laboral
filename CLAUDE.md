# CLAUDE.md — Monitor Mercado Laboral Chile

Contexto completo del proyecto para continuar el trabajo. Escrito en
agosto 2026 al cerrar la sesión de rediseño v7 → v9, y actualizado el
16 de agosto con la primera corrida completa de las 10 áreas (§5.9).

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
| `procesar.sh` | todo lo que va después de capturar: consolidar + control + diccionario |
| `scraper_v9.py` | vigente — captura |
| `consolidar.py` | vigente — derivación |
| `control.py` | chequeos de calidad + panel; lo corre `mensual.sh` solo |
| `homologar.py` | genera la cola editable de homologación |
| `homologacion.py` | el join carrera → programa: define la clave y resuelve los destinos |
| `validar_homologacion.py` / `validar.sh` | revisa la homologación contra el catálogo propio y ISCED-F |
| `programas_propios.csv` | catálogo propio: 204 programas, con genérica SIES, niveles e ISCED-F |
| `isced_f_2013.csv` | ISCED-F 2013 (UNESCO): 138 códigos amplio/estrecho/detallado |
| `mirar.py` / `mirar.sh` | qué hay detrás de un nombre de carrera; apoya la homologación |
| `coocurrencia.py` / `coocurrencia.sh` | genera `coocurrencia_programas.html`: qué programa se pide junto con qué, y qué nombres de aviso lo alimentan |
| `diccionario.py` | genera `DICCIONARIO.md` desde los datos reales |
| `variables.py` / `variables.sh` | genera `variables_maestras.html`: las mismas glosas, para consultar mientras se trabaja |
| `glosario.py` | las glosas de las columnas, escritas a mano |
| `DICCIONARIO.md` | generado; **no editar a mano** |
| `carreras_sies_2026.py` | vigente — catálogo + índices; lo usan v9 y consolidar |
| `CLAUDE.md` | este documento |
| `.gitignore` | excluye bytecode, checkpoints de Colab, `crudo/` y `maestras/` |

**El diccionario de variables** se genera, no se escribe:

```bash
python3 diccionario.py --maestras "<datos>/maestras" --crudo "<datos>/crudo"
```

`diccionario.py` lee las maestras y el crudo reales, los cruza con los
esquemas de `consolidar.py`/`homologar.py` y con las glosas de
`glosario.py`, y marca cada columna como descrita, **SIN DOCUMENTAR** o
**HUÉRFANA** (hay glosa, ya no hay columna). Distingue además las
columnas que vienen del código de las agregadas a mano, y calcula el
relleno de cada una.

La razón de generarlo es la misma de la lección 10: un diccionario
escrito a mano se desincroniza **en silencio**. Si `consolidar.py` suma
una columna, un documento estático no la menciona y el lector cree que
la lista está completa. Acá aparece como SIN DOCUMENTAR.

Correrlo después de tocar `consolidar.py` o `homologar.py`, y commitear
el `DICCIONARIO.md` resultante. No está enganchado a `mensual.sh` a
propósito: cambia cuando cambia el **código**, no cuando llegan datos
nuevos.

**Al escribir una glosa, solo se documenta lo verificado.** Si no se
sabe qué es una columna, se deja afuera y el diccionario la lista como
pendiente. Un hueco visible es información; una glosa plausible pero
falsa, no.

**Las mismas glosas, en una página que se abre con doble clic:**

```bash
./variables.sh
```

Deja `<datos>/variables_maestras.html` en Drive: las 115 columnas de las
nueve maestras, con buscador sobre el nombre y sobre el texto de la
definición, y una banda al margen en las 34 columnas cuya glosa existe
sobre todo para evitar una mala lectura (`n_corridas_visto` no cuenta
corridas, `sies_por_termino` sobre-atribuye por diseño, los tres valores
de `calidad_duracion` no se promedian juntos).

No reemplaza a `DICCIONARIO.md`, hace lo contrario. El diccionario es el
documento de **control**: cruza las glosas con los datos y los esquemas
reales para que se vea lo que falta, y por eso necesita las maestras y el
crudo a mano. La página es la **referencia**: no lee ni maestras ni
crudo —sale entera de `consolidar.py`, `homologar.py` y `glosario.py`—,
así que corre en cualquier máquina. El texto es el mismo objeto en los
dos casos, `glosario.py`; hay un solo lugar donde escribir.

Se regenera cuando cambia el **código**, igual que el diccionario. La
lista de columnas con banda de cautela es editorial y vive en
`variables.py`: si se escribe una glosa de ese tipo, hay que sumarla ahí.

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
cd ~/monitor-mercado-laboral && git pull --no-edit
./mensual.sh                  # las 10 áreas + consolidación
./capturar.sh "Agropecuaria"  # una sola área
./procesar.sh                 # consolidar + control + diccionario

./mirar.sh "Ingeniería en Metalmecánica"   # qué avisos hay detrás
./mirar.sh --buscar metal                  # qué nombres contienen "metal"
./coocurrencia.sh                          # el dashboard HTML de co-ocurrencia
./variables.sh                             # la referencia HTML de variables
./validar.sh                               # revisa la homologación
```

`procesar.sh` es para cuando el post-proceso se corre aparte de la
captura — porque se cortó, porque cambió el código, o porque se quiere
regenerar el diccionario. `mensual.sh` ya consolida y controla solo.

Existe por lo mismo que `capturar.sh`. Las tres etapas necesitaban
exportar la ruta de Drive, hacer `cd` y pasar rutas a mano en cada
comando; pegar ese bloque en la terminal falla en cuanto algo se
detiene a preguntar —un editor, una contraseña— porque el resto del
texto se le mete adentro al que preguntó. Pasó tres veces en un día:
una con vim tras un `git pull`, otra con el prompt de credenciales de
`git push`, que se tragó las dos líneas siguientes y dejó `$D` sin
definir.

**Corolario de terminal: pegar los comandos de a uno.** Y usar
`git pull --no-edit`, que no abre editor al mergear.

Los envoltorios resuelven la carpeta de datos y el modo de sesión solos.
Ver §4 para el detalle.

### El notebook, y por qué quedó tan chico

`SMLab.ipynb` está **en el repo**, no suelto en Drive: se abre desde
GitHub (hay un badge de Colab en la primera celda) o con Jupyter local, y
se versiona como cualquier otro archivo. Se guarda **con las salidas
limpias**: sin outputs no hay fuga de datos ni diffs enormes.

Tenía 37 celdas y quedó en 15. La razón es un criterio, no una limpieza:
**lo que se corre igual todos los meses no es exploración, es un
programa.** Los chequeos, el panel y la cola de homologación pasaron a
`control.py` y `homologar.py`, que además `mensual.sh` puede encadenar.

Al notebook le queda lo único que un cuaderno hace mejor que un script:
preguntas nuevas, donde cada paso depende de lo que viste en el anterior.
Carga las maestras, recuerda las tres reglas que condicionan cualquier
análisis, y deja una celda en blanco. Si una pregunta se vuelve rutina,
su lugar es `control.py`.

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
que el Mac no se suspenda, **consolida y corre `control.py`** al final, y
deja todo en un log por corrida en `<datos>/logs/`.

Que el control salga solo es deliberado: si dependiera de acordarse de
correrlo, tarde o temprano no se corre. Es la lección 10 aplicada a la
verificación.

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
| `nombreNivelAcademico` | **opción única** de una lista de 9 valores; nivel formativo declarado por el empleador |
| `aniosExperiencia` + `nombreOperadorExperiencia` | se contradicen a veces |
| `candidadPostulaciones` | typo de la API (no `cantidad`); viene `null` seguido |
| `candidadVisualizaciones` | idem |
| `slug` | null en el 93% de los avisos, pero **reconstruible** |
| `nombreMoneda` | siempre "Pesos Chilenos" en lo observado |

**Trampa de coordenadas.** `ubicacion.coordenadas` dice
`"type": "Point"` pero el orden es **[lat, lon]**, al revés de GeoJSON.
Verificado con Antofagasta: `[-23.617728, -70.3915701]`. Alimentar esto
a una librería geoespacial estándar sin invertir pone los puntos en
Somalia.

### La URL pública se reconstruye

`slug` tiene la forma `{idOferta}-{nombreCargo normalizado}`: minúsculas,
sin tildes, y cualquier corrida de caracteres no alfanuméricos colapsada
en un guion. La API lo trae en **676 de 9.125 avisos (7%)**.

Hasta agosto 2026, `consolidar.py` emitía `/trabajo/{aviso_id}` cuando
faltaba — un patrón **nunca probado contra el sitio**, y que no resuelve:
la columna `url` apuntaba a ninguna parte para el 93% de los avisos.

`slugificar()` reconstruye el slug desde el título. **Validado contra los
676 que traen el valor real: lo reproduce en el 100%.** Por eso se aplica
al 93% restante sin volver a golpear el sitio, y las URLs viejas se
arreglan con solo reconsolidar.

Es un caso de la lección 5 en su forma más barata de cometer: nadie
inventó un dato, se inventó una **derivación** y se publicó sin abrir
una sola de las URLs que producía.

### El listado trae cosas que el detalle no

El crudo guarda entera la respuesta del buscador, además del detalle.
Nunca se había mirado; documentada en agosto 2026, tiene 13 claves y
tres que **no** son la misma que su homónima del detalle:

| clave del listado | qué la hace distinta |
|---|---|
| `descripcionOferta` | **fragmento de resultados, con el término buscado resaltado en `<strong>`** |
| `fechaPublicacion` | trae **hora**: `2026-08-12 12:10`. El detalle solo da la fecha |
| `geolocalizacion` | string `lat,lon` en el orden que dice; el del detalle viene invertido |

**El fragmento resaltado es el hallazgo con más futuro.** §5.8 tuvo que
deducir por qué un aviso entró en una búsqueda leyendo los cuatro
campos y buscando la raíz a mano. El listado ya lo dice: el `<strong>`
marca dónde matcheó. Eso convierte el diagnóstico por término (§7
pendiente 4) de una heurística por tokens —que ya falló dos veces— en
una lectura directa del dato. **Sin volver a scrapear**: está en el
crudo desde agosto.

La hora de publicación también se está descartando: `consolidar.py` usa
`fechaPublicacionFormatoIngles` del detalle, que es solo `aaaa-mm-dd`.

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

**Con el corpus completo el hueco desapareció.** Medido sobre los 9.125
avisos de agosto 2026:

```
21→3  22→9  23→4  24→1  25→3     antes 25 era el máximo legítimo
26→3  28→1  29→3  30→3           hoy cuentan como ESPECÍFICOS
31→2  32→2  33→7  41→1  43→1
44→1  47→1  49→2  59→1  100→1    hoy cuentan como GENÉRICOS
504→10                           Bresler
```

La distribución es **continua de 0 a 100**. El único salto real que
queda está **entre 100 y 504**. Los 29 avisos con más de 30 carreras
caen todos dentro del viejo hueco de 26–503.

Esto no invalida el umbral, invalida su **justificación**. El argumento
era "el corte cae en un vacío, así que su valor exacto no cambia nada".
Ahora sí cambia: mover el corte a 101 sumaría 789 pares aviso×carrera a
las menciones específicas (+3,9%); bajarlo a 25 restaría 283 (−1,4%).

**Los 29 avisos revisados uno por uno: ninguno es un concurso
multidisciplinario.** Son avisos comunes con un cargo concreto —
"Vendedor E-Commerce" con 33 carreras, "Técnico Tratamiento de Agua"
con 43, "Supervisor Terreno Exploraciones" con 100. Empleadores
ensanchando el embudo, no instituciones convocando a varias
disciplinas. O sea: **el umbral no debe subir a 101.**

**Y el tamaño no es un estadístico suficiente.** Cruzando los conjuntos
declarados por empleador (avisos de 20 a 503 carreras, `fuente =
declarada`):

| empleador | avisos | conjuntos distintos | tamaños |
|---|---:|---:|---|
| Salazar Israel | 5 | **1** | 22 ×5 |
| Autoplanet | 5 | 4 | 22, 29, 29, 31, 31 |
| AMERICAR | 4 | **1** | 33 ×4 |
| Panorama | 3 | **1** | 20 ×3 |
| Aramark | 3 | **1** | 30 ×3 |
| PORTILLO | 2 | **1** | 33 ×2 |
| ECRGROUP | 2 | **1** | 49 ×2 |
| Universidad Mayor | 2 | 2 | 23, 25 |
| ME ELECMETAL | 2 | 2 | 24, 29 |
| Consultor Selección | 2 | 2 | 26, 59 |
| Alpes Talent Consulting | 2 | 2 | 23, 28 |

Siete de doce empleadores repiten **un conjunto idéntico** en todos sus
avisos: es un perfil guardado, no una decisión por vacante. Pero esas
plantillas están en 20, 21, 22, 30, 33 y 49 — **a ambos lados de
cualquier corte**. Salazar Israel (22) cuenta hoy como específico y
AMERICAR (33) como genérico, y hacen exactamente lo mismo.

El caso decisivo es **Universidad Mayor: 2 avisos, 2 conjuntos
distintos** de 23 y 25. El concurso legítimo se comporta distinto de la
plantilla —cada uno trae su propia lista— pero cae en el mismo rango de
tamaño. Ningún valor del umbral los separa.

Autoplanet marca el límite de la idea: 5 avisos, 4 conjuntos, tamaños
22–31. No es plantilla rígida sino un conjunto base que editan. **La
genericidad es gradual, no binaria.**

**Decisión: queda en 30.** No porque esté bien fundado sino porque
ninguna alternativa es mejor y la población en disputa es el 0,65% de
los avisos (59 con 21 carreras o más, sobre 9.125). Lo que corresponde
no es afinar el corte sino **guardar la señal**: un hash del conjunto
declarado y cuántos avisos lo comparten identifican a Bresler y a
AMERICAR sin umbral, y dejan afuera a Universidad Mayor. Lección 4
otra vez — guardar la cantidad, no el booleano.

### 5.3 `estadoOferta`: la búsqueda devuelve avisos cerrados

13 de 40 en la sonda (muestra **no aleatoria**, no extrapolable).
1 de 37 en Humanidades.

No era detectable desde v7: solo 118 de 6.142 avisos tenían
`fecha_expiracion` vencida. Las bajas ocurren mucho antes del
vencimiento (vigencia declarada mediana: 59 días).

Habilita medir **duración de vacante**, que es probablemente la
variable más valiosa del monitor y no se podía calcular antes.

### 5.4 Identidad de empresa

Las cuatro primeras cifras son de **v7, área Administración, un mes**.
Se conservan porque el mecanismo que muestran sigue vigente; para el
corpus completo, ver §5.9.

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

Medido sobre las 10 áreas v9 (9.125 avisos, 792 empresas):

| | |
|---|---|
| avisos confidenciales | 1.872 (20,5%) |
| ↳ con `empresa_id` identificado en otro aviso | 1.323 (**70,7%**) |
| empresas siempre confidenciales | 167 |
| empresas con >1 variante de nombre | 95 de 792 |
| máximo de variantes en una empresa | 19 |

El 70,7% contra el 68% de v7 —y contra el 30% que dio Derecho solo—
confirma lo que §5.4 anticipaba: **acumular áreas mejora la resolución
de confidenciales**, porque cada área nueva es otra chance de ver el
mismo `empresa_id` identificado.

Las 167 empresas sin ningún nombre registrado son **exactamente** las
167 marcadas `siempre_confidencial`. Coincidencia perfecta: no hay fugas
de nombre por un lado ni pérdidas por el otro.

El peor caso de variantes ya no es RedSalud (15) sino
`RENEE RPO Asistido para …` con **19**, que es una consultora de
reclutamiento que renombra el aviso por cliente final. Ahí
`nombre_canonico` elige uno arbitrario y los otros 18 quedan en
`nombres_observados`; es un caso donde el nombre canónico no significa
gran cosa y hay que leer el JSON completo.

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

> **Alcance: esto es un área, y una chica.** El mecanismo de matching
> (match por prefijo sobre el cuerpo del aviso) es general y quedó
> demostrado acá. Las cifras de **concentración por empleador no lo
> son**: en el corpus completo el top 1 baja de 35,1% a 5,5% (§5.9).
> Derecho es un caso extremo, no el retrato del monitor.

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

### 5.9 El corpus completo (agosto 2026): las 10 áreas

Primera corrida completa. `mensual.sh` hizo Arte y Arquitectura →
Tecnología el 16/08 entre 13:38 y 17:51 (**4 h 13 min**); Derecho,
Humanidades y Agropecuaria venían de corridas del mismo día.

```
10 áreas   17.744 observaciones   9.125 avisos únicos
detalle ok 9.125/9.125  (100%)
792 empresas   528 carreras   283 instituciones
```

Cero fallos de detalle en 9.125 avisos. Líneas de crudo por área
(con solapamiento entre áreas):

| área | avisos | | área | avisos |
|---|---:|---|---|---:|
| Administración y Comercio | 6.044 | | Arte y Arquitectura | 447 |
| Tecnología | 5.883 | | Derecho | 342 |
| Ciencias Sociales | 2.841 | | Educación | 322 |
| Salud | 1.062 | | Agropecuaria | 186 |
| Ciencias Básicas | 580 | | Humanidades | 37 |

Las dos más grandes son el 65% de las observaciones. **Cada aviso
apareció en 1,9 áreas en promedio** (17.744 / 9.125): el solapamiento
entre áreas es enorme y `aviso_id` es lo único que lo contiene.

| variable | valor |
|---|---|
| confidenciales | 1.872 (20,5%) |
| sin carreras declaradas | 3.703 (40,6%) |
| con habilidades | 1.854 (20,3%) |
| estado último | 9.083 PUBLICADA / 42 DESACTIVADA |
| genéricos (>30 carreras) | 29 (0,3%) |

**La concentración por empleador se desploma respecto de Derecho.**

| | Derecho solo | corpus completo |
|---|---:|---:|
| top 1 | 35,1% | **5,5%** |
| top 3 | 52,9% | 12,6% |
| top 10 | 71,6% | 25,7% |

El top 1 es J.E.J. Ingeniería (505 avisos) y Fundación Integra —el 35%
de Derecho— cae al 1,6%. La lección 8 sigue en pie, pero su alcance
cambia: **deduplicar por empleador es crítico en áreas chicas y
marginal en el agregado.** Con 792 empresas y 237 de ellas con un solo
aviso, el corpus completo no está dominado por nadie.

**Duración de vacante sigue en cero.** 42 desactivadas, las 42
`cota_superior`. Hace falta la corrida de septiembre; es el diseño
funcionando, no una falla.

#### La taxonomía saturó, y es una lista controlada

- **528 nombres.** Con Derecho solo había 506: **+22 en nueve áreas
  más**, incluidas las dos más grandes. La curva está plana.
- **504 de los 528 aparecen en las 10 áreas con conjunto idéntico** —el
  patrón Bresler—; solo **24 quedan fuera** de ese conjunto.
- Al normalizar (minúsculas, sin tildes, sin puntuación) colisionan
  **exactamente 2 pares** de 528 (**0,4%**):

```
Ingeniería Civil en Minas  /  Ingeniería civil en minas
Técnico en Instrumentación,Automatización…  /  …Instrumentación, Automatización…
```

Ese 0,4% es el dato que decide qué clase de campo es. Si fuera texto
libre habría decenas de variantes por mayúsculas, tildes, espacios y
typos. **Es una lista controlada** con dos entradas cargadas a mano.

**Pero lista controlada no es taxonomía.** Conviven como hermanas al
mismo nivel `Ingeniería`, `Ingeniería de Ejecución`, `Ingeniería
Civil`, `Ingeniería Civil Industrial` e `Ingeniería Industrial`; hay
entradas que fusionan sinónimos con barra (`Marketing / Mercadotecnia`,
`Prevención de Riesgos / Seguridad Industrial`); y `Ingeniería` a secas
tiene 281 avisos específicos. No hay principio de clasificación, hay
vocabulario.

La consecuencia es práctica y buena: **una lista controlada es
homologable y finita.** Texto libre no lo sería.

Contra SIES:

```
match exacto normalizado : 121 de los 198 nombres SIES
                           (123 filas: las 2 colisiones se resuelven dos veces)
                           cubre ~51% de las menciones específicas
trabajando sin equivalente SIES : 405
SIES que nunca aparece declarado :  77
```

**Los 77 SIES sin menciones NO son ausencia de demanda.** Ahí están
`Ingeniería en Minas`, `Ingeniería Naval`, `Pedagogía en Educación
Física`, `Técnico en Telecomunicaciones`. trabajando les pone otro
nombre —tiene `Ingeniería Civil en Minas`, no `Ingeniería en Minas`—.
Es desajuste de vocabulario, y es exactamente lo que la homologación
arregla. Leerlo como "no hay avisos de esa carrera" sería el error
contra el que se cuida todo este documento.

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
| `aviso_programa.csv` | aviso × programa propio o campo ISCED | compuesta |
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

**`n_corridas_visto` no cuenta corridas — cuenta observaciones.**
Verificado en el código: incrementa una vez por cada registro de crudo
donde aparece el aviso, y un mismo aviso aparece en varias áreas de la
misma corrida. En agosto 2026 dio **5.910 avisos "vistos en >1
corrida"** con una sola corrida mensual hecha: los 5.910 salieron en
más de un área, no en más de un mes.

La columna longitudinal correcta es **`periodos_visto`**, que es un
conjunto de períodos y hoy vale `2026_08` para los 9.125 avisos. Para
contar corridas reales hay que usar la cantidad de períodos, no
`n_corridas_visto`. El nombre invita a un error de lectura serio en
cuanto haya dos meses; conviene renombrarlo a `n_observaciones` o
derivar la cuenta de `periodos_visto`.

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

### El join carrera_trabajando → programa propio

La clave del cruce es el **nombre de la carrera**, texto que escribe
trabajando.cl. Tres de los 528 traen espacios dobles y once traen
espacio final. Cualquier cruce por igualdad exacta funciona hasta que
una de las dos puntas gana o pierde un espacio —al abrir el CSV en una
planilla, al copiarlo entre máquinas— y ahí esas carreras
**desaparecen del análisis sin que nada avise**.

Por eso el cruce vive en un módulo, `homologacion.py`, y no se
reescribe en cada script:

```python
from homologacion import Homologacion
H = Homologacion.cargar('maestras/homologacion.csv')
H.destinos('Música  ')     # cruza igual que 'Música' o 'Música '
H.programas('Ingeniería')  # []  — es un campo, no tiene programa
```

**`clave()` normaliza espacios y mayúsculas**, y las tildes **no**:

```
espacios                528 nombres → 528 claves, 0 colisiones
espacios + minúsculas   528 nombres → 527 claves, 1 colisión
```

La única colisión es `Ingeniería Civil en Minas` / `Ingeniería civil en
minas` — la misma carrera escrita distinto, con destino, `tipo_relacion`,
`estado` y `confianza` idénticos. Se fundieron en una fila (111
menciones). Las tildes se conservan porque en castellano distinguen
palabras y ninguna colisión justificaba sacarlas.

Que dos grafías caigan en la misma clave con **destinos distintos** sí
sería un error: la clave dejaría de identificar una fila y `destinos()`
devolvería dos donde no hay un `multiple`. El validador lo marca ⛔ y
dice si el destino es el mismo (fundir) o no (decidir).

**`destinos()` devuelve una lista, no un valor.** Nueve carreras abren a
varios programas (`tipo_relacion = multiple`). Devolver el primero y
callar los otros inventaría una atribución única donde el autor decidió
que hay varias.

**`programas()` puede venir vacío y eso no es una falla.** Cuando el
aviso nombra un campo, un nivel, un cargo o nada, no hay programa —
7,1% de las menciones específicas. Forzarlas a uno es exactamente el
error que la homologación existe para evitar.

`validar.sh` mide la cobertura real cruzando contra `aviso_carrera.csv`:
92,9% llega a un programa, 7,1% está homologado sin programa, y lo que
quede sin fila de homologación sale como ⛔ — esas menciones sí se
pierden.

### `aviso_programa.csv` — dónde aterriza la homologación

Una tabla nueva, no una columna en las existentes. El grano cambia en
las dos direcciones —una carrera puede abrir a varios programas y dos
carreras pueden cerrar en uno—, así que colgarla de `aviso_carrera.csv`
obligaría a meter listas dentro de una celda, que es justo lo que §5.7
critica de v7.

**Grano: 1 fila por (aviso × destino).** Si un aviso declara
`Asistente Judicial` y `Técnico Jurídico`, pide **un** programa, no dos:
es una fila con `n_carreras_origen = 2`. Colapsar eso es el punto de la
tabla.

**Qué entra y qué no.** Solo `fuente == 'declarada'` —las filas
`keyword_only` son trazabilidad del término, no atribución (§5.6)— y
solo los destinos que existen. `nivel_formativo`, `solo_ocupacion` y
`no_informativo` **no producen fila**: el aviso no nombró ninguna
formación. Es el 1,4% de las menciones y siguen en `aviso_carrera.csv`.

**Los campos ISCED sí entran**, con `programa_propio` vacío. Dejarlos
afuera haría que un conteo por campo —el uso natural de la tabla— se
comiera el 5,7% de las menciones sin avisar. `tipo_entrada` separa los
dos casos en un predicado. Y las tres columnas ISCED están en **todas**
las filas, vengan de un programa o de un campo.

**`atribucion_multiple` es la marca que hay que mirar.** True cuando la
carrera de origen abría a varios destinos: el aviso nombró algo ambiguo
y esta fila es una de varias lecturas. Sumarlas como demanda
independiente infla el conteo. Lección 7.

Primera medición, sobre Derecho (342 avisos): 5.589 filas de
`aviso_carrera` → **2.534 de `aviso_programa`**, de las cuales 324
vienen de avisos específicos. En esas 324, 54 colapsan dos o más
carreras en un programa y 6 llevan `atribucion_multiple`.

La tabla se escribe solo si existe `maestras/homologacion.csv`. Si no
está, `consolidar.py` avisa en pantalla y sigue — import blando, como la
ruta A. Nunca falla en silencio.

### Filtros de genericidad

- `carreras_trabajando.n_avisos_especificos` — cuenta solo avisos con
  `n_carreras_declaradas <= UMBRAL_AVISO_GENERICO` (**30** desde agosto
  2026; antes 20). Es el orden correcto para priorizar homologación.
  Efecto medido en Humanidades: la cobertura del top 50 pasó de 11,7% a
  83,3%.

  **Por qué se subió a 30, y por qué ese argumento ya no vale.** Con dos
  áreas la distribución era bimodal con un hueco grande: máximo legítimo
  25, siguiente valor 504. Cualquier corte dentro del hueco daba el
  mismo resultado, pero 20 caía fuera y marcaba como genérico el aviso
  `6102956` (Universidad Mayor, 25 carreras), un concurso académico
  legítimamente multidisciplinario — el falso positivo de §5.8.

  **Con las 10 áreas el hueco se pobló** (§5.2): la distribución es
  continua de 0 a 100 y el único salto queda entre 100 y 504. Revisados
  los 29 avisos, ninguno es un concurso multidisciplinario, así que el
  corte no debe subir. Pero las plantillas de empleador aparecen entre
  20 y 49, a ambos lados de cualquier corte, y un concurso legítimo
  (Universidad Mayor) cae en el mismo rango: **el tamaño no separa los
  dos casos.** Queda en 30 por falta de algo mejor, sabiendo que es
  arbitrario y que afecta al 0,65% de los avisos.

- **`hash_carreras` + `n_avisos_mismo_conjunto`** (agosto 2026) — la
  señal que **no depende del umbral**. El hash identifica el conjunto
  declarado (normalizado y ordenado: mismo conjunto en distinto orden
  da el mismo hash) y el contador dice cuántos avisos lo comparten.

  Un conjunto repetido es un **perfil guardado del empleador**, no una
  decisión por vacante: Bresler sale con 10, Salazar Israel con 5,
  AMERICAR con 4. Un concurso multidisciplinario legítimo sale con 1,
  porque cada convocatoria trae su propia lista — así se separan los
  dos casos que el tamaño confunde (§5.2).

  Vacío cuando el aviso no declara carreras. No declarar nada no es
  compartir un conjunto, y agrupar los 3.703 avisos sin carreras bajo
  un mismo hash inventaría el grupo más grande de la tabla.

  Se cuenta sobre avisos deduplicados. Contarlo dentro del ciclo de
  observaciones lo inflaría tantas veces como áreas haya visto cada
  aviso — lección 3.

  **Contar la reutilización a secas no mide nada.** Primera medición
  (agosto 2026): 562 conjuntos repetidos en 3.593 avisos (39,4%), pero
  los mayores son **194 avisos de 22 empresas declarando UNA carrera**.
  Eso no es una plantilla, es una carrera frecuente. La primera versión
  del bloque 3 avisaba que "3.574 avisos cuentan como específicos y no
  lo son", que es falso.

  Lo que identifica al perfil guardado son dos condiciones juntas: que
  el conjunto pertenezca a **una sola empresa** y que sea **grande
  suficiente** para que el aviso deje de informar qué carrera busca. El
  bloque 3 lista las plantillas así definidas, ordenadas por tamaño, y
  avisa cuáles quedan bajo el umbral — esas sí cuentan como específicas
  sin serlo.

  El piso de tamaño del reporte (10) **no clasifica nada**: es un filtro
  de lectura para que la lista quepa en pantalla. La columna guarda el
  dato completo.

- `instituciones.n_avisos_especificos` — **usa el umbral de carreras
  como proxy y es imperfecto.** Un aviso con 19 carreras declaró 35 de
  56 instituciones y cuenta como específico. `aviso_institucion.csv`
  guarda `n_carreras_declaradas_aviso` para poder calibrar un umbral
  propio cuando haya volumen. Leer esta columna con reserva.

  (Hasta agosto 2026 este párrafo decía `n_instituciones_aviso`, una
  columna que nunca existió: el código siempre escribió el conteo de
  carreras. Lo encontró `diccionario.py` al cruzar glosas con datos
  reales, que es exactamente para lo que está.)

---

## 7. Estado actual y qué falta

### Corrido

**Las 10 áreas están capturadas con v9 y consolidadas** (16 agosto
2026). El detalle por área y el perfil del corpus están en §5.9.

| área | términos | avisos |
|---|---:|---:|
| Derecho | 1 | 342 |
| Humanidades | 3 | 37 |
| Agropecuaria | 9 | 186 |
| Arte y Arquitectura | 12 | 447 |
| Ciencias Sociales | 14 | 2.841 |
| Educación | 14 | 322 |
| Ciencias Básicas | 15 | 580 |
| Salud | 22 | 1.062 |
| Administración y Comercio | 28 | 6.044 |
| Tecnología | 81 | 5.883 |
| **únicos tras deduplicar** | | **9.125** |

Términos y avisos no van de la mano. Derecho rinde 342 avisos con un
solo término, casi diez veces Humanidades con un tercio de los
términos — pero ~82% es ruido (§5.8). **Volumen de avisos y volumen de
información no son lo mismo.**

De los datos v7 de Administración y Comercio queda un CSV y un JSON de
agosto 2026, fuera del repo. **No son convertibles a crudo v9**: son
campos ya derivados y les faltan `estadoOferta`, `idCompany`,
`instituciones`, `habilidades`, `ofertaConfidencial` y las `carreras`
declaradas. Ya no hacen falta —el área se corrió con v9 el mismo día—
pero conviene conservarlos: dos scrapers distintos sobre el mismo sitio
el mismo día permiten una validación cruzada que no se puede repetir.

### Pendientes

**1. La corrida de septiembre.** Ya no queda área por descubrir: lo que
falta es la **segunda observación**, que es lo que convierte el monitor
en longitudinal. Hoy hay 42 avisos de baja y las 42 son `cota_superior`;
ninguna duración medida. Un `./mensual.sh` en septiembre produce las
primeras `observada`.

**2. Homologación carreras trabajando → catálogo propio.** Es el cuello
de botella real y **no depende de correr más áreas**. La ruta A (§6) no
la reemplaza, porque va desde el término buscado y no desde lo que el
aviso declara.

**Hecha, fuera del repo, en agosto 2026** — y no contra SIES. El autor
construyó un **catálogo propio de 204 programas formativos**
(`programas_propios.csv`), cada uno respaldado por su genérica SIES
cuando existe, por su distribución de niveles en la oferta 2026, y por
sus tres códigos **ISCED-F 2013** (amplio, estrecho, detallado). Sobre
él mapeó los 528 nombres: 542 filas, `maestras/homologacion.csv`.

**El hallazgo de diseño es que el mapeo no es «carrera → programa».**
Un nombre de aviso puede nombrar cinco cosas distintas, y solo una es
un programa:

| `tipo_entrada` | qué nombra el aviso | carreras | menciones |
|---|---|---:|---:|
| `programa_propio` | un programa identificable | 431 | 92,9% |
| `campo_iscedf` | un campo de estudio, no un programa (`Ingeniería`, `Ingeniería Civil`) | 38 | 5,7% |
| `nivel_formativo` | solo un nivel, sin disciplina (`MBA`, `Magíster`) | 11 | 0,8% |
| `solo_ocupacion` | un cargo (`Paramédico`, `Matrón`) | 14 | 0,4% |
| `no_informativo` | nada (`Otra carrera`, `Intercambio`) | 34 | 0,2% |

Ignorar esa distinción es lo que produce el error clásico: `Ingeniería
Civil` son **773 menciones**, el nombre más frecuente de todo el corpus,
y no es una carrera — SIES no tiene «Ingeniería Civil» a secas y el
aviso no dice cuál. Forzarla a un programa inventa 773 atribuciones.
Como campo (ISCED 0788) es un dato honesto.

**Que un programa no tenga genérica SIES que lo respalde** —`Teología`,
`Oceanografía`, `Quiropraxia`, `Ingeniería Civil Hidráulica`— es un
atributo **del programa**, no del vínculo con el nombre del aviso. Vive
en `programas_propios.sin_generica_sies`, donde se escribe una vez, y no
repetido en cada fila que apunte ahí. SIES los mete en un cajón (`Otros
Profesionales de…`); la marca guarda esa ausencia en vez de esconderla.
Son 9 de 204.

**`tipo_relacion` quedó en cuatro valores** —vacío, `exacta`,
`equivalente`, `multiple`— y describe solo el vínculo con un programa.
`no_homologable_programa` se retiró: estaba determinada por
`tipo_entrada` (eran exactamente las 105 filas sin programa) y no
informaba nada.

**`Ingeniería Civil` salió del catálogo propio.** No tenía genérica
SIES, su ISCED era `0788` —interdisciplinario— y no recibía ninguna
carrera: era un campo disfrazado de programa. Con eso desaparece
también el único código ISCED inválido del catálogo, un `078` que no
existe en ISCED-F 2013.

**`validar_homologacion.py` revisa el archivo, no lo produce.** Separa
tres cosas: ⛔ lo que rompe el join o el vocabulario, ⚠ lo que necesita
ojo humano, y el informe de dónde está parado el trabajo.

```bash
./validar.sh
./validar.sh --adoptar-nombres-maestra   # y arregla los espacios
```

Los chequeos que ya encontraron algo real:

- **Espacios en el nombre.** El nombre es la clave del join y **once de
  los 528 traen espacios de más** (`'Música  '`, `'Servicios  Posventa
  Área Automotriz'`). `consolidar.py` copia `nombreCarrera` tal cual, sin
  tocar nada, así que esos espacios entran a la maestra y vuelven en cada
  corrida. Un cruce por igualdad exacta perdía esas carreras **sin
  avisar**: lección 10.

  **La solución no es corregir los archivos, es que el cruce no dependa
  del espacio** (§6, *El join*). Hoy es cosmético y el validador lo marca
  ⚠, no ⛔; `--adoptar-nombres-maestra` los empareja igual, por prolijidad.

  Vale la advertencia sobre esta misma sección: la primera medición decía
  que tres nombres diferían entre la homologación y la maestra. **Era mi
  copia de la maestra la que estaba mal** —había colapsado las corridas
  de espacios al viajar—, no el dato. Se detecta porque el encabezado
  decía `areas_observadas␣␣` y `consolidar.py` escribe `areas_observadas`.
  Una copia de un archivo no es el archivo.
- **Desajuste de nivel.** El nombre del aviso suele declarar el nivel
  («Técnico en…», «Ingeniería de Ejecución en…») y el programa destino
  declara en qué niveles se imparte. Cuando se contradicen, uno de los
  dos está mal: 10 filas, 187 menciones, la mayor
  `Ingeniería de Ejecución en Mecánica Automotriz` (130) apuntando a un
  programa **técnico**. Nueve se corrigieron.
- **Coherencia `tipo_entrada` ↔ destino**, destinos que existen en el
  catálogo y en ISCED-F, `multiple` contra el número de filas.

La heurística de nivel se ancla al **comienzo** del nombre a propósito:
buscando la palabra en cualquier posición, «Dibujo de Proyectos de
Arquitectura e Ingeniería» daba falso positivo.

**Lo que queda es la cola de revisión: 266 carreras, 19,2% de las
menciones.** El archivo trae `estado` (`validado`/`propuesto`) y
`confianza`, y el validador la ordena por volumen, que es la prioridad
correcta.

Lo de abajo es el andamio **anterior**, contra las genéricas SIES.
Quedó superado por el catálogo propio —que es más fino y trae ISCED—,
pero se conserva porque `homologar.py` sigue siendo lo que detecta
nombres nuevos cuando llegue la corrida de septiembre.

**El andamio ya existe y ya corrió** (agosto 2026): `homologar.py`
genera `maestras/homologacion_carreras.csv` a partir de la taxonomía
observada. Automatiza solo el match exacto normalizado y ordena el resto
por `n_avisos_especificos`, que es la prioridad correcta.

Estado sobre el corpus completo:

```
528 filas   123 resueltas por match exacto   405 pendientes
ya cubierto: ~51% de las menciones específicas
```

**La curva de esfuerzo es muy favorable**, porque la distribución tiene
cola larga. Revisando las pendientes en el orden en que el archivo ya
viene ordenado:

| filas revisadas | cobertura global |
|---:|---:|
| 25 | 76,8% |
| 50 | 84,9% |
| 100 | 92,3% |
| 200 | 98,2% |

O sea: **una sesión sobre 50 filas lleva la homologación del 51% al
85%.** Las 25 primeras son casi todas variantes de ingeniería y
administración (`Ingeniería Civil` 773 avisos, `Ingeniería en
Administración de Empresas` 463, `Ingeniería` 281).

Y como la taxonomía saturó en 528 (§5.9), este trabajo **no se va a
rehacer** cuando lleguen los meses siguientes: las filas nuevas van a
ser pocas y el archivo preserva lo escrito.

Es idempotente y preserva las columnas manuales, incluidas las que
inventes. La clave es compuesta `(carrera_trabajando, nivel_condicion)`,
así que un caso 1:N se resuelve duplicando la fila y poniendo
`universitaria` en una y `tecnica` en la otra. Verificado.

Genera además `sugerencia` y `score` por solapamiento de tokens.
**Nunca se aplican solas.** Y conviene mirarlas con desconfianza: a
"Ingeniería Civil" le sugiere "Ingeniería Civil Industrial" con score
0,67, que es exactamente la confusión contra la que advierte §5.5. Sirven
para ordenar la pantalla, no para decidir.

**`mirar.sh` es la herramienta de apoyo.** Dado un nombre, muestra los
avisos que lo declaran: cargos reales, empleadores, nivel académico y
—lo más útil— **con qué otras carreras aparece declarado**. Esa
co-declaración es evidencia de a qué familia pertenece el nombre; la
similitud de strings no lo es. Excluye los genéricos, que si no harían
aparecer las 504 como co-declaradas.

**`coocurrencia.sh` es la misma evidencia, precalculada y agregada.**
Escribe `<datos>/coocurrencia_programas.html`, un archivo autocontenido
que se abre con doble clic: sin terminal, sin servidor, sin internet, y
queda en Drive.

**La unidad es el programa propio, no `carrera_trabajando`** (18 agosto
2026). Cuando la unidad era el nombre del aviso, la página servía para
decidir la homologación —a qué familia pertenece un nombre— y ese
trabajo ya está hecho. Con el programa como unidad, `Ingeniería en
Computación e Informática` reúne los nombres que antes estaban
dispersos en `Ingeniería en Informática / Sistemas`, `Ingeniería en
Gestión e Informática` y otros: la co-ocurrencia deja de estar partida
por variantes de redacción y dice algo sobre **formaciones**.

Se filtra por tres cosas, y el orden importa: **área SIES** (10
valores), **campo estrecho ISCED-F** (25 de los 29 en uso) y **nivel
formativo del programa**.

El campo ISCED estrecho es el filtro fino, y su gracia es que **cruza
las áreas SIES**: `041 Business and administration` junta `Ingeniería
Comercial` (Adm. y Comercio), `Administración Pública` (Ciencias
Sociales) e `Ingeniería Civil Industrial` (Tecnología) — tres áreas, un
campo. Se eligió el estrecho y no el detallado porque el detallado son
64 códigos sobre 205 programas, con muchos de uno o dos: un desplegable
inservible. Los nombres van en inglés, que es como los publica UNESCO.

El nivel es el del **programa**, no `avisos.nivel_academico`, que es lo
que declara el empleador. Un programa se imparte en más de un nivel en
76 de 205 casos, así que sale en la lista de todos ellos y los conteos
por nivel no suman 205.

**`licenciatura` se pliega en `profesional_con_grado`** (decisión del
autor, 18 agosto 2026: la distinción no le sirve al análisis). El
pliegue vive en `homologacion.py` —`PLIEGUES`— y **no** en
`programas_propios.csv`: el catálogo guarda lo que dice la oferta SIES
2026, que son dos categorías, y reescribirlo borraría un dato real —que
el 14,9% de los programas de Trabajo Social son licenciatura pura— sin
poder volver atrás. Plegar en la lectura se deshace sacando una línea.

Cada programa trae dos rankings:

1. **con qué otros programas se pide** en el mismo aviso;
2. **qué nombres de `carrera_trabajando` se homologaron ahí**, con
   cuántos avisos aportó cada uno.

El segundo existe para no perder de vista de dónde sale cada número:
`Administración de Empresas e Ing. Asociadas` junta nueve nombres de
aviso, y conviene verlo antes de citar su total. El buscador entra por
los dos —uno se acuerda de «Analista Programador», no del programa— y
hay filtro por área SIES.

Lee `aviso_programa.csv`, así que **no vuelve a resolver el join**: eso
lo hizo `consolidar.py`. Si el archivo no está, dice qué correr.

Quedan afuera, y la página lo dice en el encabezado con la cifra: los
avisos genéricos, los campos ISCED —`Ingeniería` o `Diseño` no son un
programa, y ponerlos como una unidad más mezclaría un campo con una
carrera—, los niveles sueltos y los cargos.

Al final lista los programas del catálogo que **ningún aviso específico
pide**. No es ausencia de demanda: es ausencia en esta corrida.

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

**Implementado en `control.py` (bloque 5), con una salvedad.** El cálculo
automático no puede usar vocabulario curado a mano por término, así que
`precision_titulo` mide algo más estricto: si el término aparece
literalmente en el título, con match por prefijo para imitar al buscador.
Sobre Derecho da **2,9%** en vez del 14,3% medido a mano, porque a mano
se contaron también «abogado», «jurídico» y «legal», que ninguna regla
genérica puede inferir. `precision_carrera` sí coincide: 14,8% contra
14,0%.

O sea: el número automático es un **piso**, no la misma estadística. Sirve
para comparar términos entre sí, que es para lo que se usa. Lo que sigue
pendiente es persistir un `estado_termino`; hoy es un informe, no un
registro.

**Corrección (agosto 2026).** La primera versión pedía que coincidiera
**algún** token del término, y eso invalidaba todo término de más de una
palabra: como "ingeniería" es un token de "Ingeniería Naval", cualquier
aviso que declarara cualquier ingeniería contaba como afín, y el término
salía con 75,8% de precisión sobre 1.420 avisos. Los 60 términos que
empiezan en "Técnico en" tenían el mismo problema.

El bug no se veía en Derecho —una sola palabra, donde ambas versiones
dan lo mismo— que fue justo el caso contra el que se validó la métrica.
**Validar una métrica contra un solo caso, y encima el más simple, no la
valida.** Ahora exige todos los tokens.

**5. Memoria de `consolidar.py`.** Carga todos los crudos en RAM antes
de escribir. **Primera medición (agosto 2026): aguantó.** 10 archivos,
~142 MB de JSONL, 17.744 registros, en un MacBook y sin incidente.

Sigue siendo el punto que primero va a ceder, porque el costo crece con
`meses × áreas`: en marzo serán ~1 GB de crudo. La señal a vigilar es el
tiempo de consolidación, que hoy es de menos de un minuto. Cuando
moleste, streaming; no antes.

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
   Con las 10 áreas ese top 1 baja a 5,5% (§5.9): el sesgo es de área
   chica, no del corpus. **Una estadística de un área no es una
   estadística del monitor**, y conviene decir siempre cuál de las dos
   se está mirando.
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
   Corolario de agosto 2026: acumuló y **se detuvo en 528** (§5.9). Que
   una muestra no sea un censo no significa que el censo esté lejos;
   significa que hay que medir la saturación en vez de suponerla en
   cualquiera de las dos direcciones.
12. **Un campo controlado no es lo mismo que un campo clasificado.**
   `carreras` es una lista cerrada —0,4% de variantes al normalizar— y
   aun así no es una taxonomía: mezcla niveles, fusiona sinónimos y
   tiene `Ingeniería` a secas con 281 avisos. La pregunta útil no es
   "¿es texto libre?" sino "¿tiene un principio de clasificación?".
   De la primera respuesta depende si vale homologar; de la segunda,
   si se puede agregar sin homologar.
