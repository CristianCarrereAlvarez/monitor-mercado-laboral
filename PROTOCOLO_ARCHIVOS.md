# PROTOCOLO_ARCHIVOS.md — cómo creamos archivos y carpetas

Protocolo de trabajo entre Cristián Carrère y Claude para nombrar y
ubicar archivos y carpetas en los proyectos. Escrito el 19 de agosto de
2026 a partir de una inspección del Drive, no de supuestos.

**Rige la misma regla que `CLAUDE.md`: cero tolerancia a información
inventada.** Cada convención de acá dice de dónde sale. Las que están
medidas se marcan **verificado**; las que yo propongo se marcan
**propuesta** y no se aplican hasta que las apruebes. Si al momento de
crear un archivo la evidencia no alcanza para decidir, **pregunto**.

---

## 0. Las tres reglas que ordenan todo lo demás

1. **Antes de crear, digo la ruta completa y el nombre exacto.** No
   creo nada "a ver si sirve". Un archivo mal puesto en Drive no se
   nota: no hay `git status` que lo delate.
2. **No renombro ni muevo lo que ya existe sin que lo pidas.** Puedo
   señalar que algo no cumple el protocolo; corregirlo es decisión
   tuya. Lo viejo no se migra al estándar nuevo por iniciativa mía.
3. **Cuando no hay convención observada, pregunto en vez de elegir.**
   Este documento marca explícitamente dónde no hay evidencia.

---

## 1. La fecha en el nombre

**Formato canónico** (decidido por el autor el 19/08/2026):

```
AAAA-MM-DD_Tipo_Asunto.ext
```

Ejemplos correctos:

```
2026-08-19_Minuta_DuocUC_Benchmark.docx
2026-08-18_Minuta_SOCOEPA.docx
2026-07-26_Minuta_Analisis_Censo_Agropecuario.docx
```

**La fecha nombra el hecho, no el archivo. Verificado.** En las minutas
de reunión la fecha del nombre es anterior a la de creación del archivo
—`2026-07-30_Minuta_Reunion_Pablo_Silva.docx` se creó el 02/08;
`2026-07-03 Minuta Reunión GORE.pdf` se creó el 07/07—, así que nombra
la reunión. En las minutas analíticas coincide con el día del análisis
(`2026-07-27_...` creada el 27/07). En los dos casos es la fecha del
hecho. **Nunca uso la fecha de hoy por defecto: pregunto de qué día es
el hecho si no lo sé.**

### La evidencia, y por qué había que decidir

Sobre los 31 archivos con "Minuta" en el nombre que encontré en tu
Drive:

| forma | archivos | dónde |
|---|---:|---|
| `AAAA-MM-DD` al inicio | **19** | Minutas Analiticas, Minutas CoDiseño |
| `DDMMAAAA` al final | 4 (2 documentos ×2 formatos) | Minutas Contraparte, `Minuta_SOCOEPA` |
| `AAAA_MM_DD` al final | 1 | `Minuta Implementación Política 2022_02_27` (2023) |
| sin fecha | 7 | Minutas Bilaterales, Informantes, sueltos |

Es decir: **había dos convenciones vivas, no una.** La mayoritaria es
`AAAA-MM-DD` al inicio, pero los archivos más recientes —17 y 18 de
agosto— usaban `DDMMAAAA` al final. Sin preguntar, cualquiera de las
dos que yo eligiera habría sido una invención mía disfrazada de
"reproducir tu formato".

Dos cosas juegan a favor de la elegida, y conviene dejarlas escritas:

- **Ordena solo.** El listado alfabético queda cronológico. Con
  `DDMMAAAA` al final, `18082026` y `17092026` se ordenan al revés.
- **Es la que ya usa tu código.** `mensual.sh` y `procesar.sh` escriben
  `mensual_2026-08-16_133810.log` y `procesar_2026-08-18_094934.log`.
  El proyecto ya tenía la convención adentro.

### El separador después de la fecha es `_`

De los 19 archivos con fecha al inicio, **12 usan `_` y 7 usan espacio**
(los `2026-07-24 Minuta Reunión GORE`). Se fija `_` porque es la
mayoría y porque un nombre sin espacios sobrevive a rutas, URLs y a
copiarlo entre máquinas.

### Sin tildes ni ñ en el nombre — **propuesta**

Tus propios nombres van en las dos direcciones: `2026-07-26_Minuta_
Analisis_Accion Colectiva` (sin tildes) contra `2026-07-03 Minuta
Reunión GORE` (con). Propongo **ASCII en nombres de archivo** —tildes
sí en el contenido y en las carpetas ya existentes—, porque una tilde
mal codificada al viajar entre macOS, Drive y Linux rompe el nombre y
el archivo aparece duplicado. Las carpetas fijas (`2. Diseño`,
`3. Operación`) **no se tocan**: renombrarlas rompería enlaces.

### Versiones — **propuesta**

Observado hoy: `_v2`, `_vf`, `v.1`, `v.2`, ` 1`, ` 2`. Propongo `_v2`,
`_v3` y **nunca `_vf`**: la versión final siempre termina teniendo un
`_vf2`. Si el archivo va a Drive con nombre de fecha, la versión ya
está en la fecha y el sufijo sobra.

### El PDF conserva el nombre del original — **verificado**

`Minuta_SOCOEPA_18082026.docx` y `.pdf` comparten el nombre exacto. Se
mantiene: exportar no cambia el nombre, solo la extensión.

---

## 2. La estructura de carpetas de un proyecto

**Verificado en 6 proyectos.** El esqueleto es:

```
AAAA Cliente. Descripción/
├── 1. Administrativo/     contrato, OC, declaraciones, CV, factura
├── 2. Diseño/             TDR, propuesta, metodología
├── 3. Operación/          el trabajo de campo y de análisis
└── 4. Entregables/        lo que se entrega a la contraparte
```

`4. Entregables` es el nombre canónico (decisión del autor, 19/08/2026);
aparece también como `4. Informes`, que queda como variante histórica y
no se replica.

**El número es parte del nombre, y no es decorativo:** ordena las
carpetas en el orden del ciclo del proyecto, que no es el alfabético.

### Qué tan "casi siempre" es — la evidencia completa

| proyecto | 1 | 2 | 3 | 4 |
|---|:-:|:-:|:-:|:-:|
| 2026 DuocUC. Benchmark Análisis Mercado | ✓ | ✓ | ✓ | Entregables |
| 2026 Aproval. Diseño de Proyecto | ✓ | ✓ | ✓ | Entregables |
| 2026 UAH | ✓ | ✓ | ✓ | — |
| 2025 ENAC | ✓ | ✓ | — | — |
| 2026 Aproval. Manual Prácticas Profesionales | — | ✓ | ✓ | — |
| 2026 Apoyo Alejandra | — | ✓ | ✓ | Informes |
| 2026 Mineduc Diálogos | — | — | — | — |

**Ninguno de los siete tiene una carpeta que no sea del esqueleto**,
salvo `3. Postulación PNUD` en Apoyo Alejandra —que duplica el número 3
y es un caso aparte— y `2026 Mineduc Diálogos`, que no tiene estructura
y guarda todo suelto en la raíz.

O sea: **las excepciones son por ausencia, no por invención.** Un
proyecto puede no haber llegado a la etapa 3 o 4 todavía. Ninguno se
inventó una etapa 5.

**Regla derivada:** creo la carpeta que falta cuando llega su primer
archivo, no antes. Un `4. Entregables` vacío en un proyecto que recién
empieza es ruido. Y **si un archivo no cae en ninguna de las cuatro, es
señal de que no entendí qué es: pregunto antes de inventar una quinta.**

### Dentro de `3. Operación`

Acá sí hay variación real y **no hay convención que reproducir**. Lo
observado:

```
2026 Aproval / 3. Operación/     2026 DuocUC / 3. Operación/
├── Minutas/                     ├── Minutas Contraparte/
│   ├── Minutas Analiticas/      └── (instrumentos sueltos)
│   ├── Minutas Bilaterales/
│   ├── Minutas CoDiseño/
│   └── Minutas Informantes/
├── Documentos/
├── Bases Censo/
├── Teoría del Cambio/
├── Operacionalización/
├── Posibles Ejecutores/
├── Basurero/
└── Actores.xlsx
```

Lo estable entre los dos: **hay una carpeta de minutas, y se subdivide
por tipo de interlocutor cuando el volumen lo pide** (analíticas,
bilaterales, co-diseño, informantes, contraparte). El resto son
carpetas temáticas del proyecto, que no se pueden anticipar.

**Regla:** una minuta va a la subcarpeta de su tipo. Si no existe la
subcarpeta y hay menos de tres minutas de ese tipo, va directo a
`Minutas/` y no abro carpeta nueva.

### El nombre del proyecto

**Verificado**, con dos formas conviviendo:

```
AAAA Cliente. Descripción     2026 DuocUC. Benchmark Análisis Mercado
                              2026 Aproval. Manual Prácticas Profesionales
                              2026 SOCOEPA. Vinculación con Stakeholders
AAAA Cliente                  2026 UAH, 2025 ENAC, 2027 Acuícolas
```

La segunda forma aparece en proyectos sin concretar o de una sola
línea de trabajo. **Propuesta:** usar siempre `AAAA Cliente.
Descripción` cuando el cliente tenga o pueda tener más de un proyecto
—`2026 Aproval` solo sería ambiguo, hay dos— y `AAAA Cliente` cuando
no. El año es el de inicio del proyecto: hay carpetas `2027` creadas en
2026.

### Sin espacios dobles ni espacio final — **regla dura**

Encontré `2026 Aproval. Diseño de Proyecto ` y `Operacionalización `,
las dos con espacio al final. Es exactamente el problema que ya te
costó caro en el monitor (`CLAUDE.md` §6, *El join*): once nombres de
carrera con espacios de más, y un cruce por igualdad exacta que perdía
esas filas **sin avisar**.

En Drive el costo es otro pero del mismo tipo: buscar la carpeta por
nombre no la encuentra, y dos carpetas que se ven idénticas son
distintas.

**Yo nunca genero un nombre con espacio doble o final.** Los que ya
existen los dejo como están y te los señalo.

---

## 3. Dónde va cada cosa

Ruta por defecto según qué es el archivo. Si dudo entre dos, pregunto.

| qué es | dónde va |
|---|---|
| contrato, OC, declaración jurada, CV, factura | `1. Administrativo/` |
| TDR, propuesta, carta Gantt, metodología | `2. Diseño/` |
| minuta de reunión, de entrevista, analítica | `3. Operación/Minutas/<tipo>/` |
| instrumento (pauta, ficha, matriz, protocolo) | `3. Operación/` |
| base de datos, transcripción, audio | `3. Operación/<carpeta temática>/` |
| informe, presentación, producto comprometido | `4. Entregables/` |
| descartado o reemplazado | `Basurero/` (ver §4) |

**Los instrumentos siguen su propio patrón, verificado** en las cinco
piezas que creaste el 19/08 en DuocUC:

```
Objeto — Proyecto
Pautas de entrevista — Benchmark de oferta formativa
Matriz de sistematización y variables por dimensión — Benchmark de oferta formativa
Protocolo de contacto, invitación, consentimiento y devolución — Benchmark de oferta formativa
```

Raya larga `—`, sin fecha, en Google Docs nativo. Tiene sentido: un
instrumento es un documento vivo que se edita, no un registro fechado.
**Se reproduce tal cual, y no le pongo fecha.**

**Regla de formato derivada:** lo que se **edita** vive en Google
nativo (Docs, Sheets); lo que **registra un momento** vive como archivo
fechado (`.docx`, y `.pdf` cuando se comparte).

---

## 4. Nada se borra: `Basurero/`

Cuando un archivo queda obsoleto o reemplazado, **se mueve a
`Basurero/` dentro de su carpeta**. No se borra y no se deja
acumulando versiones al lado del vigente. La carpeta ya existe en
`2026 Aproval / 3. Operación / Basurero`; donde no exista, la creo al
mover el primer archivo.

Es la misma lógica del crudo en el monitor (`CLAUDE.md` §2): lo que se
guarda entero se puede reprocesar; lo que se borró, no. Y sigue siendo
tu decisión, no mía: **muevo a `Basurero/` cuando me lo pides o cuando
yo mismo reemplazo un archivo que generé.** Un archivo tuyo no se mueve
por iniciativa mía.

---

## 5. Lo que hago antes de crear cada archivo

Checklist corto, en orden:

1. **¿Ya existe?** Busco el nombre en la carpeta destino antes de
   escribir. Duplicar una minuta con otro nombre es peor que no tenerla.
2. **¿Cuál es la fecha del hecho?** Si no la sé, la pregunto. No uso
   hoy por defecto.
3. **Digo ruta + nombre completos** y espero, salvo que ya me hayas
   autorizado esa creación específica.
4. **Nada de espacios dobles ni finales.**
5. **Si creé el archivo en el contenedor** (no directamente en Drive),
   te digo dónde quedó y qué falta para que llegue a Drive. Un archivo
   en `/tmp` de una sesión remota se pierde al cerrar; es la misma
   trampa que el `crudo/` en el clon efímero de Colab
   (`CLAUDE.md` §3).

---

## 6. Decisiones que faltan

Marcadas para que no queden como huecos silenciosos.

1. **Nombres de personas en el nombre del archivo.** Hoy existen
   `2026-07-30_Minuta_Reunion_Pablo_Silva.docx` y transcripciones
   `Entrevista Paula Naranjo`. Choca con la postura de `CLAUDE.md` §1
   —agregado sí, individualizado no— aunque ahí se refiere a avisos y
   empresas, no a informantes de un estudio. **No sé si querés la misma
   regla acá.** Mientras no lo decidas, reproduzco lo que ya hacés:
   nombre de la persona en minutas bilaterales y de entrevista.
2. **Dónde vive un proyecto nuevo.** Vi dos raíces distintas con
   proyectos `2026 ...`: una tiene `Actuales/`, `Sin Concretar/`,
   `Fondos/`, `SMLab/`; la otra tiene los proyectos colgando directo.
   **La API no me da el nombre de las unidades**, solo los IDs, así que
   no puedo decirte cuál es "Operaciones". Falta la regla de cuándo un
   proyecto pasa de `Sin Concretar/` a `Actuales/`, y quién lo mueve.
3. **Qué pasa cuando termina un proyecto.** No vi carpeta de cerrados
   ni archivados. `2025 ENAC` sigue en `Sin Concretar/`.
4. **Los siete proyectos que no inspeccioné** —`2027 GORE Lechero`,
   `2027 Acuícolas`, `2026 Mineduc. AtlasTP`, `2026 Santo Tomás.
   Benchmark Internacional`, `2026 SOCOEPA. Vinculación con
   Stakeholders`— pueden traer excepciones que este documento no
   recoge. La tabla de §2 es una muestra de 7 sobre ~12, no un censo.
   (Lección 11 de `CLAUDE.md`: medir la saturación en vez de suponerla.)

---

## 7. Cómo se mantiene este documento

Se actualiza cuando **cambia una convención o aparece una excepción
nueva**, no cuando se crea un archivo más. Si al aplicarlo me encuentro
con un caso que no cubre, lo digo en el momento y lo sumo acá con su
evidencia — no lo resuelvo en silencio y sigo.

**Si querés que esto se aplique sin tener que recordármelo**, el paso
siguiente es convertirlo en un *skill* de Claude Code, que se carga
solo cuando la tarea es crear archivos o carpetas. No lo hice porque no
lo pediste; es un rato de trabajo y se hace sobre este mismo texto.
