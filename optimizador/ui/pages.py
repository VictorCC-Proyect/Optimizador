"""Páginas de la aplicación."""

from __future__ import annotations

import os
import subprocess

import customtkinter as ctk

from .. import memory, startup, tweaks
from ..recommendations import LAPTOPS, TASKS, personalized
from ..system_info import LAPTOP_TYPES, diagnose
from ..winutils import IS_WINDOWS, data_dir
from .widgets import (ACCENT, BG, BLUE, BORDER, CARD, CARD_HOVER, GREEN, MUTED, ORANGE, RED, TEXT,
                      Badge, Card, LineChart, Muted, Ring, SectionTitle, button, font, switch)

IMPACT_COLORS = {"Alto": RED, "Medio": ORANGE, "Bajo": GREEN}
LEVEL_COLORS = {"alto": RED, "medio": ORANGE, "ok": GREEN}


class Page(ctk.CTkFrame):
    title = ""

    def __init__(self, master, app):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.app = app

    def on_show(self) -> None:
        """Se llama cada vez que se abre la página."""

    def tick(self) -> None:
        """Se llama cada segundo mientras la página está visible."""

    def header(self, title: str, subtitle: str = "") -> ctk.CTkFrame:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=28, pady=(22, 8))
        ctk.CTkLabel(bar, text=title, font=font(24, "bold"), text_color=TEXT,
                     anchor="w").pack(side="left")
        if subtitle:
            Muted(bar, subtitle, 13).pack(side="left", padx=14, pady=(8, 0))
        return bar


# ==========================================================================
# Inicio / Dashboard
# ==========================================================================

class DashboardPage(Page):
    title = "Inicio"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.header("Bienvenido a Optimizador")
        self.model_lbl = Muted(bar, "Detectando tu laptop…", 13)
        self.model_lbl.pack(side="left", padx=14, pady=(8, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(4, 20))
        body.grid_columnconfigure(0, weight=5, uniform="c")
        body.grid_columnconfigure(1, weight=4, uniform="c")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # ---- Puntuación de optimización
        score = Card(left)
        score.pack(fill="x")
        self.score_ring = Ring(score, size=118, width=12, color=ACCENT, label_size=22)
        self.score_ring.pack(side="left", padx=18, pady=16)
        txt = ctk.CTkFrame(score, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, pady=16)
        self.score_title = ctk.CTkLabel(txt, text="Analizando…", font=font(20, "bold"),
                                        text_color=TEXT, anchor="w")
        self.score_title.pack(fill="x")
        self.score_sub = Muted(txt, "", 12, wrap=330)
        self.score_sub.pack(fill="x", pady=(2, 10))
        button(txt, "⚡  Optimizar ahora", self.optimize_now, width=180).pack(anchor="w")

        # ---- Tarjetas de estado
        stats = ctk.CTkFrame(left, fg_color="transparent")
        stats.pack(fill="x", pady=12)
        self.stat_labels = {}
        for i, (key, label, page) in enumerate([
            ("tweaks", "Optimizaciones activas", "Optimizaciones"),
            ("startup", "Programas al iniciar", "Arranque"),
            ("boot", "Último arranque", "Mi laptop"),
        ]):
            stats.grid_columnconfigure(i, weight=1, uniform="s")
            c = Card(stats)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            v = ctk.CTkLabel(c, text="--", font=font(24, "bold"), text_color=TEXT, anchor="w")
            v.pack(fill="x", padx=14, pady=(12, 0))
            Muted(c, label, 12).pack(fill="x", padx=14)
            button(c, "Ver", lambda p=page: app.show(p), primary=False, height=28,
                   font=font(12)).pack(fill="x", padx=14, pady=(8, 12))
            self.stat_labels[key] = v

        # ---- Acciones rápidas
        SectionTitle(left, "Acciones rápidas", 15).pack(fill="x", pady=(4, 6))
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(fill="x")
        for i, (txt_, cmd) in enumerate([
            ("🧹  Liberar RAM", self.free_ram),
            ("🗑  Limpiar temporales", self.clean_temp),
            ("📈  Ver procesos", lambda: app.show("Procesos")),
        ]):
            actions.grid_columnconfigure(i, weight=1, uniform="a")
            button(actions, txt_, cmd, primary=False, height=40).grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 0 if i == 2 else 5))

        # ---- Diagnóstico
        SectionTitle(left, "Diagnóstico de tu laptop", 15).pack(fill="x", pady=(16, 6))
        self.diag = ctk.CTkScrollableFrame(left, fg_color=CARD, corner_radius=12, height=140)
        self.diag.pack(fill="both", expand=True)
        Muted(self.diag, "Analizando hardware…").pack(fill="x", padx=8, pady=8)

        # ---- CPU
        cpu = Card(right)
        cpu.pack(fill="x")
        Muted(cpu, "USO DE CPU", 11).pack(anchor="w", padx=16, pady=(12, 0))
        row = ctk.CTkFrame(cpu, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self.cpu_chart = LineChart(row, width=220, height=110)
        self.cpu_chart.pack(side="left", fill="x", expand=True, padx=(4, 10))
        self.cpu_ring = Ring(row, size=110, width=11)
        self.cpu_ring.pack(side="right")

        # ---- GPU y RAM
        gr = ctk.CTkFrame(right, fg_color="transparent")
        gr.pack(fill="x", pady=12)
        gr.grid_columnconfigure((0, 1), weight=1, uniform="g")
        self.gpu_ring, self.gpu_sub = self._usage_card(gr, 0, "USO DE GPU", BLUE)
        self.ram_ring, self.ram_sub = self._usage_card(gr, 1, "USO DE RAM", None)

        # ---- Atajos
        SectionTitle(right, "Atajos", 15).pack(fill="x", pady=(0, 6))
        sc = ctk.CTkFrame(right, fg_color="transparent")
        sc.pack(fill="x")
        for i, (icon, label, page) in enumerate([
            ("⚡", "Arranque", "Arranque"), ("🎯", "Por tarea", "Por tarea"),
            ("💻", "Mi laptop", "Mi laptop"), ("🧭", "Por laptop", "Tipos de laptop"),
        ]):
            sc.grid_columnconfigure(i, weight=1, uniform="sc")
            b = ctk.CTkButton(sc, text=f"{icon}\n{label}", command=lambda p=page: app.show(p),
                              fg_color=CARD, hover_color=CARD_HOVER, text_color=TEXT,
                              font=font(12, "bold"), height=78, corner_radius=12)
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0 if i == 3 else 4))

    def _usage_card(self, parent, col, title, color):
        c = Card(parent)
        c.grid(row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0))
        Muted(c, title, 11).pack(anchor="w", padx=16, pady=(12, 4))
        ring = Ring(c, size=112, width=11, color=color)
        ring.pack(pady=4)
        sub = Muted(c, "", 11, anchor="center")
        sub.pack(pady=(0, 12))
        return ring, sub

    # ---------------- datos ----------------
    def on_show(self) -> None:
        self.refresh_summary()

    def refresh_summary(self) -> None:
        app = self.app
        specs = app.specs
        if specs:
            self.model_lbl.configure(text=f"{specs.manufacturer} {specs.model}".strip())
            boot = f"{specs.boot_seconds:.0f} s" if specs.boot_seconds else "N/D"
            self.stat_labels["boot"].configure(text=boot)
            for w in self.diag.winfo_children():
                w.destroy()
            items = diagnose(specs) or [("ok", "No se detectaron problemas de hardware.")]
            for level, msg in items:
                row = ctk.CTkFrame(self.diag, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=4)
                ctk.CTkLabel(row, text="●", text_color=LEVEL_COLORS[level], font=font(14),
                             width=18).pack(side="left", anchor="n")
                Muted(row, msg, 12, wrap=470).pack(side="left", fill="x", expand=True)

        states = app.tweak_states
        if states:
            active = sum(states.values())
            self.stat_labels["tweaks"].configure(text=f"{active}/{len(states)}")
            rec = tweaks.tweaks_for_profile(app.settings.get("profile", "estudio"))
            done = sum(1 for t in rec if states.get(t.id))
            pct = 100 * done / len(rec) if rec else 100
            self.score_ring.set(pct)
            if pct >= 99:
                self.score_title.configure(text=f"{pct:.0f}% optimizado")
                self.score_sub.configure(text="Tu laptop ya tiene todas las optimizaciones recomendadas "
                                              "para tu perfil.")
            else:
                self.score_title.configure(text=f"{pct:.0f}% optimizado")
                self.score_sub.configure(
                    text=f"Faltan {len(rec) - done} optimizaciones recomendadas para "
                         f"'{tweaks.PROFILES[app.settings.get('profile', 'estudio')]}'.")
        if app.startup_items is not None:
            on = sum(1 for i in app.startup_items if i.enabled)
            self.stat_labels["startup"].configure(text=str(on))

    def tick(self) -> None:
        m = self.app.monitor
        self.cpu_chart.set(m.cpu_hist)
        self.cpu_ring.set(m.cpu)
        self.ram_ring.set(m.ram)
        self.ram_sub.configure(text=f"{m.ram_used_gb:.1f} / {m.ram_total_gb:.1f} GB")
        if m.gpu is None:
            self.gpu_ring.set(None, "N/D" if not IS_WINDOWS else "…")
            self.gpu_sub.configure(text="Midiendo…" if IS_WINDOWS else "Solo en Windows")
        else:
            self.gpu_ring.set(m.gpu)
            self.gpu_sub.configure(text=f"Memoria GPU: {m.gpu_mem_gb:.1f} GB")

    # ---------------- acciones ----------------
    def optimize_now(self) -> None:
        self.app.apply_profile(self.app.settings.get("profile", "estudio"), include_startup=True)

    def free_ram(self) -> None:
        self.app.free_ram()

    def clean_temp(self) -> None:
        self.app.toast("Limpiando archivos temporales…")
        self.app.run_bg(memory.clean_temp,
                        lambda mb: self.app.toast(f"Se liberaron {mb:,.0f} MB de archivos temporales"))


# ==========================================================================
# Optimizaciones
# ==========================================================================

class TweakRow(Card):
    def __init__(self, master, page: "TweaksPage", tweak: tweaks.Tweak):
        super().__init__(master)
        self.page, self.tweak = page, tweak
        self.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkLabel(top, text=tweak.name, font=font(14, "bold"), text_color=TEXT,
                     anchor="w").pack(side="left")
        Badge(top, tweak.impact, color=BORDER, text_color_=TEXT).pack(side="left", padx=(10, 0))
        if tweak.admin:
            Badge(top, "Admin", color="#7c3aed").pack(side="left", padx=(6, 0))
        if tweak.reboot:
            Badge(top, "Reinicio", color=ORANGE).pack(side="left", padx=(6, 0))
        Muted(self, tweak.description, 12, wrap=640).grid(row=1, column=0, sticky="ew",
                                                         padx=16, pady=(4, 12))
        self.sw = switch(self, command=self.toggled)
        self.sw.grid(row=0, column=1, rowspan=2, padx=16)
        if tweak.admin and not page.app.admin:
            self.sw.configure(state="disabled")

    def set_state(self, on: bool) -> None:
        self.sw.select() if on else self.sw.deselect()

    def toggled(self) -> None:
        on = bool(self.sw.get())
        self.sw.configure(state="disabled")

        def work():
            return tweaks.apply(self.tweak) if on else tweaks.revert(self.tweak)

        def done(res):
            ok, msg = res
            self.sw.configure(state="normal")
            if not ok:
                self.set_state(not on)
            self.page.app.tweak_states[self.tweak.id] = tweaks.is_applied(self.tweak)
            self.set_state(self.page.app.tweak_states[self.tweak.id])
            self.page.app.toast(msg, ok)

        self.page.app.run_bg(work, done)


class TweaksPage(Page):
    title = "Optimizaciones"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.header("Optimizaciones")
        button(bar, "Aplicar perfil", self.apply_profile, width=130).pack(side="right")
        self.profile = ctk.CTkOptionMenu(
            bar, values=list(tweaks.PROFILES.values()), width=230, fg_color=CARD,
            button_color=CARD_HOVER, button_hover_color=BORDER, font=font(12),
            command=self.profile_changed)
        self.profile.pack(side="right", padx=8)
        self.profile.set(tweaks.PROFILES[app.settings.get("profile", "estudio")])
        Muted(bar, "Perfil:", 12).pack(side="right")

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=28)
        msg = ("Cada interruptor guarda un respaldo y se puede revertir al apagarlo."
               if app.admin else
               "⚠ Sin permisos de administrador: las opciones marcadas 'Admin' están bloqueadas. "
               "Reinicia el programa como administrador para usarlas.")
        Muted(info, msg, 12, wrap=900, text_color=MUTED if app.admin else ORANGE).pack(fill="x")

        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_fg_color=CARD,
                                   segmented_button_selected_color=ACCENT,
                                   segmented_button_selected_hover_color=ACCENT,
                                   segmented_button_unselected_color=CARD,
                                   segmented_button_unselected_hover_color=CARD_HOVER,
                                   text_color=TEXT, anchor="w")
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(4, 16))
        self.rows: dict[str, TweakRow] = {}
        for cat in tweaks.CATEGORIES:
            tab = self.tabs.add(cat)
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            for t in tweaks.TWEAKS:
                if t.category == cat:
                    row = TweakRow(scroll, self, t)
                    row.pack(fill="x", pady=5, padx=(0, 8))
                    self.rows[t.id] = row

    def _profile_key(self) -> str:
        label = self.profile.get()
        return next(k for k, v in tweaks.PROFILES.items() if v == label)

    def profile_changed(self, _=None) -> None:
        self.app.settings["profile"] = self._profile_key()
        self.app.save_settings()

    def apply_profile(self) -> None:
        self.app.apply_profile(self._profile_key())

    def on_show(self) -> None:
        self.sync()

    def sync(self) -> None:
        self.profile.set(tweaks.PROFILES[self.app.settings.get("profile", "estudio")])
        for tid, row in self.rows.items():
            row.set_state(self.app.tweak_states.get(tid, False))


# ==========================================================================
# Arranque
# ==========================================================================

class StartupPage(Page):
    title = "Arranque"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.header("Arranque", "Programas que se abren al encender la laptop")
        button(bar, "Desactivar los de impacto alto", self.disable_heavy, width=230).pack(side="right")
        button(bar, "Apps de la Tienda", lambda: _open("ms-settings:startupapps"), primary=False,
               width=150).pack(side="right", padx=8)

        self.summary = Card(self)
        self.summary.pack(fill="x", padx=28, pady=(4, 8))
        self.summary_lbl = Muted(self.summary, "", 12, wrap=950)
        self.summary_lbl.pack(fill="x", padx=16, pady=12)

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def on_show(self) -> None:
        self.app.run_bg(startup.list_startup, self.populate)

    def populate(self, items) -> None:
        self.app.startup_items = items
        for w in self.list.winfo_children():
            w.destroy()
        specs = self.app.specs
        parts = []
        if specs and specs.boot_seconds:
            parts.append(f"Último arranque: {specs.boot_seconds:.0f} s.")
        if specs and specs.fast_startup is not None:
            parts.append("Inicio rápido: " + ("activado ✓." if specs.fast_startup else "desactivado ✗."))
        on = sum(1 for i in items if i.enabled)
        parts.append(f"{on} de {len(items)} programas se abren al encender. Lo ideal para una laptop de "
                     "uso escolar es dejar solo antivirus, audio, touchpad y controladores.")
        if specs and specs.only_hdd:
            parts.append("Tu disco es HDD: cada programa de inicio suma varios segundos.")
        self.summary_lbl.configure(text="  ".join(parts))

        if not items:
            Muted(self.list, "No se encontraron programas de inicio (o no estás en Windows).").pack(pady=20)
        for item in items:
            row = Card(self.list)
            row.pack(fill="x", pady=4, padx=(0, 8))
            row.grid_columnconfigure(1, weight=1)
            Badge(row, item.impact, IMPACT_COLORS.get(item.impact, ORANGE)).grid(
                row=0, column=0, rowspan=2, padx=(14, 10), pady=12)
            name = item.name + ("   · recomendado mantener" if item.keep else "")
            ctk.CTkLabel(row, text=name, font=font(13, "bold"), text_color=TEXT,
                         anchor="w").grid(row=0, column=1, sticky="ew", pady=(10, 0))
            Muted(row, item.advice, 11, wrap=620).grid(row=1, column=1, sticky="ew", pady=(0, 10))
            sw = switch(row)
            sw.grid(row=0, column=2, rowspan=2, padx=16)
            sw.select() if item.enabled else sw.deselect()
            if item.source in ("HKLM", "HKLM32", "Carpeta común") and not self.app.admin:
                sw.configure(state="disabled")
            sw.configure(command=lambda it=item, s=sw: self.toggle(it, s))

    def toggle(self, item, sw) -> None:
        on = bool(sw.get())
        if startup.set_enabled(item, on):
            self.app.toast(f"{item.name}: {'se abrirá' if on else 'ya no se abrirá'} al encender")
        else:
            sw.select() if not on else sw.deselect()
            self.app.toast(f"No se pudo cambiar {item.name}", False)

    def disable_heavy(self) -> None:
        items = self.app.startup_items or []
        changed = [i for i in items if i.enabled and i.impact == "Alto" and not i.keep
                   and startup.set_enabled(i, False)]
        self.app.toast(f"Se desactivaron {len(changed)} programas de inicio pesados")
        self.populate(items)


# ==========================================================================
# Procesos
# ==========================================================================

class ProcessesPage(Page):
    title = "Procesos"
    ROWS = 15

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.header("Procesos", "Qué está usando tu RAM y tu GPU ahora mismo")
        button(bar, "🧹  Liberar RAM", app.free_ram, width=150).pack(side="right")

        self.top = Card(self)
        self.top.pack(fill="x", padx=28, pady=(4, 8))
        self.summary = ctk.CTkLabel(self.top, text="", font=font(13), text_color=TEXT, anchor="w",
                                    justify="left", wraplength=950)
        self.summary.pack(fill="x", padx=16, pady=12)

        table = Card(self)
        table.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        table.grid_columnconfigure(0, weight=1)
        for c, (txt, w) in enumerate([("Programa", 0), ("Ventanas/procesos", 130), ("RAM", 110),
                                      ("GPU", 80), ("", 100)]):
            ctk.CTkLabel(table, text=txt, font=font(12, "bold"), text_color=MUTED, width=w,
                         anchor="w").grid(row=0, column=c, sticky="ew", padx=10, pady=(12, 6))
        self.cells = []
        for r in range(self.ROWS):
            labels = [ctk.CTkLabel(table, text="", font=font(12), text_color=TEXT, anchor="w")
                      for _ in range(4)]
            for c, lbl in enumerate(labels):
                lbl.grid(row=r + 1, column=c, sticky="ew", padx=10, pady=1)
            btn = button(table, "Cerrar", primary=False, height=24, width=90, font=font(11))
            btn.grid(row=r + 1, column=4, padx=10, pady=1)
            self.cells.append((labels, btn))
        self._counter = 0

    def on_show(self) -> None:
        self._counter = 0
        self.tick()

    def tick(self) -> None:
        self._counter -= 1
        if self._counter > 0:
            return
        self._counter = 3
        self.app.run_bg(lambda: memory.top_processes(self.ROWS, dict(self.app.monitor.gpu_by_pid)),
                        self.update_table)

    def update_table(self, procs) -> None:
        m = self.app.monitor
        gpu = f"{m.gpu:.0f} %" if m.gpu is not None else "N/D"
        browsers = sum(p.ram_mb for p in procs if p.name.lower() in
                       ("chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"))
        text = f"RAM en uso: {m.ram:.0f} % ({m.ram_used_gb:.1f} de {m.ram_total_gb:.1f} GB)   ·   GPU: {gpu}"
        if browsers > 800:
            text += (f"\n💡 Tu navegador está usando {browsers / 1024:.1f} GB. Cerrar pestañas o activar el "
                     "ahorro de memoria es lo que más RAM libera.")
        self.summary.configure(text=text)
        for i, (labels, btn) in enumerate(self.cells):
            if i < len(procs):
                p = procs[i]
                vals = [p.friendly, str(p.count), f"{p.ram_mb:,.0f} MB", f"{p.gpu:.0f} %" if p.gpu else "-"]
                for lbl, v in zip(labels, vals):
                    lbl.configure(text=v)
                labels[2].configure(text_color=RED if p.ram_mb > 1000 else ORANGE if p.ram_mb > 400 else TEXT)
                if p.protected:
                    btn.configure(state="disabled", text="Sistema", command=None)
                else:
                    btn.configure(state="normal", text="Cerrar",
                                  command=lambda n=p.name, f=p.friendly: self.kill(n, f))
            else:
                for lbl in labels:
                    lbl.configure(text="")
                btn.configure(state="disabled", text="")

    def kill(self, name: str, friendly: str) -> None:
        n = memory.kill_by_name(name)
        self.app.toast(f"Se cerró {friendly} ({n} procesos)" if n else f"No se pudo cerrar {friendly}",
                       bool(n))
        self._counter = 1


# ==========================================================================
# Recomendaciones por tarea
# ==========================================================================

def _task_tweaks(key: str) -> list[tweaks.Tweak]:
    if key == "arranque":
        return [t for t in tweaks.TWEAKS if t.category == "Arranque"]
    return tweaks.tweaks_for_profile(key)


class TasksPage(Page):
    title = "Por tarea"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.header("Recomendaciones por tarea", "Elige lo que vas a hacer")
        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_fg_color=CARD,
                                   segmented_button_selected_color=ACCENT,
                                   segmented_button_selected_hover_color=ACCENT,
                                   segmented_button_unselected_color=CARD,
                                   segmented_button_unselected_hover_color=CARD_HOVER,
                                   text_color=TEXT, anchor="w")
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.apply_labels = {}
        for key, task in TASKS.items():
            tab = self.tabs.add(f"{task['icon']} {task['title']}")
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            Muted(scroll, task["intro"], 13, wrap=900, text_color=TEXT).pack(fill="x", pady=(4, 10))

            rec = Card(scroll, border_width=1, border_color=ACCENT)
            rec.pack(fill="x", pady=(0, 12), padx=(0, 8))
            tw = _task_tweaks(key)
            SectionTitle(rec, f"Optimizaciones recomendadas ({len(tw)})", 14).pack(
                fill="x", padx=16, pady=(12, 2))
            lbl = Muted(rec, "", 12, wrap=880)
            lbl.pack(fill="x", padx=16)
            self.apply_labels[key] = (lbl, tw)
            button(rec, "Aplicar optimizaciones para esta tarea",
                   lambda k=key: self.apply(k), width=300).pack(anchor="w", padx=16, pady=12)

            SectionTitle(scroll, "Consejos", 15).pack(fill="x", pady=(0, 6))
            for title, detail in task["tips"]:
                c = Card(scroll)
                c.pack(fill="x", pady=4, padx=(0, 8))
                ctk.CTkLabel(c, text="✓  " + title, font=font(13, "bold"), text_color=TEXT,
                             anchor="w").pack(fill="x", padx=16, pady=(10, 0))
                Muted(c, detail, 12, wrap=860).pack(fill="x", padx=36, pady=(2, 10))

    def on_show(self) -> None:
        for key, (lbl, tw) in self.apply_labels.items():
            names = [("✓ " if self.app.tweak_states.get(t.id) else "• ") + t.name for t in tw]
            lbl.configure(text="   ".join(names))

    def apply(self, key: str) -> None:
        self.app.apply_tweaks(_task_tweaks(key), TASKS[key]["title"], on_done=self.on_show)


# ==========================================================================
# Mi laptop
# ==========================================================================

class LaptopPage(Page):
    title = "Mi laptop"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.header("Mi laptop", "Especificaciones detectadas automáticamente")
        button(bar, "Volver a detectar", app.detect, primary=False, width=150).pack(side="right")
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        Muted(self.scroll, "Detectando hardware…", 13).pack(pady=20)

    def on_show(self) -> None:
        self.render()

    def render(self) -> None:
        specs = self.app.specs
        if not specs:
            return
        for w in self.scroll.winfo_children():
            w.destroy()

        top = Card(self.scroll)
        top.pack(fill="x", pady=(0, 10), padx=(0, 8))
        ctk.CTkLabel(top, text=f"{specs.manufacturer} {specs.model}", font=font(20, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x", padx=18, pady=(14, 0))
        line = ctk.CTkFrame(top, fg_color="transparent")
        line.pack(fill="x", padx=18, pady=(6, 14))
        Badge(line, LAPTOP_TYPES[self.app.laptop_type]).pack(side="left")
        Muted(line, "  ← tipo detectado. Mira sus consejos en 'Tipos de laptop'.", 12).pack(side="left")

        grid = Card(self.scroll)
        grid.pack(fill="x", pady=(0, 10), padx=(0, 8))
        grid.grid_columnconfigure((1, 3), weight=1)
        ram = f"{specs.ram_gb:.0f} GB"
        if specs.ram_speed:
            ram += f" · {specs.ram_speed} MHz"
        if specs.ram_modules:
            ram += f" · {specs.ram_modules} módulo(s)"
            if specs.ram_slots:
                ram += f" de {specs.ram_slots} ranuras"
        gpus = "\n".join(f"{g.name} ({'dedicada' if g.dedicated else 'integrada'}"
                         + (f", {g.vram_gb:.0f} GB" if g.dedicated and g.vram_gb else "") + ")"
                         for g in specs.gpus) or "Desconocida"
        rows = [
            ("Procesador", specs.cpu), ("Núcleos / hilos", f"{specs.cpu_cores} / {specs.cpu_threads}"),
            ("Memoria RAM", ram), ("Tarjeta gráfica", gpus),
            ("Almacenamiento", specs.disk_summary), ("Sistema", f"{specs.os} {specs.os_build}".strip()),
            ("Último arranque", f"{specs.boot_seconds:.0f} s" if specs.boot_seconds else "N/D"),
            ("Inicio rápido", {True: "Activado", False: "Desactivado", None: "N/D"}[specs.fast_startup]),
        ]
        for i, (k, v) in enumerate(rows):
            r, c = divmod(i, 2)
            Muted(grid, k, 12).grid(row=r, column=c * 2, sticky="nw", padx=(18, 10), pady=8)
            ctk.CTkLabel(grid, text=v, font=font(13, "bold"), text_color=TEXT, anchor="w",
                         justify="left", wraplength=330).grid(row=r, column=c * 2 + 1, sticky="w", pady=8)

        SectionTitle(self.scroll, "Diagnóstico", 15).pack(fill="x", pady=(6, 6))
        for level, msg in diagnose(specs) or [("ok", "Sin problemas de hardware detectados.")]:
            c = Card(self.scroll)
            c.pack(fill="x", pady=3, padx=(0, 8))
            ctk.CTkLabel(c, text="●", text_color=LEVEL_COLORS[level], font=font(16),
                         width=20).pack(side="left", padx=(14, 6), pady=10, anchor="n")
            Muted(c, msg, 12, wrap=860, text_color=TEXT).pack(side="left", fill="x", pady=10, padx=(0, 14))

        SectionTitle(self.scroll, "Recomendaciones para tu hardware", 15).pack(fill="x", pady=(12, 6))
        for tip in personalized(specs):
            c = Card(self.scroll)
            c.pack(fill="x", pady=3, padx=(0, 8))
            Muted(c, "💡  " + tip, 12, wrap=900, text_color=TEXT).pack(fill="x", padx=14, pady=10)


# ==========================================================================
# Tipos de laptop
# ==========================================================================

class LaptopTypesPage(Page):
    title = "Tipos de laptop"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.header("Recomendaciones por tipo de laptop")
        self.tabs = None

    def on_show(self) -> None:
        if self.tabs is not None:
            return
        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_fg_color=CARD,
                                   segmented_button_selected_color=ACCENT,
                                   segmented_button_selected_hover_color=ACCENT,
                                   segmented_button_unselected_color=CARD,
                                   segmented_button_unselected_hover_color=CARD_HOVER,
                                   text_color=TEXT, anchor="w")
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        mine = self.app.laptop_type
        for key, info in LAPTOPS.items():
            name = f"{info['icon']} {info['title']}" + ("  ★" if key == mine else "")
            tab = self.tabs.add(name)
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            if key == mine:
                c = Card(scroll, border_width=1, border_color=ACCENT)
                c.pack(fill="x", pady=(4, 10), padx=(0, 8))
                Muted(c, "★ Este es el tipo que detectamos para tu laptop.", 13,
                      text_color=ACCENT).pack(fill="x", padx=16, pady=10)
            Muted(scroll, "Típicamente: " + info["who"], 13, wrap=900).pack(fill="x", pady=(4, 10))
            for tip in info["tips"]:
                c = Card(scroll)
                c.pack(fill="x", pady=4, padx=(0, 8))
                Muted(c, "✓  " + tip, 13, wrap=900, text_color=TEXT).pack(fill="x", padx=16, pady=11)
            if key == mine:
                self.tabs.set(name)


# ==========================================================================
# Ajustes
# ==========================================================================

class SettingsPage(Page):
    title = "Ajustes"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.header("Ajustes")
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        s = app.settings

        c = Card(body)
        c.pack(fill="x", pady=6, padx=(0, 8))
        c.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(c, text="Liberar RAM automáticamente", font=font(14, "bold"), text_color=TEXT,
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        self.thr_lbl = Muted(c, "", 12)
        self.thr_lbl.grid(row=1, column=0, sticky="ew", padx=16)
        self.auto = switch(c, command=self.save)
        self.auto.grid(row=0, column=1, rowspan=2, padx=16)
        self.auto.select() if s.get("auto_free_ram") else self.auto.deselect()
        self.slider = ctk.CTkSlider(c, from_=70, to=95, number_of_steps=25, command=self.save,
                                    progress_color=ACCENT, button_color=ACCENT,
                                    button_hover_color=ACCENT)
        self.slider.set(s.get("ram_threshold", 85))
        self.slider.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 14))

        c2 = Card(body)
        c2.pack(fill="x", pady=6, padx=(0, 8))
        c2.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(c2, text="Crear punto de restauración antes de aplicar perfiles",
                     font=font(14, "bold"), text_color=TEXT, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        Muted(c2, "Recomendado. Permite deshacer cualquier cambio desde 'Restaurar sistema' de Windows.",
              12).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.rp = switch(c2, command=self.save)
        self.rp.grid(row=0, column=1, rowspan=2, padx=16)
        self.rp.select() if s.get("restore_point", True) else self.rp.deselect()

        c3 = Card(body)
        c3.pack(fill="x", pady=6, padx=(0, 8))
        ctk.CTkLabel(c3, text="Mantenimiento", font=font(14, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x", padx=16, pady=(12, 8))
        row = ctk.CTkFrame(c3, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        button(row, "Crear punto de restauración", self.restore_point, primary=False,
               width=220).pack(side="left")
        button(row, "Revertir todas las optimizaciones", self.revert_all, primary=False,
               width=250).pack(side="left", padx=8)
        button(row, "Abrir carpeta de respaldos", lambda: _open(str(data_dir())), primary=False,
               width=200).pack(side="left")

        c4 = Card(body)
        c4.pack(fill="x", pady=6, padx=(0, 8))
        status = "Sí ✓" if app.admin else "No — algunas opciones están bloqueadas"
        Muted(c4, f"Ejecutando como administrador: {status}\nRespaldos y ajustes en: {data_dir()}",
              12, text_color=TEXT).pack(fill="x", padx=16, pady=12)
        if IS_WINDOWS and not app.admin:
            button(c4, "Reiniciar como administrador", app.restart_admin, width=240).pack(
                anchor="w", padx=16, pady=(0, 14))
        self.save()

    def save(self, _=None) -> None:
        s = self.app.settings
        s["auto_free_ram"] = bool(self.auto.get())
        s["ram_threshold"] = int(self.slider.get())
        s["restore_point"] = bool(self.rp.get())
        self.thr_lbl.configure(text=f"Cuando la RAM supere el {s['ram_threshold']} % (como máximo una vez "
                                    "cada 2 minutos).")
        self.app.save_settings()

    def restore_point(self) -> None:
        self.app.toast("Creando punto de restauración… (puede tardar un minuto)")
        self.app.run_bg(tweaks.create_restore_point, lambda r: self.app.toast(r[1], r[0]))

    def revert_all(self) -> None:
        def work():
            n = 0
            for t in tweaks.TWEAKS:
                if t.id in tweaks.load_json(tweaks.BACKUP_FILE, {}):
                    ok, _ = tweaks.revert(t)
                    n += ok
            return n

        def done(n):
            self.app.toast(f"Se revirtieron {n} optimizaciones")
            self.app.refresh_tweaks()

        self.app.run_bg(work, done)


def _open(target: str) -> None:
    if IS_WINDOWS:
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", target])


PAGES = [
    ("🏠", DashboardPage), ("🚀", TweaksPage), ("⚡", StartupPage), ("📈", ProcessesPage),
    ("🎯", TasksPage), ("💻", LaptopPage), ("🧭", LaptopTypesPage), ("⚙", SettingsPage),
]
