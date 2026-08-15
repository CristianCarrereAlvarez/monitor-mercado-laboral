"""
Diccionario completo de carreras SIES 2026 — Pregrado únicamente
Fuente: Oferta Académica 2026 SIES (05-06-2026)

Estructura:
  CARRERAS_POR_AREA[área] = {término_búsqueda: carrera_genérica_sies}

  término_búsqueda    → lo que se escribe en trabajando.cl
  carrera_genérica_sies → nombre oficial del SIES (para trazabilidad)

Posgrado excluido: Doctorado, Magíster, Postítulo
Tecnología: 92 carreras — es el área más grande por lejos.
            Considera dividirla en subscrapes si el tiempo de ejecución
            es muy alto (92 búsquedas × N páginas).

Uso en el scraper:
  from carreras_sies_2026 import CARRERAS_POR_AREA

  # Escoger un área:
  CARRERAS = CARRERAS_POR_AREA["Agropecuaria"]

  # O correr todas:
  for area, carreras in CARRERAS_POR_AREA.items():
      CARRERAS = carreras
      # ... lanzar scraper para esa área
"""

CARRERAS_POR_AREA = {

    # ══════════════════════════════════════════════════════
    # Administración y Comercio — 35 carreras
    # ══════════════════════════════════════════════════════
    "Administración y Comercio": {
        "Administración Gastronómica":                          "Administración Gastronómica",
        "Administración Turística y Hotelera":                  "Administración Turística y Hotelera",
        "Administración de Empresas e Ing. Asociadas":          "Administración de Empresas e Ing. Asociadas",
        "Bachillerato en Administración y Comercio":            "Bachillerato y/o Licenciatura en Administración y Comercio",
        "Contador Auditor":                                     "Contador Auditor",
        "Ingeniería Comercial":                                 "Ingeniería Comercial",
        "Ingeniería en Comercio Exterior":                      "Ingeniería en Comercio Exterior",
        "Ingeniería en Control de Gestión":                     "Ingeniería en Control de Gestión",
        "Ingeniería en Finanzas":                               "Ingeniería en Finanzas",
        "Ingeniería en Gestión y Control de Calidad":           "Ingeniería en Gestión y Control de Calidad",
        "Ingeniería en Logística":                              "Ingeniería en Logística",
        "Ingeniería en Marketing":                              "Ingeniería en Marketing",
        "Ingeniería en Recursos Humanos":                       "Ingeniería en Recursos Humanos",
        "Ingeniería en Seguridad Privada":                      "Ingeniería en Seguridad Privada",
        "Secretariado Bilingüe":                                "Secretariado Bilingüe",
        "Secretariado Computacional":                           "Secretariado Computacional",
        "Secretariado Ejecutivo":                               "Secretariado Ejecutivo",
        "Técnico Agente o Visitador Médico":                    "Técnico Agente o Visitador Médico",
        "Técnico en Administración Financiera":                 "Técnico en Administración Financiera y Finanzas",
        "Técnico en Administración de Empresas":                "Técnico en Administración de Empresas",
        "Técnico en Administración de Recursos Humanos":        "Técnico en Administración de Recursos Humanos y Personal",
        "Técnico en Administración de Ventas":                  "Técnico en Administración de Ventas",
        "Técnico en Administración en Marketing":               "Técnico en Administración en Marketing",
        "Técnico en Comercio Exterior":                         "Técnico en Comercio Exterior",
        "Técnico en Contabilidad Computacional":                "Técnico en Contabilidad Computacional",
        "Técnico en Contabilidad General":                      "Técnico en Contabilidad General",
        "Técnico en Contabilidad Tributaria":                   "Técnico en Contabilidad Tributaria",
        "Técnico en Gastronomía":                               "Técnico en Gastronomía y Cocina",
        "Técnico en Gestión y Control de Calidad":              "Técnico en Gestión y Control de Calidad",
        "Técnico en Logística":                                 "Técnico en Logística",
        "Técnico en Producción de Eventos":                     "Técnico en Producción de Eventos",
        "Técnico en Seguridad Privada":                         "Técnico en Seguridad Privada",
        "Técnico en Turismo y Hotelería":                       "Técnico en Turismo y Hotelería",
    },

    # ══════════════════════════════════════════════════════
    # Agropecuaria — 10 carreras
    # ══════════════════════════════════════════════════════
    "Agropecuaria": {
        "Agronomía":                    "Agronomía",
        "Ingeniería Agrícola":          "Ingeniería Agrícola",
        "Ingeniería Forestal":          "Ingeniería Forestal",
        "Ejecución Forestal":           "Ingeniería de Ejecución Forestal",
        "Acuicultura":                  "Ingeniería en Acuicultura y Pesca",
        "Medicina Veterinaria":         "Medicina Veterinaria",
        "Técnico Agropecuario":         "Técnico Agropecuario",
        "Técnico Veterinario":          "Técnico Veterinario",
        "Técnico Acuicultura":          "Técnico en Acuicultura y Pesca",
        "Enología":                     "Técnico en Vitivinicultura y/o Enología",
    },

    # ══════════════════════════════════════════════════════
    # Arte y Arquitectura — 27 carreras
    # ══════════════════════════════════════════════════════
    "Arte y Arquitectura": {
        "Actuación y Teatro":                       "Actuación y Teatro",
        "Animación Digital":                        "Animación Digital",
        "Arquitectura":                             "Arquitectura",
        "Artes":                                    "Artes y Licenciatura en Artes",
        "Comunicación Audiovisual":                 "Comunicación Audiovisual y/o Multimedia",
        "Diseño":                                   "Diseño",
        "Diseño Gráfico":                           "Diseño Gráfico",
        "Diseño Teatral":                           "Diseño Teatral",
        "Diseño de Ambientes e Interiores":         "Diseño de Ambientes e Interiores",
        "Diseño de Vestuario":                      "Diseño de Vestuario",
        "Fotografía":                               "Fotografía",
        "Música":                                   "Música, Canto o Danza",
        "Paisajismo":                               "Paisajismo",
        "Realizador de Cine y Televisión":          "Realizador de Cine y Televisión",
        "Técnico en Ambientes e Interiores":        "Técnico en Ambientes e Interiores",
        "Técnico en Comunicación Audiovisual":      "Técnico en Comunicación Audiovisual",
        "Técnico en Dibujo Arquitectónico":         "Técnico en Dibujo Arquitectónico",
        "Técnico en Diseño Gráfico":                "Técnico en Diseño Gráfico",
        "Técnico en Diseño de Vestuario":           "Técnico en Diseño de Vestuario",
        "Técnico en Diseño de Áreas Verdes":        "Técnico en Diseño de Áreas Verdes y Paisajismo",
        "Técnico en Fotografía":                    "Técnico en Fotografía",
        "Técnico en Peluquería y Estética":         "Técnico en Peluquería y Estética",
        "Técnico en Producción Gráfica":            "Técnico en Producción Gráfica y Multimedia",
        "Técnico en Producción de Videojuegos":     "Técnico en Producción de Videojuegos",
        "Técnico en Teatro":                        "Técnico en Teatro",
    },

    # ══════════════════════════════════════════════════════
    # Ciencias Básicas — 20 carreras
    # ══════════════════════════════════════════════════════
    "Ciencias Básicas": {
        "Analista Químico":                         "Analista Químico",
        "Biología":                                 "Biología",
        "Biología Marina":                          "Biología Marina y Ecología Marina",
        "Bioquímica":                               "Bioquímica",
        "Física y Astronomía":                      "Física y Astronomía",
        "Geología":                                 "Geología",
        "Ingeniería Civil Matemática":              "Ingeniería Civil Matemática y Estadística",
        "Ingeniería Civil en Geomática":            "Ingeniería Civil en Geomática y Geomensura",
        "Ingeniería en Geomensura":                 "Ingeniería en Geomensura y Cartografía",
        "Ingeniería en Matemática":                 "Ingeniería en Matemática y Estadística",
        "Matemática":                               "Matemática y/o Estadística",
        "Química Ambiental":                        "Química Ambiental",
        "Química":                                  "Química, Licenciado en Química",
        "Técnico en Análisis de Datos":             "Técnico en Análisis de Datos",
        "Técnico en Geología":                      "Técnico en Geología",
        "Técnico en Geominería":                    "Técnico en Geominería",
        "Técnico en Química":                       "Técnico en Química (Análisis e Industrial)",
    },

    # ══════════════════════════════════════════════════════
    # Ciencias Sociales — 24 carreras
    # ══════════════════════════════════════════════════════
    "Ciencias Sociales": {
        "Administración Pública":                   "Administración Pública",
        "Antropología":                             "Antropología",
        "Arqueología":                              "Arqueología",
        "Ciencias Políticas":                       "Ciencias Políticas",
        "Comunicación Social":                      "Comunicación Social",
        "Geografía":                                "Geografía",
        "Historia":                                 "Historia",
        "Ingeniería en Gestión Pública":            "Ingeniería en Gestión Pública",
        "Orientación Familiar":                     "Orientación Familiar y Relaciones Humanas",
        "Periodismo":                               "Periodismo",
        "Psicología":                               "Psicología",
        "Publicidad":                               "Publicidad",
        "Relaciones Públicas":                      "Relaciones Públicas",
        "Sociología":                               "Sociología",
        "Trabajo Social":                           "Trabajo Social",
        "Técnico en Administración Pública":        "Técnico en Administración Pública o Municipal",
        "Técnico en Comunicación Social":           "Técnico en Comunicación Social",
        "Técnico en Prevención y Rehabilitación":   "Técnico en Prevención y Rehabilitación",
        "Técnico en Publicidad":                    "Técnico en Publicidad",
        "Técnico en Relaciones Públicas":           "Técnico en Relaciones Públicas",
        "Técnico en Servicio Social":               "Técnico en Servicio Social",
    },

    # ══════════════════════════════════════════════════════
    # Derecho — 4 carreras
    # ══════════════════════════════════════════════════════
    "Derecho": {
        "Criminalística":   "Criminalística",
        "Derecho":          "Derecho",
        "Técnico Jurídico": "Técnico Jurídico",
    },

    # ══════════════════════════════════════════════════════
    # Educación — 22 carreras
    # ══════════════════════════════════════════════════════
    "Educación": {
        "Pedagogía en Artes y Música":              "Pedagogía en Artes y Música",
        "Pedagogía en Ciencias":                    "Pedagogía en Ciencias",
        "Pedagogía en Educación Básica":            "Pedagogía en Educación Básica",
        "Pedagogía en Educación Diferencial":       "Pedagogía en Educación Diferencial",
        "Pedagogía en Educación Física":            "Pedagogía en Educación Física",
        "Pedagogía en Educación Media":             "Pedagogía en Educación Media",
        "Pedagogía en Educación Tecnológica":       "Pedagogía en Educación Tecnológica",
        "Pedagogía en Educación Técnico Profesional": "Pedagogía en Educación Técnico Profesional",
        "Pedagogía en Educación de Párvulos":       "Pedagogía en Educación de Párvulos",
        "Pedagogía en Filosofía y Religión":        "Pedagogía en Filosofía y Religión",
        "Pedagogía en Historia":                    "Pedagogía en Historia, Geografía y Ciencias Sociales",
        "Pedagogía en Idiomas":                     "Pedagogía en Idiomas",
        "Pedagogía en Lenguaje":                    "Pedagogía en Lenguaje, Comunicación y/o Castellano",
        "Pedagogía en Matemáticas":                 "Pedagogía en Matemáticas y Computación",
        "Programas de Formación Pedagógica":        "Programas de Formación Pedagógica",
        "Psicopedagogía":                           "Psicopedagogía",
        "Técnico Asistente del Educador Diferencial": "Técnico Asistente del Educador Diferencial",
        "Técnico Asistente del Educador de Párvulos": "Técnico Asistente del Educador de Párvulos",
        "Técnico en Deporte":                       "Técnico en Deporte, Recreación y Preparación Física",
    },

    # ══════════════════════════════════════════════════════
    # Humanidades — 9 carreras
    # ══════════════════════════════════════════════════════
    "Humanidades": {
        "Bibliotecología":                              "Bibliotecología",
        "Filosofía":                                    "Filosofía",
        "Licenciatura en Letras":                       "Licenciatura en Letras y Literatura",
        "Traducción e Interpretación":                  "Traducción e Interpretación",
        "Técnico en Bibliotecas":                       "Técnico en Bibliotecas y Centros de Documentación",
        "Técnico en Traducción e Interpretariado":      "Técnico en Traducción e Interpretariado",
    },

    # ══════════════════════════════════════════════════════
    # Salud — 25 carreras
    # ══════════════════════════════════════════════════════
    "Salud": {
        "Enfermería":                               "Enfermería",
        "Fonoaudiología":                           "Fonoaudiología",
        "Kinesiología":                             "Kinesiología",
        "Medicina":                                 "Medicina",
        "Naturopatía":                              "Naturopatía",
        "Nutrición y Dietética":                    "Nutrición y Dietética",
        "Obstetricia":                              "Obstetricia y Puericultura",
        "Odontología":                              "Odontología",
        "Química y Farmacia":                       "Química y Farmacia",
        "Tecnología Médica":                        "Tecnología Médica",
        "Terapia Ocupacional":                      "Terapia Ocupacional",
        "Técnico Dental":                           "Técnico Dental y Asistente de Odontología",
        "Técnico Laboratorista Dental":             "Técnico Laboratorista Dental",
        "Técnico en Enfermería":                    "Técnico en Enfermería",
        "Técnico en Farmacia":                      "Técnico en Farmacia",
        "Técnico en Laboratorio Clínico":           "Técnico en Laboratorio Clínico",
        "Técnico en Masoterapia":                   "Técnico en Masoterapia",
        "Técnico en Nutrición":                     "Técnico en Nutrición y Dietética",
        "Técnico en Podología":                     "Técnico en Podología",
        "Técnico en Radiología":                    "Técnico en Radiología y Radioterapia",
        "Técnico en Terapias Naturales":            "Técnico en Terapias Naturales y Naturopatía",
        "Técnico en Óptica":                        "Técnico en Óptica",
    },

    # ══════════════════════════════════════════════════════
    # Tecnología — 92 carreras
    # NOTA: área más grande. Si el tiempo de ejecución es muy alto,
    # considera dividirla en subscrapes temáticos (ej. Civil, Informática,
    # Mecánica, Minería) usando subconjuntos del diccionario.
    # ══════════════════════════════════════════════════════
    "Tecnología": {
        "Biotecnología":                            "Biotecnología",
        "Construcción Civil":                       "Construcción Civil",
        "Diseño Industrial":                        "Diseño Industrial",
        "Ingeniería Agroindustrial":                "Ingeniería Agroindustrial",
        "Ingeniería Civil Agrícola":                "Ingeniería Civil Agrícola",
        "Ingeniería Civil Ambiental":               "Ingeniería Civil Ambiental",
        "Ingeniería Civil Bioquímica":              "Ingeniería Civil Bioquímica",
        "Ingeniería Civil Electrónica":             "Ingeniería Civil Electrónica",
        "Ingeniería Civil Eléctrica":               "Ingeniería Civil Eléctrica",
        "Ingeniería Civil Industrial":              "Ingeniería Civil Industrial",
        "Ingeniería Civil Mecánica":                "Ingeniería Civil Mecánica",
        "Ingeniería Civil Metalúrgica":             "Ingeniería Civil Metalúrgica",
        "Ingeniería Civil Química":                 "Ingeniería Civil Química",
        "Ingeniería Civil en Biomédica":            "Ingeniería Civil en Biomédica",
        "Ingeniería Civil en Biotecnología":        "Ingeniería Civil en Biotecnología y/o Bioingeniería",
        "Ingeniería Civil en Computación":          "Ingeniería Civil en Computación e Informática",
        "Ingeniería Civil en Energía":              "Ingeniería Civil en Energía",
        "Ingeniería Civil en Geografía":            "Ingeniería Civil en Geografía",
        "Ingeniería Civil en Industrias Forestales": "Ingeniería Civil en Industrias Forestales",
        "Ingeniería Civil en Materiales":           "Ingeniería Civil en Materiales",
        "Ingeniería Civil en Minas":                "Ingeniería Civil en Minas",
        "Ingeniería Civil en Obras Civiles":        "Ingeniería Civil en Obras Civiles",
        "Ingeniería Civil en Sonido":               "Ingeniería Civil en Sonido y Acústica",
        "Ingeniería Civil en Telemática":           "Ingeniería Civil en Telemática",
        "Ingeniería Civil":                         "Ingeniería Civil, plan común y licenciatura en Ciencias de la Ingeniería",
        "Ingeniería Industrial":                    "Ingeniería Industrial",
        "Ingeniería Marina":                        "Ingeniería Marina y Marítimo Portuaria",
        "Ingeniería Mecánica":                      "Ingeniería Mecánica",
        "Ingeniería Naval":                         "Ingeniería Naval",
        "Ingeniería en Alimentos":                  "Ingeniería en Alimentos",
        "Ingeniería en Automatización":             "Ingeniería en Automatización, Instrumentación y Control",
        "Ingeniería en Biotecnología":              "Ingeniería en Biotecnología y Bioingeniería",
        "Ingeniería en Computación e Informática":  "Ingeniería en Computación e Informática",
        "Ingeniería en Conectividad y Redes":       "Ingeniería en Conectividad y Redes",
        "Ingeniería en Construcción":               "Ingeniería en Construcción",
        "Ingeniería en Electricidad":               "Ingeniería en Electricidad",
        "Ingeniería en Electrónica":                "Ingeniería en Electrónica",
        "Ingeniería en Energía":                    "Ingeniería en Energía",
        "Ingeniería en Geomensura":                 "Ingeniería en Geomensura y Cartografía",
        "Ingeniería en Industria de la Madera":     "Ingeniería en Industria de la Madera",
        "Ingeniería en Mecatrónica":                "Ingeniería en Mecatrónica",
        "Ingeniería en Mecánica Automotriz":        "Ingeniería en Mecánica Automotriz",
        "Ingeniería en Medio Ambiente":             "Ingeniería en Medio Ambiente",
        "Ingeniería en Metalurgia":                 "Ingeniería en Metalurgia",
        "Ingeniería en Minas":                      "Ingeniería en Minas",
        "Ingeniería en Prevención de Riesgos":      "Ingeniería en Prevención de Riesgos",
        "Ingeniería en Proyectos Estructurales":    "Ingeniería en Proyectos Estructurales",
        "Ingeniería en Química":                    "Ingeniería en Química",
        "Ingeniería en Recursos Renovables":        "Ingeniería en Recursos Renovables",
        "Ingeniería en Refrigeración":              "Ingeniería en Refrigeración y Climatización",
        "Ingeniería en Sonido":                     "Ingeniería en Sonido",
        "Ingeniería en Telecomunicaciones":         "Ingeniería en Telecomunicaciones",
        "Ingeniería en Transporte y Tránsito":      "Ingeniería en Transporte y Tránsito",
        "Química Industrial":                       "Química Industrial",
        "Técnico en Administración de Redes":       "Técnico en Administración de Redes y Soporte",
        "Técnico en Agroindustria":                 "Técnico en Agroindustria",
        "Técnico en Alimentos":                     "Técnico en Alimentos",
        "Técnico en Análisis de Sistemas":          "Técnico en Análisis de Sistemas",
        "Técnico en Biotecnología Industrial":      "Técnico en Biotecnología Industrial",
        "Técnico en Computación e Informática":     "Técnico en Computación e Informática",
        "Técnico en Construcción y Obras Civiles":  "Técnico en Construcción y Obras Civiles",
        "Técnico en Dibujo Técnico":                "Técnico en Dibujo Técnico",
        "Técnico en Diseño Industrial":             "Técnico en Diseño Industrial",
        "Técnico en Electricidad Industrial":       "Técnico en Electricidad y Electricidad Industrial",
        "Técnico en Electromecánica":               "Técnico en Electromecánica",
        "Técnico en Electrónica Industrial":        "Técnico en Electrónica y Electrónica Industrial",
        "Técnico en Energía":                       "Técnico en Energía",
        "Técnico en Industria Forestal":            "Técnico en Industria Forestal o de la Madera",
        "Técnico en Instrumentación":               "Técnico en Instrumentación, Automatización y Control Industrial",
        "Técnico en Mantenimiento Industrial":      "Técnico en Mantenimiento Industrial",
        "Técnico en Mecatrónica":                   "Técnico en Mecatrónica",
        "Técnico en Mecánica Automotriz":           "Técnico en Mecánica Automotriz",
        "Técnico en Mecánica Industrial":           "Técnico en Mecánica Industrial",
        "Técnico en Mecánica de Equipos":           "Técnico en Mecánica de Equipos",
        "Técnico en Medio Ambiente":                "Técnico en Medio Ambiente (Control y Gestión)",
        "Técnico en Metalurgia":                    "Técnico en Metalurgia",
        "Técnico en Minería":                       "Técnico en Minería",
        "Técnico en Prevención de Riesgos":         "Técnico en Prevención de Riesgos",
        "Técnico en Procesos Industriales":         "Técnico en Procesos Industriales",
        "Técnico en Producción Web":                "Técnico en Producción, Desarrollo y Diseño Web",
        "Técnico en Proyecto y Diseño Mecánico":    "Técnico en Proyecto y Diseño Mecánico",
        "Técnico en Proyectos de Ingeniería":       "Técnico en Proyectos de Ingeniería",
        "Técnico en Refrigeración":                 "Técnico en Refrigeración y Climatización",
        "Técnico en Sonido":                        "Técnico en Sonido",
        "Técnico en Telecomunicaciones":            "Técnico en Telecomunicaciones",
        "Técnico en Topografía":                    "Técnico en Topografía",
        "Técnico en Transporte Marítimo":           "Técnico en Transporte Marítimo y Puertos",
    },

}

# Resumen rápido
if __name__ == "__main__":
    total = sum(len(v) for v in CARRERAS_POR_AREA.values())
    print(f"Áreas: {len(CARRERAS_POR_AREA)}")
    print(f"Carreras totales: {total}")
    for area, carreras in CARRERAS_POR_AREA.items():
        print(f"  {len(carreras):3d}  {area}")
