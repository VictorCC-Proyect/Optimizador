"""Detección automática de las especificaciones de la laptop."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field

import psutil

from .winutils import IS_WINDOWS, powershell_json

_SPECS_SCRIPT = r"""
$r = [ordered]@{}
try { $cs = Get-CimInstance Win32_ComputerSystem
      $r.manufacturer = $cs.Manufacturer; $r.model = $cs.Model
      $r.pc_system_type = [int]$cs.PCSystemType } catch {}
try { $p = Get-CimInstance Win32_Processor | Select-Object -First 1
      $r.cpu = $p.Name.Trim(); $r.cpu_max_mhz = [int]$p.MaxClockSpeed } catch {}
try { $r.gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object {
        [ordered]@{ name = $_.Name; driver = $_.DriverVersion; ram = [int64]$_.AdapterRAM } }) } catch {}
try { $r.gpu_vram = @(Get-ItemProperty 'HKLM:\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*' -ErrorAction SilentlyContinue |
        Where-Object { $_.'HardwareInformation.qwMemorySize' } | ForEach-Object {
        [ordered]@{ name = $_.DriverDesc; bytes = [int64]$_.'HardwareInformation.qwMemorySize' } }) } catch {}
try { $r.disks = @(Get-PhysicalDisk | ForEach-Object {
        [ordered]@{ name = $_.FriendlyName; media = [string]$_.MediaType; bus = [string]$_.BusType; size = [int64]$_.Size } }) } catch {}
try { $m = @(Get-CimInstance Win32_PhysicalMemory)
      $r.ram_modules = $m.Count; $r.ram_speed = [int]($m | Measure-Object -Property Speed -Maximum).Maximum
      $arr = Get-CimInstance Win32_PhysicalMemoryArray | Select-Object -First 1
      $r.ram_slots = [int]$arr.MemoryDevices } catch {}
try { $os = Get-CimInstance Win32_OperatingSystem
      $r.os = $os.Caption; $r.os_build = $os.BuildNumber } catch {}
try { $b = Get-CimInstance Win32_Battery | Select-Object -First 1
      if ($b) { $r.has_battery = $true } else { $r.has_battery = $false } } catch {}
try { $e = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=100} -MaxEvents 1 -ErrorAction Stop
      $x = [xml]$e.ToXml()
      $r.boot_ms = [int]($x.Event.EventData.Data | Where-Object { $_.Name -eq 'BootTime' }).'#text'
      $r.boot_post_ms = [int]($x.Event.EventData.Data | Where-Object { $_.Name -eq 'MainPathBootTime' }).'#text' } catch {}
try { $r.fast_startup = [int](Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power' -Name HiberbootEnabled -ErrorAction Stop).HiberbootEnabled } catch {}
$r | ConvertTo-Json -Depth 4 -Compress
"""


@dataclass
class GPU:
    name: str
    vram_gb: float = 0.0
    dedicated: bool = False


@dataclass
class Disk:
    name: str
    media: str  # "SSD", "HDD" o "Desconocido"
    bus: str
    size_gb: float


@dataclass
class SystemSpecs:
    manufacturer: str = "Desconocido"
    model: str = "Desconocido"
    is_laptop: bool = True
    cpu: str = "Desconocido"
    cpu_cores: int = 0
    cpu_threads: int = 0
    cpu_max_mhz: int = 0
    ram_gb: float = 0.0
    ram_speed: int = 0
    ram_modules: int = 0
    ram_slots: int = 0
    gpus: list[GPU] = field(default_factory=list)
    disks: list[Disk] = field(default_factory=list)
    os: str = platform.platform()
    os_build: str = ""
    boot_seconds: float | None = None
    fast_startup: bool | None = None

    # ---------------- propiedades derivadas ----------------
    @property
    def has_dedicated_gpu(self) -> bool:
        return any(g.dedicated for g in self.gpus)

    @property
    def has_ssd(self) -> bool:
        return any(d.media == "SSD" for d in self.disks)

    @property
    def only_hdd(self) -> bool:
        return bool(self.disks) and all(d.media == "HDD" for d in self.disks)

    @property
    def single_channel_ram(self) -> bool:
        return self.ram_modules == 1

    @property
    def gpu_summary(self) -> str:
        return " + ".join(g.name for g in self.gpus) or "Desconocida"

    @property
    def disk_summary(self) -> str:
        return ", ".join(f"{d.media} {d.size_gb:.0f} GB" for d in self.disks) or "Desconocido"


_DEDICATED_HINTS = ("nvidia", "geforce", "rtx", "gtx", "quadro", "radeon rx", "radeon pro",
                    "arc a", "radeon(tm) rx")
_INTEGRATED_HINTS = ("intel(r) uhd", "intel(r) hd", "iris", "vega", "radeon(tm) graphics",
                     "radeon graphics", "basic display", "microsoft basic")


def _is_dedicated(name: str, vram_gb: float) -> bool:
    low = name.lower()
    if any(h in low for h in _INTEGRATED_HINTS):
        return False
    if any(h in low for h in _DEDICATED_HINTS):
        return True
    return vram_gb >= 2


def detect_specs() -> SystemSpecs:
    """Detecta el hardware. En Windows usa WMI vía PowerShell + psutil."""
    specs = SystemSpecs()
    specs.cpu_cores = psutil.cpu_count(logical=False) or 0
    specs.cpu_threads = psutil.cpu_count(logical=True) or 0
    specs.ram_gb = round(psutil.virtual_memory().total / 1024 ** 3, 1)
    specs.cpu = platform.processor() or specs.cpu

    if not IS_WINDOWS:
        specs.is_laptop = psutil.sensors_battery() is not None if hasattr(psutil, "sensors_battery") else False
        return specs

    data = powershell_json(_SPECS_SCRIPT, timeout=45) or {}
    specs.manufacturer = (data.get("manufacturer") or specs.manufacturer).strip()
    specs.model = (data.get("model") or specs.model).strip()
    specs.cpu = data.get("cpu") or specs.cpu
    specs.cpu_max_mhz = data.get("cpu_max_mhz") or 0
    specs.ram_speed = data.get("ram_speed") or 0
    specs.ram_modules = data.get("ram_modules") or 0
    specs.ram_slots = data.get("ram_slots") or 0
    specs.os = data.get("os") or specs.os
    specs.os_build = str(data.get("os_build") or "")
    specs.is_laptop = data.get("pc_system_type") == 2 or bool(data.get("has_battery"))
    if data.get("boot_ms"):
        specs.boot_seconds = round(data["boot_ms"] / 1000, 1)
    if data.get("fast_startup") is not None:
        specs.fast_startup = bool(data["fast_startup"])

    # AdapterRAM de WMI está limitado a 4 GB; el registro da el valor real.
    vram_reg = {v.get("name"): v.get("bytes", 0) for v in data.get("gpu_vram") or []}
    for g in data.get("gpus") or []:
        name = (g.get("name") or "GPU").strip()
        vram = vram_reg.get(name) or g.get("ram") or 0
        vram_gb = round(max(vram, 0) / 1024 ** 3, 1)
        specs.gpus.append(GPU(name=name, vram_gb=vram_gb, dedicated=_is_dedicated(name, vram_gb)))

    for d in data.get("disks") or []:
        media = d.get("media") or ""
        bus = d.get("bus") or ""
        if media not in ("SSD", "HDD"):
            media = "SSD" if bus.upper() == "NVME" else "Desconocido"
        specs.disks.append(Disk(
            name=(d.get("name") or "Disco").strip(),
            media=media,
            bus=bus,
            size_gb=round((d.get("size") or 0) / 1000 ** 3),
        ))
    return specs


# --------------------------------------------------------------------------
# Clasificación del tipo de laptop
# --------------------------------------------------------------------------

LAPTOP_TYPES = {
    "basica": "Gama básica / de entrada",
    "media": "Gama media / oficina",
    "ultrabook": "Ultrabook / ligera",
    "gaming": "Gaming / con GPU dedicada",
    "antigua": "Antigua (con disco duro HDD)",
}


def classify_laptop(specs: SystemSpecs) -> str:
    """Devuelve la clave de LAPTOP_TYPES que mejor describe el equipo."""
    cpu = specs.cpu.lower()
    if specs.only_hdd:
        return "antigua"
    if specs.has_dedicated_gpu:
        return "gaming"
    weak_cpu = any(k in cpu for k in ("celeron", "pentium", "athlon", "atom", "i3-", "ryzen 3",
                                      " n100", " n200", "silver", "gold"))
    if specs.ram_gb and specs.ram_gb <= 8.5 or weak_cpu:
        return "basica"
    if any(k in cpu for k in ("u ", "-u", "ultra", "y ", " m1", " m2")) and specs.ram_gb <= 16.5:
        return "ultrabook"
    return "media"


def diagnose(specs: SystemSpecs) -> list[tuple[str, str]]:
    """Lista de (nivel, mensaje) con los cuellos de botella detectados.

    nivel: "alto", "medio" o "ok".
    """
    out: list[tuple[str, str]] = []
    if specs.only_hdd:
        out.append(("alto", "Tu laptop usa un disco duro mecánico (HDD). Es la causa nº 1 de un "
                            "arranque lento: cambiar a un SSD reduce el encendido de minutos a segundos."))
    elif specs.has_ssd:
        out.append(("ok", "Tienes un SSD: el almacenamiento no es el cuello de botella."))
    if specs.ram_gb and specs.ram_gb <= 4.5:
        out.append(("alto", f"Solo tienes {specs.ram_gb:.0f} GB de RAM. Windows 10/11 usa 3-4 GB por sí "
                            "solo, por eso la RAM llega al 100 %. Ampliar a 8 GB es lo más recomendable."))
    elif specs.ram_gb and specs.ram_gb <= 8.5:
        out.append(("medio", f"Tienes {specs.ram_gb:.0f} GB de RAM: suficiente para tareas básicas si "
                             "controlas los programas de inicio y las pestañas del navegador."))
    if specs.single_channel_ram and specs.ram_slots >= 2:
        out.append(("medio", "La RAM está en un solo módulo (single channel). Añadir un segundo módulo "
                             "igual activa el dual channel y mejora mucho la GPU integrada."))
    if not specs.has_dedicated_gpu and specs.gpus:
        out.append(("medio", "Tu GPU es integrada: comparte la RAM del sistema. Bajar efectos visuales "
                             "y usar aceleración por hardware en el navegador reduce su uso."))
    if specs.boot_seconds and specs.boot_seconds > 60:
        out.append(("alto", f"El último arranque tardó {specs.boot_seconds:.0f} s. Desactiva programas de "
                            "inicio y activa el Inicio rápido en la pestaña 'Arranque'."))
    if specs.fast_startup is False:
        out.append(("medio", "El 'Inicio rápido' de Windows está desactivado."))
    return out
