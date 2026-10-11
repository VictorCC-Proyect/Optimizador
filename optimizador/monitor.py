"""Monitor en segundo plano de CPU, RAM y GPU."""

from __future__ import annotations

import json
import subprocess
import threading
import time
from collections import deque

import psutil

from .winutils import CREATE_NO_WINDOW, IS_WINDOWS

# Un solo proceso de PowerShell que se queda abierto e informa la GPU cada
# 2 segundos (lanzar uno nuevo cada vez gastaría más CPU que lo que mide).
# Se usan las clases WMI de contadores porque, a diferencia de Get-Counter,
# sus nombres no cambian con el idioma de Windows.
_GPU_LOOP = r"""
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
while ($true) {
  try {
    $eng = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop
    $byType = @{}; $byPid = @{}
    foreach ($e in $eng) {
      if ($e.Name -match 'pid_(\d+)_.*engtype_(\w+)') {
        $procId = $matches[1]; $t = $matches[2]; $u = [double]$e.UtilizationPercentage
        $byType[$t] = [double]$byType[$t] + $u
        $k = "$procId|$t"; $byPid[$k] = [double]$byPid[$k] + $u
      }
    }
    $total = 0; foreach ($v in $byType.Values) { if ($v -gt $total) { $total = $v } }
    $procs = @{}
    foreach ($k in $byPid.Keys) {
      $procId = $k.Split('|')[0]
      if ($byPid[$k] -gt [double]$procs[$procId]) { $procs[$procId] = [math]::Round($byPid[$k], 1) }
    }
    $mem = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUAdapterMemory -ErrorAction SilentlyContinue
    $ded = ($mem | Measure-Object DedicatedUsage -Sum).Sum
    $sha = ($mem | Measure-Object SharedUsage -Sum).Sum
    @{ gpu = [math]::Min(100, [math]::Round($total, 1)); procs = $procs; ded = $ded; shared = $sha } |
      ConvertTo-Json -Compress
  } catch { '{"gpu":null}' }
  Start-Sleep -Seconds 2
}
"""


class Monitor:
    def __init__(self, history: int = 60):
        self.cpu = 0.0
        self.ram = 0.0
        self.ram_used_gb = 0.0
        self.ram_total_gb = psutil.virtual_memory().total / 1024 ** 3
        self.gpu: float | None = None
        self.gpu_mem_gb = 0.0
        self.gpu_by_pid: dict[int, float] = {}
        self.cpu_hist: deque[float] = deque([0.0] * history, maxlen=history)
        self.ram_hist: deque[float] = deque([0.0] * history, maxlen=history)
        self.gpu_hist: deque[float] = deque([0.0] * history, maxlen=history)
        self._stop = threading.Event()
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        psutil.cpu_percent(None)
        threading.Thread(target=self._loop, daemon=True).start()
        if IS_WINDOWS:
            threading.Thread(target=self._gpu_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        if self._proc and self._proc.poll() is None:
            self._proc.kill()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.cpu = psutil.cpu_percent(None)
            vm = psutil.virtual_memory()
            self.ram = vm.percent
            self.ram_used_gb = (vm.total - vm.available) / 1024 ** 3
            self.cpu_hist.append(self.cpu)
            self.ram_hist.append(self.ram)
            self.gpu_hist.append(self.gpu or 0.0)
            self._stop.wait(1.5)

    def _gpu_loop(self) -> None:
        try:
            self._proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", _GPU_LOOP],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError:
            return
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            if self._stop.is_set():
                break
            try:
                data = json.loads(raw.decode("utf-8", errors="replace").strip() or "{}")
            except ValueError:
                continue
            if data.get("gpu") is None:
                continue
            self.gpu = float(data["gpu"])
            self.gpu_mem_gb = ((data.get("ded") or 0) + (data.get("shared") or 0)) / 1024 ** 3
            self.gpu_by_pid = {int(k): float(v) for k, v in (data.get("procs") or {}).items()}

    def wait_first_sample(self, timeout: float = 2.0) -> None:
        end = time.time() + timeout
        while time.time() < end and self.ram == 0:
            time.sleep(0.1)
