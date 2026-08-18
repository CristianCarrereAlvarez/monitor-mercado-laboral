"""
El join entrada_trabajando → programa propio
=============================================

Un solo lugar donde se define **cómo se cruza** la homologación con las
maestras. Todo lo que necesite resolver una entrada de trabajando pasa por
acá; nadie vuelve a escribir el cruce a mano.

POR QUÉ ES UN MÓDULO Y NO UNA LÍNEA EN CADA SCRIPT
  La clave del join es el nombre de la entrada, texto que
  escribe trabajando.cl. Tres de los 528 traen **espacios dobles** y
  once traen espacio final (`'Música  '`, `'Servicios  Posventa Área
  Automotriz'`). Un cruce por igualdad exacta funciona hasta que una de
  las dos puntas pierde o gana un espacio —al abrir el CSV en una
  planilla, al copiarlo entre máquinas— y ahí esas entradas
  **desaparecen del análisis sin que nada avise**. Es la lección 10.

  La respuesta no es corregir los archivos cada vez: es que el cruce
  nunca dependa del espacio. Con la clave de acá, los 528 nombres calzan
  aunque los espacios difieran.

QUÉ NORMALIZA, Y QUÉ NO
  **Espacios y mayúsculas.** Recorta las puntas, colapsa las corridas
  internas y baja a minúsculas. **Las tildes se conservan**: en
  castellano distinguen palabras, y sacarlas es normalizar de más sin
  ninguna colisión que lo justifique.

      espacios                528 nombres → 528 claves, 0 colisiones
      espacios + minúsculas   528 nombres → 527 claves, 1 colisión

  La única colisión es `Ingeniería Civil en Minas` / `Ingeniería civil
  en minas`: dos entradas de la lista de trabajando que son **la misma
  formación escrita distinto**, con destino, tipo_relacion, estado y
  confianza idénticos. Plegarlas es lo correcto, y por eso la
  homologación las trae fundidas en una sola fila.

  Que dos nombres caigan en la misma clave con **destinos distintos**
  sí sería un error, y el validador lo marca ⛔: la clave dejaría de
  identificar una fila y `destinos()` devolvería dos filas donde no hay
  un `multiple`.

USO
    from homologacion import Homologacion
    H = Homologacion.cargar('maestras/homologacion.csv')
    for d in H.destinos('Música  '):
        print(d['tipo_entrada'], d['programa_propio'] or d['isced_cod'])

  `destinos()` devuelve **una lista**: nueve entradas abren a varios
  programas (`tipo_relacion = multiple`). Devolver el primero y callar
  los otros sería inventar una atribución única donde el autor decidió
  que hay varias.
"""

import csv, os, re, sys
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def clave(nombre):
    """La clave del join: el nombre sin espacios de más ni mayúsculas.

    Recorta las puntas, colapsa las corridas internas y baja a
    minúsculas. Las tildes se conservan — ver el encabezado del módulo.
    """
    return re.sub(r'\s+', ' ', str(nombre or '')).strip().lower()


# El vocabulario de niveles del catálogo propio, con su glosa. Vive acá
# porque lo usan la página de co-ocurrencia y cualquier análisis por
# nivel; escrito dos veces, se desincroniza.
#
# OJO: NO es `avisos.nivel_academico`, que es el nivel que el empleador
# declara en el aviso. Este es el nivel en que el programa **se
# imparte**, según la oferta SIES 2026, y 76 de los 205 programas se
# imparten en más de uno.
NIVELES = {
    'tecnico':               ('TNS',          'Técnico de Nivel Superior'),
    'profesional':           ('Prof. s/grado', 'Profesional sin grado'),
    'profesional_con_grado': ('Prof. c/grado',
                              'Profesional con grado'),
    'posgrado_postitulo':    ('Posg.',
                              'Magíster, doctorado, especialidad, '
                              'postítulo o diplomado'),
}

# `licenciatura` se pliega en `profesional_con_grado` — decisión del
# autor, 18 agosto 2026: la distinción «licenciatura no conducente a
# título» no le sirve al análisis.
#
# Se pliega ACÁ y no en `programas_propios.csv` a propósito. El catálogo
# guarda lo que dice la oferta SIES 2026, que son dos categorías
# distintas; reescribirlo borraría un dato real —que el 14,9% de los
# programas de Trabajo Social son licenciatura pura— para siempre y sin
# poder volver atrás. Plegar en la lectura es reversible: se saca esta
# línea y el dato está.
PLIEGUES = {'licenciatura': 'profesional_con_grado'}

# Orden de menor a mayor. No es una escala de mérito: es el orden en que
# se leen en una lista.
ORDEN_NIVELES = ['tecnico', 'profesional', 'profesional_con_grado',
                 'posgrado_postitulo']


def plegar_nivel(n):
    """El nivel tal como se usa en el análisis. Ver PLIEGUES."""
    n = (n or '').strip()
    return PLIEGUES.get(n, n)


class Homologacion:
    """La homologación cargada e indexada por clave de join."""

    def __init__(self, filas):
        self.filas = filas
        self._idx = defaultdict(list)
        for r in filas:
            self._idx[clave(r.get('entrada_trabajando'))].append(r)

    # ── construcción ───────────────────────────────────────────────
    @classmethod
    def cargar(cls, ruta, obligatoria=True):
        """Lee el archivo. Con `obligatoria=False` devuelve None si no
        está, para que un script pueda seguir sin homologación en vez
        de morir — pero el que la usa tiene que **avisar en pantalla**,
        nunca seguir en silencio."""
        if not os.path.exists(ruta):
            if obligatoria:
                print(f"\n  ⛔  No existe la homologación: {ruta}\n")
                sys.exit(1)
            return None
        with open(ruta, encoding='utf-8-sig', newline='') as f:
            return cls(list(csv.DictReader(f)))

    # ── consulta ───────────────────────────────────────────────────
    def destinos(self, nombre):
        """Las filas de homologación de una entrada. Lista vacía si no
        está homologada; varias si `tipo_relacion = multiple`."""
        return self._idx.get(clave(nombre), [])

    def tipo_entrada(self, nombre):
        """Qué nombra el aviso: programa_propio, campo_iscedf,
        nivel_formativo, solo_ocupacion, no_informativo — o None si el
        nombre no está en la homologación."""
        d = self.destinos(nombre)
        return d[0].get('tipo_entrada') if d else None

    def programas(self, nombre):
        """Los programas propios a los que apunta el nombre. Vacío
        cuando el aviso nombra un campo, un nivel, un cargo o nada:
        esos casos **no tienen programa**, y forzarlos a uno es
        exactamente el error que la homologación evita."""
        return [d['programa_propio'] for d in self.destinos(nombre)
                if d.get('programa_propio', '').strip()]

    def __contains__(self, nombre):
        return clave(nombre) in self._idx

    def __len__(self):
        return len(self._idx)

    # ── diagnóstico del join ───────────────────────────────────────
    def cobertura(self, nombres):
        """Cruza una lista de nombres observados (con repetición, tal
        como vienen de `aviso_entrada.csv`) contra la homologación.

        Devuelve tres cosas, porque son tres problemas distintos:
          resueltas  — menciones que llegan a un programa propio
          sin_programa — homologadas, pero el destino no es un programa
                         (campo, nivel, cargo, nada). No es una falla.
          huerfanas  — nombres que no están en la homologación. Esto sí
                       es una falla: son menciones que se pierden.
        """
        res, sin_prog, huer = 0, 0, defaultdict(int)
        for nombre in nombres:
            d = self.destinos(nombre)
            if not d:
                huer[clave(nombre)] += 1
            elif any(x.get('programa_propio', '').strip() for x in d):
                res += 1
            else:
                sin_prog += 1
        return res, sin_prog, dict(huer)


if __name__ == "__main__":
    # Prueba de humo: la clave tiene que aguantar exactamente el caso
    # que motiva el módulo.
    assert clave('Música  ') == clave('Música ') == clave('Música')
    assert clave('Servicios  Posventa') == clave('Servicios Posventa')
    assert clave('Ingeniería Civil en Minas') == clave('Ingeniería civil '
                                                       'en minas')
    assert clave('Música') != clave('Musica')   # las tildes se conservan
    print("  clave(): ok — colapsa espacios y mayúsculas, conserva tildes")
