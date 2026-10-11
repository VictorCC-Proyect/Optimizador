"""Liberación de RAM, lista de procesos y limpieza de archivos temporales."""

from __future__ import annotations

import ctypes
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

from .winutils import IS_WINDOWS

# Procesos del sistema que nunca se deben cerrar desde la app
PROTECTED = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe",
    "fontdrvhost.exe", "memory compression", "sihost.exe", "ctfmon.exe", "audiodg.exe",
    "securityhealthservice.exe", "msmpeng.exe", "spoolsv.exe", "taskhostw.exe",
    "runtimebroker.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe",
    "searchhost.exe", "textinputhost.exe", "conhost.exe", "wudfhost.exe", "lsaiso.exe",
}

# Nombres amigables para procesos comunes
FRIENDLY = {
    "msedge.exe": "Microsoft Edge", "chrome.exe": "Google Chrome", "firefox.exe": "Firefox",
    "opera.exe": "Opera", "brave.exe": "Brave", "winword.exe": "Word",
    "powerpnt.exe": "PowerPoint", "excel.exe": "Excel", "onenote.exe": "OneNote",
    "onedrive.exe": "OneDrive", "teams.exe": "Teams", "ms-teams.exe": "Teams",
    "discord.exe": "Discord", "spotify.exe": "Spotify", "steam.exe": "Steam",
    "steamwebhelper.exe": "Steam (navegador interno)", "epicgameslauncher.exe": "Epic Games",
    "dwm.exe": "Administrador de ventanas (efectos visuales)", "msmpeng.exe": "Antivirus Defender",
    "searchhost.exe": "Búsqueda de Windows", "widgets.exe": "Widgets",
    "phoneexperiencehost.exe": "Enlace móvil", "notion.exe": "Notion",
    "whatsapp.exe": "WhatsApp", "zoom.exe": "Zoom", "code.exe": "VS Code",
}


@dataclass
class ProcInfo:
    pid: int
    name: str
    friendly: str
    ram_mb: float
    count: int = 1
    gpu: float = 0.0

    @property
    def protected(self) -> bool:
        return self.name.lower() in PROTECTED


def top_processes(limit: int = 15, gpu_by_pid: dict[int, float] | None = None) -> list[ProcInfo]:
    """Procesos agrupados por nombre y ordenados por uso de RAM."""
    gpu_by_pid = gpu_by_pid or {}
    groups: dict[str, ProcInfo] = {}
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            name = p.info["name"] or "?"
            mem = p.info["memory_info"]
            if mem is None:
                continue
            # 'private' se parece más a lo que muestra el Administrador de tareas
            ram = getattr(mem, "private", 0) or mem.rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        key = name.lower()
        info = groups.get(key)
        if info is None:
            groups[key] = ProcInfo(p.info["pid"], name, FRIENDLY.get(key, name),
                                   ram / 1024 ** 2, 1, gpu_by_pid.get(p.info["pid"], 0.0))
        else:
            info.ram_mb += ram / 1024 ** 2
            info.count += 1
            info.gpu += gpu_by_pid.get(p.info["pid"], 0.0)
    return sorted(groups.values(), key=lambda i: i.ram_mb, reverse=True)[:limit]


def kill_by_name(name: str) -> int:
    """Cierra todas las instancias de un programa. Devuelve cuántas se cerraron."""
    if name.lower() in PROTECTED:
        return 0
    killed = 0
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() == name.lower():
                p.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


def free_ram() -> tuple[float, float]:
    """Recorta la memoria de trabajo de todos los procesos (EmptyWorkingSet).

    Es lo mismo que hacen herramientas como Hone o Wise Memory Optimizer: la
    memoria que los programas no están usando activamente se devuelve a
    Windows. Devuelve (MB liberados, % de RAM en uso después).
    """
    before = psutil.virtual_memory().used
    if IS_WINDOWS:
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.OpenProcess.restype = ctypes.c_void_p
        access = 0x0400 | 0x0100  # PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
        own = os.getpid()
        for pid in psutil.pids():
            if pid in (0, 4, own):
                continue
            handle = kernel32.OpenProcess(access, False, pid)
            if handle:
                psapi.EmptyWorkingSet(ctypes.c_void_p(handle))
                kernel32.CloseHandle(ctypes.c_void_p(handle))
        time.sleep(0.5)
    after = psutil.virtual_memory()
    freed = max(0.0, (before - after.used) / 1024 ** 2)
    return freed, after.percent


def _dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def temp_folders() -> list[Path]:
    folders = []
    for env in ("TEMP", "TMP"):
        val = os.environ.get(env)
        if val:
            folders.append(Path(val))
    if IS_WINDOWS:
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        folders += [windir / "Temp", windir / "SoftwareDistribution" / "Download"]
        local = os.environ.get("LOCALAPPDATA")
        if local:
            folders += [Path(local) / "Microsoft" / "Windows" / "INetCache",
                        Path(local) / "CrashDumps",
                        Path(local) / "D3DSCache"]
    seen, unique = set(), []
    for f in folders:
        key = str(f).lower()
        if key not in seen and f.exists():
            seen.add(key)
            unique.append(f)
    return unique


def clean_temp() -> float:
    """Borra archivos temporales (los que estén en uso se omiten). Devuelve MB liberados."""
    folders = temp_folders()
    before = sum(_dir_size(f) for f in folders)
    for folder in folders:
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir() and not entry.is_symlink():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink()
            except OSError:
                continue  # archivo en uso: se deja
    after = sum(_dir_size(f) for f in folders)
    return max(0, before - after) / 1024 ** 2


def temp_size_mb() -> float:
    return sum(_dir_size(f) for f in temp_folders()) / 1024 ** 2
