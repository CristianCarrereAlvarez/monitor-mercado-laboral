"""
El join carrera_trabajando → programa propio
=============================================

Un solo lugar donde se define **cómo se cruza** la homologación con las
maestras. Todo lo que necesite resolver un nombre de carrera pasa por
acá; nadie vuelve a escribir el cruce a mano.

POR QUÉ ES UN MÓDULO Y NO UNA LÍNEA EN CADA SCRIPT
  La clave del join es el nombre de la carrera, un texto libre que
  escribe trabajando.cl. Tres de los 528 traen **espacios dobles** y
  once traen espacio final (`'Música  '`, `'Servicios  Posventa Área
  Automotriz'`). Un cruce por igualdad exacta funciona hasta que una de
  las dos puntas pierde o gana un espacio —al abrir el CSV en una
  planilla, al copiarlo entre máquinas— y ahí esas carreras
  **desaparecen del análisis sin que nada avise**. Es la lección 10.

  La respuesta no es corregir los archivos cada vez: es que el cruce
  nunca dependa del espacio. Con la clave de acá, los 528 nombres calzan
  aunque los espacios difieran.

QUÉ NORMALIZA, Y QUÉ NO
  **Solo espacios**: recorta las puntas y colapsa las corridas
  internas. No baja a minúsculas ni saca tildes, a propósito y medido:

      solo espacios              528 nombres → 528 claves, 0 colisiones
      + minúsculas + tildes      528 nombres → 527 claves, 1 colisión

  La colisión es `Ingeniería Civil en Minas` / `Ingeniería civil en
  minas`, que en la homologación son **dos filas** —van al mismo
  programa, pero son dos entradas de la lista de trabajando—. Plegarlas
  rompería la clave. Normalizar de menos deja pasar un error posible;
  normalizar de más crea uno seguro.

USO
    from homologacion import Homologacion
    H = Homologacion.cargar('maestras/homologacion.csv')
    for d in H.destinos('Música  '):
        print(d['tipo_entrada'], d['programa_propio'] or d['isced_cod'])

  `destinos()` devuelve **una lista**: nueve carreras abren a varios
  programas (`tipo_relacion = multiple`). Devolver el primero y callar
  los otros sería inventar una atribución única donde el autor decidió
  que hay varias.
"""

import csv, os, re, sys
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def clave(nombre):
    """La clave del join: el nombre sin espacios de más.

    Recorta las puntas y colapsa las corridas internas. Nada más — ver
    el encabezado del módulo para por qué no baja a minúsculas.
    """
    return re.sub(r'\s+', ' ', str(nombre or '')).strip()


class Homologacion:
    """La homologación cargada e indexada por clave de join."""

    def __init__(self, filas):
        self.filas = filas
        self._idx = defaultdict(list)
        for r in filas:
            self._idx[clave(r.get('carrera_trabajando'))].append(r)

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
        """Las filas de homologación de un nombre. Lista vacía si no
        está homologado; varias si `tipo_relacion = multiple`."""
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
        como vienen de `aviso_carrera.csv`) contra la homologación.

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
    assert clave('Ingeniería Civil en Minas') != clave('Ingeniería civil '
                                                       'en minas')
    print("  clave(): ok — colapsa espacios, no pliega mayúsculas")
