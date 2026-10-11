"""Utilidades de bajo nivel para Windows: PowerShell, registro, permisos.

Todo está protegido para que el programa pueda importarse (y probarse) en
otros sistemas operativos sin fallar; en ese caso las funciones devuelven
valores vacíos.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg  # type: ignore

    CREATE_NO_WINDOW = 0x08000000
    HIVES = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    REG_TYPES = {
        "DWORD": winreg.REG_DWORD,
        "SZ": winreg.REG_SZ,
        "BINARY": winreg.REG_BINARY,
    }
else:  # pragma: no cover - solo para desarrollo fuera de Windows
    winreg = None
    CREATE_NO_WINDOW = 0
    HIVES = {}
    REG_TYPES = {}


def data_dir() -> Path:
    """Carpeta donde se guardan respaldos y ajustes."""
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / "Optimizador"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(name: str, default):
    path = data_dir() / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(name: str, data) -> None:
    path = data_dir() / name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------
# Permisos de administrador
# --------------------------------------------------------------------------

def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> bool:
    """Vuelve a abrir el programa pidiendo permisos de administrador (UAC).

    Devuelve True si se lanzó la nueva instancia elevada.
    """
    if not IS_WINDOWS:
        return False
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe = sys.executable
        params = " ".join(f'"{a}"' for a in [os.path.abspath(sys.argv[0]), *sys.argv[1:]])
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32


# --------------------------------------------------------------------------
# Ejecución de comandos
# --------------------------------------------------------------------------

def run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    """Ejecuta un comando sin abrir ventana. Devuelve (código, salida)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    out = proc.stdout or b""
    err = proc.stderr or b""
    text = _decode(out) + _decode(err)
    return proc.returncode, text.strip()


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp850", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def powershell(script: str, timeout: int = 60) -> tuple[int, str]:
    if not IS_WINDOWS:
        return 1, "PowerShell solo está disponible en Windows"
    prefix = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;$ProgressPreference='SilentlyContinue';"
    return run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-Command", prefix + script],
        timeout=timeout,
    )


def powershell_json(script: str, timeout: int = 60):
    """Ejecuta un script que termina en ConvertTo-Json y devuelve el objeto."""
    code, out = powershell(script, timeout=timeout)
    if code != 0 or not out:
        return None
    start = min((i for i in (out.find("{"), out.find("[")) if i >= 0), default=-1)
    if start < 0:
        return None
    try:
        return json.loads(out[start:])
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Registro de Windows
# --------------------------------------------------------------------------

_MISSING = object()


def reg_get(hive: str, path: str, name: str):
    """Lee un valor del registro. Devuelve (valor, tipo) o None si no existe."""
    if not IS_WINDOWS:
        return None
    try:
        with winreg.OpenKey(HIVES[hive], path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            value, typ = winreg.QueryValueEx(key, name)
            return value, typ
    except OSError:
        return None


def reg_set(hive: str, path: str, name: str, value, typ: str | int = "DWORD") -> bool:
    if not IS_WINDOWS:
        return False
    reg_type = REG_TYPES[typ] if isinstance(typ, str) else typ
    try:
        with winreg.CreateKeyEx(HIVES[hive], path, 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, name, 0, reg_type, value)
        return True
    except OSError:
        return False


def reg_delete(hive: str, path: str, name: str) -> bool:
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(HIVES[hive], path, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.DeleteValue(key, name)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def reg_values(hive: str, path: str, wow64_32: bool = False) -> dict:
    """Devuelve todos los valores de una clave como {nombre: valor}."""
    if not IS_WINDOWS:
        return {}
    flags = winreg.KEY_READ | (winreg.KEY_WOW64_32KEY if wow64_32 else winreg.KEY_WOW64_64KEY)
    result = {}
    try:
        with winreg.OpenKey(HIVES[hive], path, 0, flags) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                except OSError:
                    break
                result[name] = value
                i += 1
    except OSError:
        pass
    return result
