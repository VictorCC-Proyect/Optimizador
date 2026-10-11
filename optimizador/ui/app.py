"""Ventana principal: barra lateral, navegación, tareas en segundo plano y avisos."""

from __future__ import annotations

import queue
import threading
import time
import traceback

import customtkinter as ctk

from .. import APP_NAME, APP_VERSION, memory, startup, tweaks
from ..monitor import Monitor
from ..system_info import classify_laptop, detect_specs
from ..winutils import IS_WINDOWS, is_admin, load_json, relaunch_as_admin, save_json
from .pages import PAGES, Page
from .widgets import ACCENT, BG, BORDER, CARD_HOVER, GREEN, MUTED, RED, SIDEBAR, TEXT, font

SETTINGS_FILE = "ajustes.json"
DEFAULT_SETTINGS = {
    "profile": "estudio",
    "auto_free_ram": False,
    "ram_threshold": 85,
    "restore_point": True,
}


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1240x780")
        self.minsize(1080, 680)

        self.admin = is_admin()
        self.settings = {**DEFAULT_SETTINGS, **load_json(SETTINGS_FILE, {})}
        self.specs = None
        self.laptop_type = "media"
        self.tweak_states: dict[str, bool] = {}
        self.startup_items = None
        self.monitor = Monitor()
        self._queue: queue.Queue = queue.Queue()
        self._last_auto_free = 0.0
        self._toast_job = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self.container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.pages: dict[str, Page] = {}
        self.current: Page | None = None

        self.toast_lbl = ctk.CTkLabel(self, text="", font=font(13, "bold"), corner_radius=10,
                                      fg_color=CARD_HOVER, text_color=TEXT, height=40)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.monitor.start()
        self.show("Inicio")
        self.after(100, self._poll_queue)
        self.after(1000, self._tick)
        self.after(200, self._initial_load)

    # ------------------------------------------------------------------ UI
    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=210)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)
        ctk.CTkLabel(bar, text="⚡ OPTIMIZADOR", font=font(18, "bold"), text_color=ACCENT,
                     anchor="w").pack(fill="x", padx=20, pady=(22, 18))
        self.nav_buttons = {}
        for icon, cls in PAGES:
            b = ctk.CTkButton(bar, text=f"  {icon}   {cls.title}", anchor="w", height=40,
                              corner_radius=10, fg_color="transparent", hover_color=CARD_HOVER,
                              text_color=MUTED, font=font(14),
                              command=lambda t=cls.title: self.show(t))
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[cls.title] = b

        foot = ctk.CTkFrame(bar, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=16, pady=16)
        color = GREEN if self.admin else RED
        txt = "● Administrador" if self.admin else "● Modo limitado"
        ctk.CTkLabel(foot, text=txt, text_color=color, font=font(12, "bold"), anchor="w").pack(fill="x")
        if IS_WINDOWS and not self.admin:
            ctk.CTkButton(foot, text="Abrir como administrador", height=30, fg_color=ACCENT,
                          hover_color=ACCENT, text_color="#111827", font=font(12, "bold"),
                          command=self.restart_admin).pack(fill="x", pady=(6, 0))

    def show(self, title: str) -> None:
        if title not in self.pages:
            cls = next(c for _, c in PAGES if c.title == title)
            page = cls(self.container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[title] = page
        page = self.pages[title]
        page.tkraise()
        self.current = page
        for t, b in self.nav_buttons.items():
            active = t == title
            b.configure(fg_color=BORDER if active else "transparent",
                        text_color=ACCENT if active else MUTED)
        page.on_show()
        page.tick()

    def toast(self, msg: str, ok: bool = True) -> None:
        self.toast_lbl.configure(text=f"  {'✓' if ok else '✗'}  {msg}  ",
                                 text_color=TEXT if ok else "#fecaca")
        self.toast_lbl.place(relx=0.99, rely=0.98, anchor="se")
        self.toast_lbl.lift()
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(4000, self.toast_lbl.place_forget)

    # ------------------------------------------------------- tareas de fondo
    def run_bg(self, fn, done=None) -> None:
        """Ejecuta fn en un hilo y llama done(resultado) en el hilo de la interfaz."""
        def worker():
            try:
                res = fn()
            except Exception as exc:  # noqa: BLE001 - se informa al usuario
                traceback.print_exc()
                self._queue.put((self.toast, (f"Error: {exc}", False)))
                return
            if done:
                self._queue.put((done, (res,)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self) -> None:
        try:
            while True:
                fn, args = self._queue.get_nowait()
                try:
                    fn(*args)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _tick(self) -> None:
        if self.current:
            try:
                self.current.tick()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        s = self.settings
        if (s.get("auto_free_ram") and self.monitor.ram >= s.get("ram_threshold", 85)
                and time.time() - self._last_auto_free > 120):
            self._last_auto_free = time.time()
            self.run_bg(memory.free_ram, lambda r: self.toast(
                f"RAM alta: se liberaron {r[0]:,.0f} MB automáticamente"))
        self.after(1000, self._tick)

    # ----------------------------------------------------------- datos
    def _initial_load(self) -> None:
        self.detect()
        self.refresh_tweaks()
        self.run_bg(startup.list_startup, self._set_startup)

    def detect(self) -> None:
        def done(specs):
            self.specs = specs
            self.laptop_type = classify_laptop(specs)
            self._refresh_pages()
        self.run_bg(detect_specs, done)

    def refresh_tweaks(self, done=None) -> None:
        def work():
            return {t.id: tweaks.is_applied(t) for t in tweaks.TWEAKS}

        def finish(states):
            self.tweak_states = states
            self._refresh_pages()
            if done:
                done()
        self.run_bg(work, finish)

    def _set_startup(self, items) -> None:
        self.startup_items = items
        self._refresh_pages()

    def _refresh_pages(self) -> None:
        dash = self.pages.get("Inicio")
        if dash:
            dash.refresh_summary()
        if self.current and self.current is not dash:
            self.current.on_show()

    def save_settings(self) -> None:
        save_json(SETTINGS_FILE, self.settings)

    # ---------------------------------------------------------- acciones
    def free_ram(self) -> None:
        self.toast("Liberando RAM…")
        self.run_bg(memory.free_ram, lambda r: self.toast(
            f"Se liberaron {r[0]:,.0f} MB · RAM en uso ahora: {r[1]:.0f} %"))

    def apply_profile(self, profile: str, include_startup: bool = False) -> None:
        self.apply_tweaks(tweaks.tweaks_for_profile(profile), tweaks.PROFILES[profile],
                          include_startup=include_startup)

    def apply_tweaks(self, items, label: str, include_startup: bool = False, on_done=None) -> None:
        if not IS_WINDOWS:
            self.toast("Las optimizaciones solo funcionan en Windows", False)
            return
        pending = [t for t in items if not self.tweak_states.get(t.id) and (self.admin or not t.admin)]
        skipped = sum(1 for t in items if t.admin and not self.admin)
        if not pending and not include_startup:
            self.toast(f"'{label}' ya está optimizado" +
                       (f" ({skipped} requieren administrador)" if skipped else ""))
            return
        self.toast(f"Aplicando {len(pending)} optimizaciones para '{label}'…")

        def work():
            if pending and self.admin and self.settings.get("restore_point", True):
                tweaks.create_restore_point()
            ok = sum(tweaks.apply(t)[0] for t in pending)
            disabled = 0
            if include_startup:
                for it in startup.list_startup():
                    if it.enabled and it.impact == "Alto" and not it.keep:
                        if it.source in ("HKCU", "Carpeta usuario") or self.admin:
                            disabled += startup.set_enabled(it, False)
            return ok, disabled

        def done(res):
            ok, disabled = res
            msg = f"{ok} optimizaciones aplicadas"
            if disabled:
                msg += f" · {disabled} programas de inicio desactivados"
            if skipped:
                msg += f" · {skipped} requieren administrador"
            if any(t.reboot or t.category == "Arranque" for t in pending):
                msg += " · reinicia para notar todo el efecto"
            self.toast(msg)
            self.refresh_tweaks(on_done)
            self.run_bg(startup.list_startup, self._set_startup)

        self.run_bg(work, done)

    def restart_admin(self) -> None:
        if relaunch_as_admin():
            self.on_close()

    def on_close(self) -> None:
        self.monitor.stop()
        self.destroy()


def main() -> None:
    App().mainloop()
