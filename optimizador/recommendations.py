"""Recomendaciones por tipo de tarea y por tipo de laptop."""

from __future__ import annotations

from .system_info import SystemSpecs

# Cada tarea: título, icono, descripción, lista de consejos (título, detalle)
TASKS = {
    "estudio": {
        "title": "Apuntes y tareas",
        "icon": "📝",
        "intro": "Para tomar apuntes y hacer tareas escolares no necesitas potencia, sino que la "
                 "laptop responda rápido y no se quede sin RAM.",
        "tips": [
            ("Usa un solo navegador", "Tener Chrome y Edge abiertos a la vez duplica el consumo de RAM. "
             "Elige uno y cierra el otro por completo."),
            ("Activa el ahorro de memoria del navegador", "Chrome: Configuración › Rendimiento › 'Ahorro de "
             "memoria'. Edge: Configuración › Sistema y rendimiento › 'Pestañas en suspensión' (5 min)."),
            ("Pocas pestañas abiertas", "Cada pestaña usa 100-300 MB. Guarda las páginas en marcadores o "
             "en una lista de lectura en vez de dejarlas abiertas."),
            ("Apuntes en apps ligeras", "OneNote, Google Docs o Notion web funcionan bien. Evita tener "
             "abiertos a la vez Word, OneNote y el navegador con Docs."),
            ("Desactiva la sincronización constante", "OneDrive/Google Drive sincronizando al mismo tiempo "
             "ralentizan todo. Pausa la sincronización mientras trabajas y reanúdala al terminar."),
            ("Modo de energía 'Equilibrado'", "Para tareas básicas es suficiente y alarga la batería. "
             "No necesitas 'Alto rendimiento'."),
        ],
    },
    "presentaciones": {
        "title": "Trabajos y presentaciones",
        "icon": "📊",
        "intro": "PowerPoint, Canva y Word con muchas imágenes son los que más RAM y GPU piden "
                 "dentro de las tareas básicas.",
        "tips": [
            ("Comprime las imágenes", "En PowerPoint: selecciona una imagen › Formato de imagen › "
             "'Comprimir imágenes' › 150 ppp. El archivo pesa menos y se mueve fluido."),
            ("Canva: usa la app web en un navegador limpio", "Canva consume mucha GPU. Cierra otras "
             "pestañas mientras diseñas y desactiva las animaciones en la vista previa."),
            ("Evita videos incrustados pesados", "Mejor enlazar videos de YouTube que pegar archivos MP4 "
             "de cientos de MB en la presentación."),
            ("Guarda en local y sube al terminar", "Editar directamente desde OneDrive/Drive con "
             "autoguardado constante consume disco y red."),
            ("Cierra Teams/Discord mientras trabajas", "Liberan entre 300 MB y 1 GB de RAM."),
            ("Desactiva complementos de Office", "Archivo › Opciones › Complementos: desactiva los que no "
             "uses (traductores, plugins de PDF...). Office abrirá más rápido."),
        ],
    },
    "videos": {
        "title": "YouTube y videos",
        "icon": "▶",
        "intro": "Ver videos no debería poner la GPU al 100 %. Si pasa, suele ser por la calidad "
                 "del video, el códec o la aceleración por hardware desactivada.",
        "tips": [
            ("Activa la aceleración por hardware", "Chrome/Edge: Configuración › Sistema › 'Usar "
             "aceleración de gráficos cuando esté disponible'. Así el video lo decodifica el chip de "
             "video y no el procesador."),
            ("Baja la calidad a 720p/1080p", "En pantallas de laptop de 14-15\" no se nota la diferencia "
             "con 1440p/4K y usa mucha menos GPU y RAM."),
            ("Instala la extensión 'enhanced-h264ify'", "Fuerza a YouTube a usar el códec H.264, que casi "
             "todas las GPU integradas decodifican sin esfuerzo (VP9/AV1 pueden saturarlas)."),
            ("Evita reproducir en segundo plano muchas pestañas", "Pausa los videos que no estás viendo: "
             "siguen consumiendo GPU aunque la pestaña no esté visible."),
            ("Desactiva la grabación de Xbox Game Bar", "Graba en segundo plano y usa la GPU todo el "
             "tiempo. Está en la pestaña Optimizaciones › Juegos."),
            ("Conecta el cargador para videos largos", "Con batería baja Windows reduce la frecuencia y el "
             "video puede trabarse."),
        ],
    },
    "apps": {
        "title": "Software de dietas y gym",
        "icon": "💪",
        "intro": "Las apps de nutrición y rutinas (de escritorio o web) son ligeras, pero muchas "
                 "están hechas con tecnología web (Electron) y consumen como un navegador.",
        "tips": [
            ("Usa la versión web si existe", "Muchas apps de dieta/rutinas (MyFitnessPal, Hevy, "
             "Fitbod, etc.) tienen versión web: consumen menos que la app de escritorio."),
            ("Ciérrala al terminar", "Que no se quede en la bandeja del sistema (junto al reloj). "
             "Revisa sus ajustes y desactiva 'Iniciar con Windows' y 'Minimizar a la bandeja'."),
            ("Hojas de cálculo grandes", "Si llevas tus rutinas en Excel con muchas fórmulas y gráficas, "
             "divide el archivo por meses para que abra más rápido."),
            ("Mantén la app actualizada", "Las actualizaciones suelen corregir fugas de memoria."),
            ("Revisa que no esté en el inicio", "Pestaña 'Arranque' de este programa."),
        ],
    },
    "juegos": {
        "title": "Juegos",
        "icon": "🎮",
        "intro": "Para jugar sí conviene priorizar el rendimiento: plan de energía alto, modo "
                 "juego y cerrar todo lo demás.",
        "tips": [
            ("Juega siempre conectado al cargador", "Con batería la GPU y la CPU bajan su potencia hasta "
             "a la mitad."),
            ("Elige la GPU dedicada", "Configuración › Sistema › Pantalla › Gráficos: asigna el juego a "
             "'Alto rendimiento' (si tu laptop tiene NVIDIA/AMD dedicada)."),
            ("Actualiza los drivers de video", "Descarga el driver desde la web de NVIDIA, AMD o Intel, "
             "no solo desde Windows Update."),
            ("Baja la resolución de render, no la de pantalla", "Usa FSR/DLSS/XeSS o 'escala de "
             "resolución' al 75-85 % antes de bajar texturas."),
            ("Limita los FPS", "Fijar FPS al refresco de tu pantalla (60/120/144) reduce temperatura y evita "
             "que la laptop se frene por calor."),
            ("Eleva la laptop", "Una base o algo que levante la parte trasera mejora la ventilación y evita "
             "el 'thermal throttling'."),
            ("Cierra el navegador antes de jugar", "Es lo que más RAM consume después del juego."),
        ],
    },
    "arranque": {
        "title": "Arranque lento",
        "icon": "⚡",
        "intro": "Si tarda mucho en encender y en mostrar la contraseña, casi siempre es por el disco "
                 "(HDD), por demasiados programas de inicio o por actualizaciones pendientes.",
        "tips": [
            ("Desactiva programas de inicio", "Pestaña 'Arranque': deja solo antivirus, audio y "
             "touchpad. OneDrive, Teams, Spotify, Discord, Steam y similares pueden abrirse a mano."),
            ("Activa el Inicio rápido", "Ya incluido en Optimizaciones › Arranque."),
            ("Ve directo a la contraseña", "Optimización 'Ir directo a la contraseña' quita la pantalla "
             "de bloqueo con imagen."),
            ("Usa PIN en lugar de contraseña", "Configuración › Cuentas › Opciones de inicio de sesión › "
             "PIN. Es más rápido de escribir y verificar que la contraseña de la cuenta Microsoft."),
            ("Instala las actualizaciones pendientes", "Si Windows Update tiene actualizaciones a medias, "
             "cada arranque intenta terminarlas."),
            ("Reinicia de vez en cuando", "Con Inicio rápido, 'Apagar' no reinicia el sistema por "
             "completo. Usa 'Reiniciar' una vez por semana para limpiar la memoria."),
            ("Cambia a SSD si tienes HDD", "Es la mejora más grande posible: un SSD SATA de 480 GB es "
             "económico y reduce el arranque de 2-3 min a 15-20 s."),
        ],
    },
}

LAPTOPS = {
    "basica": {
        "title": "Gama básica / de entrada",
        "icon": "💻",
        "who": "Celeron, Pentium, Athlon, Core i3 o Ryzen 3 · 4-8 GB de RAM · gráficos integrados.",
        "tips": [
            "Activa todas las optimizaciones de RAM y GPU de este programa.",
            "Usa Edge con 'Pestañas en suspensión' o Chrome con 'Ahorro de memoria' activado.",
            "Máximo 5-8 pestañas abiertas a la vez.",
            "Desactiva casi todos los programas de inicio.",
            "Si tienes 4 GB, ampliar a 8 GB es la mejora con mejor relación precio/resultado.",
            "Si tienes un solo módulo de RAM y hay ranura libre, añade otro igual (dual channel).",
            "Evita antivirus de terceros pesados: Windows Defender es suficiente.",
            "Juegos: solo títulos ligeros (Minecraft con OptiFine/Sodium, Stardew Valley, juegos indie).",
        ],
    },
    "media": {
        "title": "Gama media / oficina",
        "icon": "🖥",
        "who": "Core i5/i7 o Ryzen 5/7 · 8-16 GB de RAM · gráficos integrados (Iris Xe, Radeon).",
        "tips": [
            "Las optimizaciones generales y de arranque son suficientes.",
            "Mantén los drivers de Intel/AMD actualizados desde la web del fabricante.",
            "En el BIOS, si existe la opción, asigna 1-2 GB de memoria a la GPU integrada (UMA).",
            "Usa el modo 'Equilibrado' con batería y 'Alto rendimiento' con cargador.",
            "Juegos: e-sports (Valorant, LoL, Fortnite en modo rendimiento) a 720p-1080p bajo.",
        ],
    },
    "ultrabook": {
        "title": "Ultrabook / ligera",
        "icon": "🪶",
        "who": "Procesadores serie U / Ultra · diseño delgado · priorizan batería y silencio.",
        "tips": [
            "Su límite suele ser la temperatura: úsala sobre una mesa, no sobre la cama o las piernas.",
            "Usa el software del fabricante (MyASUS, Lenovo Vantage, HP Command Center, Dell Optimizer) "
            "para elegir el modo 'Rendimiento' cuando lo necesites.",
            "Desactiva efectos visuales y transparencias para ganar fluidez con pantallas de alta resolución.",
            "Si la pantalla es 2K/4K, bajar la escala o el refresco ahorra GPU y batería.",
            "La RAM suele estar soldada: controla las pestañas y apps abiertas.",
        ],
    },
    "gaming": {
        "title": "Gaming / con GPU dedicada",
        "icon": "🎮",
        "who": "GPU NVIDIA GeForce / AMD Radeon RX dedicada · 16 GB de RAM o más.",
        "tips": [
            "Para tareas básicas fuerza la GPU integrada (modo 'Eco'/'Optimus') y ahorrarás batería y calor.",
            "Para jugar, conecta el cargador y usa el modo 'Turbo/Rendimiento' del software del fabricante.",
            "Activa el MUX switch / 'GPU dedicada' si tu laptop lo tiene, para más FPS.",
            "Actualiza el driver con GeForce Experience / NVIDIA App o AMD Adrenalin.",
            "Limpia los ventiladores cada 6-12 meses y cambia la pasta térmica cada 2 años.",
            "Activa la 'Programación de GPU acelerada por hardware' en Optimizaciones › Juegos.",
        ],
    },
    "antigua": {
        "title": "Antigua (con disco duro HDD)",
        "icon": "🐢",
        "who": "Laptops de 5+ años, disco mecánico, a menudo con Windows 10/11 recién actualizado.",
        "tips": [
            "Cambia el HDD por un SSD: es la mejora nº 1 (encendido 5-10 veces más rápido).",
            "Mientras tanto: desactiva SysMain y el indexado de búsqueda (Optimizaciones).",
            "Deja la laptop encendida 10-15 min de vez en cuando para que Windows termine sus tareas.",
            "Desfragmenta el disco: busca 'Desfragmentar y optimizar unidades' en el menú Inicio.",
            "Activa todas las optimizaciones de efectos visuales.",
            "Considera una instalación limpia de Windows si tiene años sin formatearse.",
        ],
    },
}


def personalized(specs: SystemSpecs) -> list[str]:
    """Consejos generados a partir del hardware detectado."""
    tips = []
    if specs.only_hdd:
        tips.append("Tu disco es HDD: un SSD es la mejora que más notarás al encender y abrir programas.")
    if specs.ram_gb and specs.ram_gb <= 4.5:
        tips.append(f"Con {specs.ram_gb:.0f} GB de RAM es normal llegar al 90-100 %. Lo ideal es ampliar a "
                    "8 GB; mientras tanto, usa 'Liberar RAM' y limita las pestañas.")
    elif specs.ram_gb and specs.ram_gb <= 8.5:
        tips.append(f"Con {specs.ram_gb:.0f} GB de RAM controla los programas de inicio y usa el ahorro "
                    "de memoria del navegador.")
    if specs.single_channel_ram and specs.ram_slots >= 2:
        tips.append("Tienes un solo módulo de RAM con ranura libre: agregar otro igual activa dual "
                    "channel (hasta +30 % de rendimiento en la GPU integrada).")
    if specs.gpus and not specs.has_dedicated_gpu:
        tips.append("Tu GPU integrada usa la RAM del sistema: por eso cuando la GPU sube también sube la "
                    "RAM. Bajar efectos visuales y la calidad de video ayuda a las dos.")
    elif specs.has_dedicated_gpu:
        tips.append("Tienes GPU dedicada: para tareas básicas usa el modo de GPU integrada/Eco del software "
                    "del fabricante para menos calor y más batería.")
    if specs.boot_seconds and specs.boot_seconds > 45:
        tips.append(f"Tu último arranque tardó {specs.boot_seconds:.0f} s. Revisa la pestaña 'Arranque'.")
    return tips
