"""Gestión de programas que se abren al encender Windows.

Usa el mismo mecanismo que el Administrador de tareas (claves
'StartupApproved'), así que desactivar un programa aquí es 100 % reversible
y se refleja también en la pestaña 'Inicio' del Administrador de tareas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .winutils import IS_WINDOWS, reg_get, reg_set, reg_values

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"

# Programas conocidos: (palabra clave, impacto, consejo)
KNOWN = [
    ("onedrive", "Alto", "Sincroniza archivos al encender. Puedes abrirlo solo cuando lo necesites."),
    ("teams", "Alto", "Teams consume 300-600 MB de RAM. Ábrelo solo para clases o reuniones."),
    ("discord", "Alto", "Discord usa mucha RAM al iniciar. Ábrelo manualmente."),
    ("steam", "Alto", "Steam carga un navegador interno. Ábrelo solo para jugar."),
    ("epic", "Alto", "Epic Games Launcher usa RAM y GPU en segundo plano."),
    ("spotify", "Medio", "Spotify no necesita abrirse al encender."),
    ("edge", "Alto", "Precarga de Edge: consume RAM aunque no uses el navegador."),
    ("chrome", "Medio", "Chrome no necesita abrirse al encender."),
    ("opera", "Medio", "Opera no necesita abrirse al encender."),
    ("adobe", "Medio", "Servicios de actualización de Adobe."),
    ("creative cloud", "Alto", "Creative Cloud usa varios procesos en segundo plano."),
    ("skype", "Medio", "Skype no necesita abrirse al encender."),
    ("zoom", "Medio", "Zoom se puede abrir solo cuando tengas reunión."),
    ("whatsapp", "Medio", "WhatsApp Desktop se puede abrir manualmente."),
    ("cortana", "Medio", "Cortana no es necesaria."),
    ("update", "Bajo", "Actualizador: suele ser seguro desactivarlo, el programa se actualiza al abrirlo."),
    ("google drive", "Medio", "Sincronización de Google Drive."),
    ("dropbox", "Medio", "Sincronización de Dropbox."),
    ("utorrent", "Alto", "uTorrent usa disco y red en segundo plano."),
    ("ccleaner", "Bajo", "No necesita abrirse al encender."),
]

# Cosas que conviene dejar activadas
KEEP = ("securityhealth", "windows defender", "realtek", "synaptics", "elan", "igfx",
        "nvidia", "amd", "radeon", "audio", "touchpad", "bluetooth", "intel", "dolby",
        "waves", "optimizador")


@dataclass
class StartupItem:
    name: str
    command: str
    source: str  # "HKCU", "HKLM", "HKLM32", "Carpeta usuario", "Carpeta común"
    enabled: bool
    impact: str
    advice: str

    @property
    def keep(self) -> bool:
        low = (self.name + " " + self.command).lower()
        return any(k in low for k in KEEP)


def _approved_key(source: str) -> tuple[str, str]:
    return {
        "HKCU": ("HKCU", APPROVED + r"\Run"),
        "HKLM": ("HKLM", APPROVED + r"\Run"),
        "HKLM32": ("HKLM", APPROVED + r"\Run32"),
        "Carpeta usuario": ("HKCU", APPROVED + r"\StartupFolder"),
        "Carpeta común": ("HKLM", APPROVED + r"\StartupFolder"),
    }[source]


def _is_enabled(source: str, name: str) -> bool:
    hive, path = _approved_key(source)
    val = reg_get(hive, path, name)
    if not val or not isinstance(val[0], bytes) or not val[0]:
        return True
    # Primer byte par = activado (02/06), impar = desactivado (03/07)
    return val[0][0] % 2 == 0


def _classify(name: str, command: str) -> tuple[str, str]:
    low = (name + " " + command).lower()
    for key, impact, advice in KNOWN:
        if key in low:
            return impact, advice
    if any(k in low for k in KEEP):
        return "Bajo", "Controlador o componente del sistema: mejor dejarlo activado."
    return "Medio", "Si no lo usas cada vez que enciendes la laptop, puedes desactivarlo."


def list_startup() -> list[StartupItem]:
    if not IS_WINDOWS:
        return []
    items: list[StartupItem] = []
    sources = [("HKCU", "HKCU", False), ("HKLM", "HKLM", False), ("HKLM32", "HKLM", True)]
    for source, hive, wow32 in sources:
        for name, cmd in reg_values(hive, RUN, wow64_32=wow32).items():
            if not isinstance(cmd, str) or not name:
                continue
            impact, advice = _classify(name, cmd)
            items.append(StartupItem(name, cmd, source, _is_enabled(source, name), impact, advice))

    folders = [
        ("Carpeta usuario", Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"),
        ("Carpeta común", Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"),
    ]
    for source, folder in folders:
        try:
            files = [f for f in folder.iterdir() if f.name.lower() != "desktop.ini"]
        except OSError:
            continue
        for f in files:
            impact, advice = _classify(f.stem, str(f))
            items.append(StartupItem(f.name, str(f), source, _is_enabled(source, f.name), impact, advice))

    order = {"Alto": 0, "Medio": 1, "Bajo": 2}
    return sorted(items, key=lambda i: (order.get(i.impact, 1), i.name.lower()))


def set_enabled(item: StartupItem, enabled: bool) -> bool:
    hive, path = _approved_key(item.source)
    data = bytes([0x02 if enabled else 0x03]) + bytes(11)
    ok = reg_set(hive, path, item.name, data, "BINARY")
    if ok:
        item.enabled = enabled
    return ok
