"""Catálogo de optimizaciones reversibles y su motor de aplicar/revertir.

Cada optimización guarda el valor original antes de cambiarlo (en
%APPDATA%\\Optimizador\\respaldo.json), así que siempre se puede volver atrás
desactivando el interruptor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from .winutils import (IS_WINDOWS, load_json, powershell, reg_delete, reg_get, reg_set, run,
                       save_json)

BACKUP_FILE = "respaldo.json"

# Categorías que se muestran como pestañas
CATEGORIES = ["General", "RAM", "GPU", "Arranque", "Juegos", "Privacidad"]

# Perfiles de uso (se usan en las pestañas de recomendaciones)
PROFILES = {
    "estudio": "Apuntes y tareas escolares",
    "presentaciones": "Trabajos y presentaciones",
    "videos": "YouTube y videos",
    "apps": "Software de dietas / gym",
    "juegos": "Juegos",
    "bateria": "Ahorro de batería",
}
BASIC = ("estudio", "presentaciones", "videos", "apps")


@dataclass
class RegChange:
    hive: str
    path: str
    name: str
    value: object
    type: str = "DWORD"
    check: bool = True  # False si Windows puede reescribir el valor por su cuenta


@dataclass
class ServiceChange:
    name: str
    start: int  # 2 = automático, 3 = manual, 4 = deshabilitado


@dataclass
class Tweak:
    id: str
    name: str
    description: str
    category: str
    impact: str  # texto corto: "Menos RAM", "Menos GPU", ...
    profiles: tuple[str, ...] = ()
    admin: bool = False
    reboot: bool = False
    regs: list[RegChange] = field(default_factory=list)
    services: list[ServiceChange] = field(default_factory=list)
    # Para casos especiales (plan de energía, etc.)
    custom_apply: Callable[[dict], bool] | None = None
    custom_revert: Callable[[dict], bool] | None = None
    custom_check: Callable[[], bool] | None = None
    after: list[str] = field(default_factory=list)  # comandos tras aplicar/revertir


# --------------------------------------------------------------------------
# Casos especiales
# --------------------------------------------------------------------------

HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
_GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _active_scheme() -> str:
    _, out = run(["powercfg", "/getactivescheme"])
    m = _GUID.search(out)
    return m.group(0).lower() if m else ""


def _power_apply(backup: dict) -> bool:
    backup["previous_scheme"] = _active_scheme() or BALANCED
    code, _ = run(["powercfg", "/setactive", HIGH_PERF])
    if code != 0:
        # Muchas laptops ocultan el plan "Alto rendimiento": se duplica.
        _, out = run(["powercfg", "-duplicatescheme", HIGH_PERF])
        m = _GUID.search(out)
        if not m:
            return False
        backup["created_scheme"] = m.group(0).lower()
        code, _ = run(["powercfg", "/setactive", m.group(0)])
    return code == 0


def _power_revert(backup: dict) -> bool:
    code, _ = run(["powercfg", "/setactive", backup.get("previous_scheme", BALANCED)])
    return code == 0


def _power_check() -> bool:
    active = _active_scheme()
    data = load_json(BACKUP_FILE, {}).get("power_plan", {})
    return active in (HIGH_PERF, data.get("created_scheme", "-"))


def _fast_startup_apply(backup: dict) -> bool:
    run(["powercfg", "/hibernate", "on"])
    return reg_set("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                   "HiberbootEnabled", 1)


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------

CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"

TWEAKS: list[Tweak] = [
    # ---------------- General ----------------
    Tweak(
        "visual_effects", "Efectos visuales para rendimiento",
        "Desactiva animaciones, sombras y transiciones de Windows. Reduce el uso de GPU y RAM "
        "(el proceso 'Administrador de ventanas del escritorio'). Se nota al cerrar sesión.",
        "GPU", "Menos GPU", profiles=BASIC + ("juegos", "bateria"),
        regs=[
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                      "VisualFXSetting", 3),
            RegChange("HKCU", r"Control Panel\Desktop", "UserPreferencesMask",
                      bytes([0x90, 0x12, 0x03, 0x80, 0x10, 0x00, 0x00, 0x00]), "BINARY", check=False),
            RegChange("HKCU", r"Control Panel\Desktop\WindowMetrics", "MinAnimate", "0", "SZ"),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                      "TaskbarAnimations", 0),
            RegChange("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", 0),
        ],
    ),
    Tweak(
        "transparency", "Desactivar transparencias",
        "Quita el efecto de vidrio/transparencia de la barra de tareas y menús. Menos carga para la GPU integrada.",
        "GPU", "Menos GPU", profiles=BASIC + ("juegos", "bateria"),
        regs=[RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                        "EnableTransparency", 0)],
    ),
    Tweak(
        "menu_delay", "Menús más rápidos",
        "Reduce el retraso al abrir menús de 400 ms a 100 ms. Windows se siente más ágil.",
        "General", "Más fluidez", profiles=BASIC + ("juegos",),
        regs=[RegChange("HKCU", r"Control Panel\Desktop", "MenuShowDelay", "100", "SZ")],
    ),
    Tweak(
        "power_plan", "Plan de energía de alto rendimiento",
        "Activa el plan 'Alto rendimiento' para que el procesador no se frene. Úsalo conectado al "
        "cargador; con batería consume más.",
        "General", "Más CPU", profiles=("juegos",), admin=True,
        custom_apply=_power_apply, custom_revert=_power_revert, custom_check=_power_check,
    ),
    Tweak(
        "tips_ads", "Desactivar sugerencias y anuncios de Windows",
        "Evita consejos, apps sugeridas e instalaciones automáticas de apps promocionadas que corren en segundo plano.",
        "General", "Menos RAM", profiles=BASIC + ("juegos", "bateria"),
        regs=[
            RegChange("HKCU", CDM, "SilentInstalledAppsEnabled", 0),
            RegChange("HKCU", CDM, "SystemPaneSuggestionsEnabled", 0),
            RegChange("HKCU", CDM, "SoftLandingEnabled", 0),
            RegChange("HKCU", CDM, "SubscribedContent-338388Enabled", 0),
            RegChange("HKCU", CDM, "SubscribedContent-338389Enabled", 0),
            RegChange("HKCU", CDM, "SubscribedContent-353694Enabled", 0),
            RegChange("HKCU", CDM, "SubscribedContent-353696Enabled", 0),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                      "ShowSyncProviderNotifications", 0),
        ],
    ),
    # ---------------- RAM ----------------
    Tweak(
        "background_apps", "Bloquear apps en segundo plano",
        "Impide que las apps de la Tienda (Correo, Fotos, Xbox, Noticias…) sigan ejecutándose cuando no las usas.",
        "RAM", "Menos RAM", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
                      "GlobalUserDisabled", 1),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search",
                      "BackgroundAppGlobalToggle", 0),
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AppPrivacy",
                      "LetAppsRunInBackground", 2),
        ],
    ),
    Tweak(
        "edge_background", "Evitar que Edge se quede abierto en segundo plano",
        "Microsoft Edge se precarga al iniciar Windows y sigue abierto al cerrarlo ('Startup boost'). "
        "Esto consume 200-500 MB de RAM aunque no lo uses.",
        "RAM", "Menos RAM", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "StartupBoostEnabled", 0),
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Edge", "BackgroundModeEnabled", 0),
        ],
    ),
    Tweak(
        "widgets", "Desactivar Widgets y Noticias",
        "Quita el panel de widgets/noticias/clima, que mantiene procesos web abiertos todo el tiempo.",
        "RAM", "Menos RAM", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Dsh", "AllowNewsAndInterests", 0),
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds",
                      "EnableFeeds", 0),
        ],
        after=["taskkill /f /im Widgets.exe", "taskkill /f /im WidgetService.exe"],
    ),
    Tweak(
        "web_search", "Quitar Bing/Cortana de la búsqueda",
        "La búsqueda de Windows deja de consultar internet y de cargar Bing: más rápida y menos RAM.",
        "RAM", "Menos RAM", profiles=BASIC + ("juegos", "bateria"),
        regs=[
            RegChange("HKCU", r"Software\Policies\Microsoft\Windows\Explorer",
                      "DisableSearchBoxSuggestions", 1),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 0),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "CortanaConsent", 0),
        ],
    ),
    Tweak(
        "sysmain", "Desactivar SysMain (Superfetch)",
        "SysMain precarga programas en la RAM. En laptops con poca RAM o disco HDD provoca uso de disco "
        "y memoria al 100 % durante minutos tras encender.",
        "RAM", "Menos RAM / disco", profiles=("estudio", "presentaciones", "videos", "apps"), admin=True,
        services=[ServiceChange("SysMain", 4)],
    ),
    # ---------------- Arranque ----------------
    Tweak(
        "fast_startup", "Activar Inicio rápido",
        "Windows guarda parte del sistema al apagar para encender mucho más rápido.",
        "Arranque", "Arranque rápido", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[RegChange("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                        "HiberbootEnabled", 1)],
        custom_apply=_fast_startup_apply,
    ),
    Tweak(
        "startup_delay", "Quitar retraso de programas de inicio",
        "Windows espera unos segundos antes de abrir los programas de inicio. Esto lo elimina para "
        "que el escritorio esté listo antes.",
        "Arranque", "Arranque rápido", profiles=BASIC + ("juegos",),
        regs=[RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                        "StartupDelayInMSec", 0)],
    ),
    Tweak(
        "lock_screen", "Ir directo a la contraseña",
        "Omite la pantalla de bloqueo con imagen (la que hay que deslizar) y muestra directamente "
        "el cuadro de contraseña al encender (en Windows Home puede no tener efecto).",
        "Arranque", "Arranque rápido", profiles=BASIC + ("juegos",), admin=True,
        regs=[RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Personalization",
                        "NoLockScreen", 1)],
    ),
    Tweak(
        "boot_ux", "Arranque sin animación del logo",
        "Desactiva la animación de carga del arranque. Ahorra un par de segundos.",
        "Arranque", "Arranque rápido", profiles=("juegos",), admin=True,
        regs=[RegChange("HKLM", r"SYSTEM\CurrentControlSet\Control\BootControl",
                        "BootProgressAnimation", 0)],
    ),
    Tweak(
        "search_index", "Indexado de búsqueda en modo ligero",
        "El servicio Windows Search indexa archivos constantemente y usa disco y RAM. Lo pasa a "
        "inicio manual (sigue funcionando cuando buscas).",
        "Arranque", "Menos disco", profiles=("estudio", "presentaciones", "videos", "apps", "bateria"),
        admin=True, services=[ServiceChange("WSearch", 3)],
    ),
    # ---------------- Juegos ----------------
    Tweak(
        "game_mode", "Activar Modo Juego",
        "Windows prioriza el juego que tienes abierto y frena actualizaciones mientras juegas.",
        "Juegos", "Más FPS", profiles=("juegos",),
        regs=[RegChange("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1)],
    ),
    Tweak(
        "game_dvr", "Desactivar grabación Xbox Game Bar (Game DVR)",
        "La grabación en segundo plano de Xbox Game Bar consume GPU constantemente aunque no grabes.",
        "Juegos", "Menos GPU", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[
            RegChange("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0),
            RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0),
        ],
    ),
    Tweak(
        "gpu_scheduling", "Programación de GPU acelerada por hardware",
        "Deja que la GPU gestione su propia memoria. Menos latencia en juegos (requiere GPU compatible y reinicio).",
        "Juegos", "Más FPS", profiles=("juegos",), admin=True, reboot=True,
        regs=[RegChange("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 2)],
    ),
    Tweak(
        "multimedia_profile", "Priorizar juegos y multimedia",
        "Da más prioridad de CPU a juegos y reproducción de video sobre tareas de fondo.",
        "Juegos", "Más FPS", profiles=("juegos", "videos"), admin=True,
        regs=[
            RegChange("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                      "SystemResponsiveness", 10),
            RegChange("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
                      "GPU Priority", 8),
            RegChange("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games",
                      "Priority", 6),
        ],
    ),
    Tweak(
        "mouse_accel", "Desactivar aceleración del mouse",
        "Movimiento del mouse 1:1, más preciso para apuntar en juegos.",
        "Juegos", "Precisión", profiles=("juegos",),
        regs=[
            RegChange("HKCU", r"Control Panel\Mouse", "MouseSpeed", "0", "SZ"),
            RegChange("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "0", "SZ"),
            RegChange("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "0", "SZ"),
        ],
    ),
    # ---------------- Privacidad ----------------
    Tweak(
        "telemetry", "Desactivar telemetría de Windows",
        "Detiene el servicio que envía datos de diagnóstico a Microsoft (DiagTrack). Menos CPU y disco en segundo plano.",
        "Privacidad", "Menos CPU", profiles=BASIC + ("juegos", "bateria"), admin=True,
        regs=[RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                        "AllowTelemetry", 0)],
        services=[ServiceChange("DiagTrack", 4)],
    ),
    Tweak(
        "activity_history", "Desactivar historial de actividad",
        "Windows deja de registrar todo lo que abres (Timeline).",
        "Privacidad", "Menos disco", profiles=BASIC + ("bateria",), admin=True,
        regs=[
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed", 0),
            RegChange("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", 0),
        ],
    ),
    Tweak(
        "ad_id", "Desactivar ID de publicidad",
        "Las apps dejan de usar tu identificador de publicidad.",
        "Privacidad", "Privacidad", profiles=BASIC,
        regs=[RegChange("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0)],
    ),
]

TWEAKS_BY_ID = {t.id: t for t in TWEAKS}


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------

def _service_start(name: str) -> int | None:
    val = reg_get("HKLM", rf"SYSTEM\CurrentControlSet\Services\{name}", "Start")
    return val[0] if val else None


def _set_service(name: str, start: int) -> bool:
    mode = {2: "auto", 3: "demand", 4: "disabled"}[start]
    code, _ = run(["sc", "config", name, "start=", mode])
    if start == 4:
        run(["sc", "stop", name])
    elif start == 2:
        run(["sc", "start", name])
    return code == 0


def is_applied(tweak: Tweak) -> bool:
    if not IS_WINDOWS:
        return False
    if tweak.custom_check:
        try:
            return tweak.custom_check()
        except Exception:
            return False
    checks = []
    for r in tweak.regs:
        if not r.check:
            continue
        cur = reg_get(r.hive, r.path, r.name)
        checks.append(cur is not None and cur[0] == r.value)
    for s in tweak.services:
        start = _service_start(s.name)
        # Si el servicio no existe en este Windows lo damos por aplicado.
        checks.append(start is None or start == s.start)
    return bool(checks) and all(checks)


def apply(tweak: Tweak) -> tuple[bool, str]:
    """Aplica una optimización guardando un respaldo de los valores previos."""
    if not IS_WINDOWS:
        return False, "Solo disponible en Windows"
    backups = load_json(BACKUP_FILE, {})
    backup = backups.get(tweak.id, {})
    first_time = "regs" not in backup

    if first_time:
        backup["regs"] = []
        for r in tweak.regs:
            cur = reg_get(r.hive, r.path, r.name)
            backup["regs"].append({
                "hive": r.hive, "path": r.path, "name": r.name,
                "exists": cur is not None,
                "value": (cur[0].hex() if isinstance(cur[0], bytes) else cur[0]) if cur else None,
                "type": cur[1] if cur else None,
                "is_bytes": bool(cur and isinstance(cur[0], bytes)),
            })
        backup["services"] = {s.name: _service_start(s.name) for s in tweak.services}

    ok = True
    if tweak.custom_apply:
        ok = tweak.custom_apply(backup)
    else:
        for r in tweak.regs:
            ok &= reg_set(r.hive, r.path, r.name, r.value, r.type)
    for s in tweak.services:
        if _service_start(s.name) is not None:
            ok &= _set_service(s.name, s.start)
    for cmd in tweak.after:
        run(cmd.split())

    backups[tweak.id] = backup
    save_json(BACKUP_FILE, backups)
    if not ok:
        hint = " (ejecuta el programa como administrador)" if tweak.admin else ""
        return False, f"No se pudo aplicar por completo '{tweak.name}'{hint}"
    msg = f"'{tweak.name}' aplicada"
    if tweak.reboot:
        msg += " (requiere reiniciar)"
    return True, msg


def revert(tweak: Tweak) -> tuple[bool, str]:
    """Restaura los valores originales guardados en el respaldo."""
    if not IS_WINDOWS:
        return False, "Solo disponible en Windows"
    backups = load_json(BACKUP_FILE, {})
    backup = backups.get(tweak.id)
    if backup is None:
        return False, f"No hay respaldo de '{tweak.name}'"

    ok = True
    if tweak.custom_revert:
        ok = tweak.custom_revert(backup)
    else:
        for r in backup.get("regs", []):
            if not r["exists"]:
                ok &= reg_delete(r["hive"], r["path"], r["name"])
            else:
                value = bytes.fromhex(r["value"]) if r.get("is_bytes") else r["value"]
                ok &= reg_set(r["hive"], r["path"], r["name"], value, r["type"])
    for name, start in (backup.get("services") or {}).items():
        if start is not None:
            ok &= _set_service(name, start)

    del backups[tweak.id]
    save_json(BACKUP_FILE, backups)
    return ok, (f"'{tweak.name}' revertida" if ok else f"'{tweak.name}' revertida parcialmente")


def create_restore_point() -> tuple[bool, str]:
    """Crea un punto de restauración del sistema antes de hacer cambios."""
    if not IS_WINDOWS:
        return False, "Solo disponible en Windows"
    script = (
        "Enable-ComputerRestore -Drive $env:SystemDrive -ErrorAction SilentlyContinue;"
        "New-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\SystemRestore' "
        "-Name SystemRestorePointCreationFrequency -Value 0 -PropertyType DWord -Force | Out-Null;"
        "Checkpoint-Computer -Description 'Optimizador' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop;"
        "'OK'"
    )
    code, out = powershell(script, timeout=180)
    if code == 0 and "OK" in out:
        return True, "Punto de restauración creado"
    return False, "No se pudo crear el punto de restauración (requiere administrador)"


def tweaks_for_profile(profile: str) -> list[Tweak]:
    return [t for t in TWEAKS if profile in t.profiles]
