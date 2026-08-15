"""
Diccionario de carreras SIES 2026 — aprobadas para scraping
Fuente: Oferta Académica 2026 SIES (05-06-2026)
Revisión manual: agosto 2026
Total: 199 carreras / 10 áreas

Uso en scraper_v7.py:
  AREA = "Salud"   # único valor que cambias entre ejecuciones
"""

CARRERAS_POR_AREA = {

    # ====================================================
    # Administración y Comercio — 28 carreras
    # ====================================================
    "Administración y Comercio": {
        "Administración de Empresas": "Administración de Empresas e Ing. Asociadas",
        "Técnico en Administración de Empresas": "Técnico en Administración de Empresas",
        "Contador Auditor": "Contador Auditor",
        "Técnico en Logística": "Técnico en Logística",
        "Ingeniería Comercial": "Ingeniería Comercial",
        "Técnico en Contabilidad General": "Técnico en Contabilidad General",
        "Técnico en Turismo y Hotelería": "Técnico en Turismo y Hotelería",
        "Técnico en Gastronomía": "Técnico en Gastronomía y Cocina",
        "Ingeniería en Logística": "Ingeniería en Logística",
        "Técnico en Administración de Recursos Humanos": "Técnico en Administración de Recursos Humanos y Personal",
        "Ingeniería en Recursos Humanos": "Ingeniería en Recursos Humanos",
        "Técnico en Administración Financiera": "Técnico en Administración Financiera y Finanzas",
        "Administración Turística y Hotelera": "Administración Turística y Hotelera",
        "Técnico en Administración en Marketing": "Técnico en Administración en Marketing",
        "Ingeniería en Marketing": "Ingeniería en Marketing",
        "Ingeniería en Finanzas": "Ingeniería en Finanzas",
        "Técnico en Comercio Exterior": "Técnico en Comercio Exterior",
        "Ingeniería en Comercio Exterior": "Ingeniería en Comercio Exterior",
        "Administración Gastronómica": "Administración Gastronómica",
        "Ingeniería en Control de Gestión": "Ingeniería en Control de Gestión",
        "Técnico en Administración de Ventas": "Técnico en Administración de Ventas",
        "Ingeniería en Seguridad Privada": "Ingeniería en Seguridad Privada",
        "Técnico en Contabilidad Tributaria": "Técnico en Contabilidad Tributaria",
        "Técnico en Gestión y Control de Calidad": "Técnico en Gestión y Control de Calidad",
        "Técnico en Producción de Eventos": "Técnico en Producción de Eventos",
        "Técnico en Seguridad Privada": "Técnico en Seguridad Privada",
        "Secretariado Bilingüe": "Secretariado Bilingüe",
        "Ingeniería en Gestión y Control de Calidad": "Ingeniería en Gestión y Control de Calidad",
    },

    # ====================================================
    # Agropecuaria — 9 carreras
    # ====================================================
    "Agropecuaria": {
        "Técnico Agropecuario": "Técnico Agropecuario",
        "Ingeniería Agrícola": "Ingeniería Agrícola",
        "Técnico Veterinario": "Técnico Veterinario",
        "Agronomía": "Agronomía",
        "Medicina Veterinaria": "Medicina Veterinaria",
        "Enología": "Técnico en Vitivinicultura y/o Enología",
        "Acuicultura": "Ingeniería en Acuicultura y Pesca",
        "Técnico Acuicultura": "Técnico en Acuicultura y Pesca",
        "Ingeniería Forestal": "Ingeniería Forestal",
    },

    # ====================================================
    # Arte y Arquitectura — 12 carreras
    # ====================================================
    "Arte y Arquitectura": {
        "Diseño Gráfico": "Diseño Gráfico",
        "Arquitectura": "Arquitectura",
        "Técnico en Dibujo Arquitectónico": "Técnico en Dibujo Arquitectónico",
        "Técnico en Producción Gráfica y Multimedia": "Técnico en Producción Gráfica y Multimedia",
        "Comunicación Audiovisual": "Comunicación Audiovisual y/o Multimedia",
        "Diseño de Vestuario": "Diseño de Vestuario",
        "Animación Digital": "Animación Digital",
        "Realizador de Cine y Televisión": "Realizador de Cine y Televisión",
        "Diseño de Ambientes e Interiores": "Diseño de Ambientes e Interiores",
        "Fotografía": "Fotografía",
        "Técnico en Producción de Videojuegos": "Técnico en Producción de Videojuegos",
        "Paisajismo": "Paisajismo",
    },

    # ====================================================
    # Ciencias Básicas — 15 carreras
    # ====================================================
    "Ciencias Básicas": {
        "Ingeniería en Matemática y Estadística": "Ingeniería en Matemática y Estadística",
        "Ingeniería en Geomensura y Cartografía": "Ingeniería en Geomensura y Cartografía",
        "Física y Astronomía": "Física y Astronomía",
        "Geología": "Geología",
        "Técnico en Química (Análisis e Industrial)": "Técnico en Química (Análisis e Industrial)",
        "Ingeniería Civil Matemática y Estadística": "Ingeniería Civil Matemática y Estadística",
        "Química": "Química, Licenciado en Química",
        "Bioquímica": "Bioquímica",
        "Matemática": "Matemática y/o Estadística",
        "Biología Marina y Ecología Marina": "Biología Marina y Ecología Marina",
        "Biología": "Biología",
        "Técnico en Geominería": "Técnico en Geominería",
        "Técnico en Geología": "Técnico en Geología",
        "Analista Químico": "Analista Químico",
        "Ingeniería Civil en Geomática y Geomensura": "Ingeniería Civil en Geomática y Geomensura",
    },

    # ====================================================
    # Ciencias Sociales — 14 carreras
    # ====================================================
    "Ciencias Sociales": {
        "Trabajo Social": "Trabajo Social",
        "Técnico en Administración Pública o Municipal": "Técnico en Administración Pública o Municipal",
        "Psicología": "Psicología",
        "Administración Pública": "Administración Pública",
        "Periodismo": "Periodismo",
        "Publicidad": "Publicidad",
        "Relaciones Públicas": "Relaciones Públicas",
        "Técnico en Prevención y Rehabilitación": "Técnico en Prevención y Rehabilitación",
        "Sociología": "Sociología",
        "Historia": "Historia",
        "Ciencias Políticas": "Ciencias Políticas",
        "Antropología": "Antropología",
        "Geografía": "Geografía",
        "Arqueología": "Arqueología",
    },

    # ====================================================
    # Derecho — 1 carreras
    # ====================================================
    "Derecho": {
        "Derecho": "Derecho",
    },

    # ====================================================
    # Educación — 14 carreras
    # ====================================================
    "Educación": {
        "Técnico Asistente del Educador de Párvulos": "Técnico Asistente del Educador de Párvulos",
        "Técnico Asistente del Educador Diferencial": "Técnico Asistente del Educador Diferencial",
        "Psicopedagogía": "Psicopedagogía",
        "Técnico en Deporte": "Técnico en Deporte, Recreación y Preparación Física",
        "Pedagogía en Educación de Párvulos": "Pedagogía en Educación de Párvulos",
        "Pedagogía en Educación Básica": "Pedagogía en Educación Básica",
        "Pedagogía en Educación Diferencial": "Pedagogía en Educación Diferencial",
        "Pedagogía en Educación Física": "Pedagogía en Educación Física",
        "Pedagogía en Idiomas": "Pedagogía en Idiomas",
        "Pedagogía en Ciencias": "Pedagogía en Ciencias",
        "Pedagogía en Matemáticas y Computación": "Pedagogía en Matemáticas y Computación",
        "Pedagogía en Lenguaje": "Pedagogía en Lenguaje, Comunicación y/o Castellano",
        "Pedagogía en Artes y Música": "Pedagogía en Artes y Música",
        "Pedagogía en Historia": "Pedagogía en Historia, Geografía y Ciencias Sociales",
    },

    # ====================================================
    # Humanidades — 3 carreras
    # ====================================================
    "Humanidades": {
        "Traducción e Interpretación": "Traducción e Interpretación",
        "Licenciatura en Letras y Literatura": "Licenciatura en Letras y Literatura",
        "Filosofía": "Filosofía",
    },

    # ====================================================
    # Salud — 22 carreras
    # ====================================================
    "Salud": {
        "Técnico en Enfermería": "Técnico en Enfermería",
        "Técnico en Podología": "Técnico en Podología",
        "Enfermería": "Enfermería",
        "Técnico Dental y Asistente de Odontología": "Técnico Dental y Asistente de Odontología",
        "Kinesiología": "Kinesiología",
        "Técnico en Masoterapia": "Técnico en Masoterapia",
        "Técnico en Farmacia": "Técnico en Farmacia",
        "Nutrición y Dietética": "Nutrición y Dietética",
        "Terapia Ocupacional": "Terapia Ocupacional",
        "Fonoaudiología": "Fonoaudiología",
        "Tecnología Médica": "Tecnología Médica",
        "Medicina": "Medicina",
        "Obstetricia y Puericultura": "Obstetricia y Puericultura",
        "Odontología": "Odontología",
        "Técnico en Terapias Naturales y Naturopatía": "Técnico en Terapias Naturales y Naturopatía",
        "Química y Farmacia": "Química y Farmacia",
        "Técnico en Laboratorio Clínico": "Técnico en Laboratorio Clínico",
        "Técnico en Radiología y Radioterapia": "Técnico en Radiología y Radioterapia",
        "Técnico Laboratorista Dental": "Técnico Laboratorista Dental",
        "Naturopatía": "Naturopatía",
        "Técnico en Nutrición y Dietética": "Técnico en Nutrición y Dietética",
        "Técnico en Óptica": "Técnico en Óptica",
    },

    # ====================================================
    # Tecnología — 81 carreras
    # ====================================================
    "Tecnología": {
        "Técnico en Computación e Informática": "Técnico en Computación e Informática",
        "Ingeniería en Computación e Informática": "Ingeniería en Computación e Informática",
        "Técnico en Electricidad y Electricidad Industrial": "Técnico en Electricidad y Electricidad Industrial",
        "Ingeniería en Prevención de Riesgos": "Ingeniería en Prevención de Riesgos",
        "Técnico en Prevención de Riesgos": "Técnico en Prevención de Riesgos",
        "Técnico en Construcción y Obras Civiles": "Técnico en Construcción y Obras Civiles",
        "Ingeniería Industrial": "Ingeniería Industrial",
        "Ingeniería Civil Industrial": "Ingeniería Civil Industrial",
        "Ingeniería en Electricidad": "Ingeniería en Electricidad",
        "Técnico en Instrumentación": "Técnico en Instrumentación, Automatización y Control Industrial",
        "Técnico en Mecánica Automotriz": "Técnico en Mecánica Automotriz",
        "Construcción Civil": "Construcción Civil",
        "Técnico en Minería": "Técnico en Minería",
        "Técnico en Mantenimiento Industrial": "Técnico en Mantenimiento Industrial",
        "Ingeniería en Conectividad y Redes": "Ingeniería en Conectividad y Redes",
        "Ingeniería en Construcción": "Ingeniería en Construcción",
        "Ingeniería en Mecánica Automotriz": "Ingeniería en Mecánica Automotriz",
        "Ingeniería en Automatización": "Ingeniería en Automatización, Instrumentación y Control",
        "Técnico en Administración de Redes y Soporte": "Técnico en Administración de Redes y Soporte",
        "Técnico en Topografía": "Técnico en Topografía",
        "Ingeniería Civil en Computación e Informática": "Ingeniería Civil en Computación e Informática",
        "Técnico en Electromecánica": "Técnico en Electromecánica",
        "Técnico en Telecomunicaciones": "Técnico en Telecomunicaciones",
        "Ingeniería en Minas": "Ingeniería en Minas",
        "Ingeniería Mecánica": "Ingeniería Mecánica",
        "Técnico en Mecánica Industrial": "Técnico en Mecánica Industrial",
        "Técnico en Energía": "Técnico en Energía",
        "Ingeniería Civil en Minas": "Ingeniería Civil en Minas",
        "Técnico en Refrigeración y Climatización": "Técnico en Refrigeración y Climatización",
        "Ingeniería en Medio Ambiente": "Ingeniería en Medio Ambiente",
        "Ingeniería en Telecomunicaciones": "Ingeniería en Telecomunicaciones",
        "Ingeniería Civil Mecánica": "Ingeniería Civil Mecánica",
        "Técnico en Alimentos": "Técnico en Alimentos",
        "Ingeniería Civil Eléctrica": "Ingeniería Civil Eléctrica",
        "Técnico en Sonido": "Técnico en Sonido",
        "Ingeniería Civil en Obras Civiles": "Ingeniería Civil en Obras Civiles",
        "Técnico en Metalurgia": "Técnico en Metalurgia",
        "Ingeniería en Electrónica": "Ingeniería en Electrónica",
        "Técnico en Electrónica y Electrónica Industrial": "Técnico en Electrónica y Electrónica Industrial",
        "Ingeniería en Sonido": "Ingeniería en Sonido",
        "Ingeniería Civil Química": "Ingeniería Civil Química",
        "Técnico en Mecatrónica": "Técnico en Mecatrónica",
        "Diseño Industrial": "Diseño Industrial",
        "Ingeniería Civil Electrónica": "Ingeniería Civil Electrónica",
        "Ingeniería en Energía": "Ingeniería en Energía",
        "Ingeniería Civil Metalúrgica": "Ingeniería Civil Metalúrgica",
        "Técnico en Procesos Industriales": "Técnico en Procesos Industriales",
        "Ingeniería Civil Ambiental": "Ingeniería Civil Ambiental",
        "Técnico en Transporte Marítimo y Puertos": "Técnico en Transporte Marítimo y Puertos",
        "Ingeniería en Metalurgia": "Ingeniería en Metalurgia",
        "Ingeniería en Alimentos": "Ingeniería en Alimentos",
        "Ingeniería en Mecatrónica": "Ingeniería en Mecatrónica",
        "Ingeniería en Química": "Ingeniería en Química",
        "Técnico en Análisis de Sistemas": "Técnico en Análisis de Sistemas",
        "Ingeniería en Refrigeración y Climatización": "Ingeniería en Refrigeración y Climatización",
        "Técnico en Agroindustria": "Técnico en Agroindustria",
        "Ingeniería Civil en Biotecnología": "Ingeniería Civil en Biotecnología y/o Bioingeniería",
        "Ingeniería Marina y Marítimo Portuaria": "Ingeniería Marina y Marítimo Portuaria",
        "Ingeniería Civil en Biomédica": "Ingeniería Civil en Biomédica",
        "Ingeniería en Recursos Renovables": "Ingeniería en Recursos Renovables",
        "Técnico en Dibujo Técnico": "Técnico en Dibujo Técnico",
        "Técnico en Diseño Industrial": "Técnico en Diseño Industrial",
        "Ingeniería Civil en Telemática": "Ingeniería Civil en Telemática",
        "Ingeniería Agroindustrial": "Ingeniería Agroindustrial",
        "Ingeniería Civil en Energía": "Ingeniería Civil en Energía",
        "Biotecnología": "Biotecnología",
        "Ingeniería en Proyectos Estructurales": "Ingeniería en Proyectos Estructurales",
        "Química Industrial": "Química Industrial",
        "Técnico en Industria Forestal o de la Madera": "Técnico en Industria Forestal o de la Madera",
        "Técnico en Mecánica de Equipos": "Técnico en Mecánica de Equipos",
        "Ingeniería Civil Agrícola": "Ingeniería Civil Agrícola",
        "Ingeniería Civil Bioquímica": "Ingeniería Civil Bioquímica",
        "Ingeniería Civil en Geografía": "Ingeniería Civil en Geografía",
        "Ingeniería Civil en Sonido y Acústica": "Ingeniería Civil en Sonido y Acústica",
        "Ingeniería en Geomensura y Cartografía": "Ingeniería en Geomensura y Cartografía",
        "Ingeniería en Industria de la Madera": "Ingeniería en Industria de la Madera",
        "Ingeniería en Transporte y Tránsito": "Ingeniería en Transporte y Tránsito",
        "Ingeniería Naval": "Ingeniería Naval",
        "Técnico en Biotecnología Industrial": "Técnico en Biotecnología Industrial",
        "Ingeniería Civil en Industrias Forestales": "Ingeniería Civil en Industrias Forestales",
        "Ingeniería Civil en Materiales": "Ingeniería Civil en Materiales",
    },

}

if __name__ == "__main__":
    total = sum(len(v) for v in CARRERAS_POR_AREA.values())
    print(f"Áreas: {len(CARRERAS_POR_AREA)}")
    print(f"Carreras: {total}")
    for area, carreras in CARRERAS_POR_AREA.items():
        print(f"  {len(carreras):3d}  {area}")