# ⚡ Optimizador

Optimizador de rendimiento para laptops con **Windows 10/11**, inspirado en Hone.
Detecta automáticamente el hardware de tu laptop, mide en tiempo real el uso de
CPU, GPU y RAM, y aplica optimizaciones **reversibles** pensadas para bajar el
consumo de RAM y GPU y acelerar el encendido.

## Qué hace

| Pestaña | Para qué sirve |
|---|---|
| 🏠 **Inicio** | Panel con el % de optimización, CPU/GPU/RAM en vivo, diagnóstico y botón **Optimizar ahora** |
| 🚀 **Optimizaciones** | 23 ajustes con interruptor (General, RAM, GPU, Arranque, Juegos, Privacidad) y perfiles de uso |
| ⚡ **Arranque** | Programas que se abren al encender, con su impacto; desactívalos con un clic |
| 📈 **Procesos** | Qué programas usan más RAM y GPU ahora mismo, con botón para cerrarlos |
| 🎯 **Por tarea** | Consejos y optimizaciones para: apuntes, presentaciones, YouTube, software de dieta/gym, juegos y arranque lento |
| 💻 **Mi laptop** | Especificaciones detectadas (CPU, RAM, GPU, disco SSD/HDD, tiempo de arranque) y diagnóstico |
| 🧭 **Tipos de laptop** | Recomendaciones para gama básica, media, ultrabook, gaming y antigua (marca la tuya ★) |
| ⚙ **Ajustes** | Liberar RAM automáticamente al superar un %, puntos de restauración, revertir todo |

### Cómo baja el uso de RAM y GPU

- **Liberar RAM**: recorta la memoria que los programas no están usando (igual que Hone/Wise Memory Optimizer). Se puede activar en automático cuando la RAM pasa del 85 %.
- Desactiva efectos visuales, transparencias y la grabación de Xbox Game Bar (las tres usan GPU todo el tiempo).
- Evita que Edge, Widgets, apps de la Tienda y la búsqueda con Bing se queden abiertos en segundo plano.
- Desactiva programas de inicio pesados (OneDrive, Teams, Discord, Steam, Spotify…).

### Cómo acelera el encendido

- Activa el **Inicio rápido**, quita el retraso de programas de inicio y la pantalla de bloqueo con imagen (vas directo a la contraseña).
- Desactiva programas de inicio y, en laptops con disco HDD, SysMain y el indexado constante.
- La pestaña **Mi laptop** muestra cuántos segundos tardó el último arranque, para comparar antes/después.

## Seguridad

- Cada optimización guarda el valor original en `%APPDATA%\Optimizador\respaldo.json`; apagar el interruptor lo restaura.
- Antes de aplicar un perfil se crea un **punto de restauración** de Windows (desactivable en Ajustes).
- Los programas de inicio se desactivan con el mismo método que el Administrador de tareas.
- No cierra procesos críticos del sistema ni desactiva Windows Defender o Windows Update.

## Instalación

### Opción A: descargar el .exe
1. En GitHub ve a **Actions › Compilar Optimizador.exe** y abre la última ejecución.
2. Descarga el artefacto **Optimizador**, descomprímelo y abre `Optimizador.exe`.
3. Acepta el aviso de administrador (UAC).

> Windows SmartScreen puede avisar porque el .exe no está firmado: «Más información › Ejecutar de todas formas».

### Opción B: con Python
1. Instala [Python 3.10+](https://www.python.org/downloads/) marcando **"Add Python to PATH"**.
2. Doble clic en `ejecutar.bat` (instala dependencias y abre el programa).
3. Para crear tu propio .exe: doble clic en `compilar_exe.bat` → `dist\Optimizador.exe`.

## Uso recomendado para tareas escolares

1. Abre el programa como administrador.
2. En **Inicio**, pulsa **Optimizar ahora** (perfil "Apuntes y tareas escolares").
3. Revisa la pestaña **Arranque** y deja solo antivirus, audio, touchpad y controladores.
4. Cierra sesión o reinicia para que los efectos visuales y el arranque se apliquen.
5. Activa en **Ajustes** «Liberar RAM automáticamente».
6. Sigue los consejos de **Por tarea › YouTube** (aceleración por hardware, 1080p, h264ify): es lo que más baja la GPU al ver videos.

## Estructura

```
main.py                     punto de entrada (pide administrador)
optimizador/
  system_info.py            detección de hardware, tipo de laptop y diagnóstico
  tweaks.py                 catálogo de optimizaciones + aplicar/revertir con respaldo
  memory.py                 liberar RAM, procesos, limpieza de temporales
  monitor.py                CPU/RAM (psutil) y GPU (contadores WMI) en segundo plano
  startup.py                programas de inicio
  recommendations.py        consejos por tarea y por tipo de laptop
  ui/                       interfaz (CustomTkinter)
```
