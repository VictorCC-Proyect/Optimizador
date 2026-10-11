"""Colores y widgets reutilizables (anillos de uso, gráfica, tarjetas)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

# Paleta inspirada en Hone: fondo azul muy oscuro y acento naranja
BG = "#0b1220"
SIDEBAR = "#0f1828"
CARD = "#152033"
CARD_HOVER = "#1b2940"
BORDER = "#22314a"
TEXT = "#e8edf5"
MUTED = "#8b98ad"
ACCENT = "#f59e0b"
ACCENT_HOVER = "#d97f06"
GREEN = "#22c55e"
BLUE = "#3b82f6"
ORANGE = "#f59e0b"
RED = "#ef4444"
TRACK = "#2a3850"

FONT = "Segoe UI"


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT, size=size, weight=weight)


def level_color(value: float) -> str:
    if value >= 85:
        return RED
    if value >= 65:
        return ORANGE
    return GREEN


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", CARD)
        kw.setdefault("corner_radius", 12)
        super().__init__(master, **kw)


class Ring(tk.Canvas):
    """Anillo circular de porcentaje (como los de CPU/GPU/RAM de Hone)."""

    def __init__(self, master, size: int = 120, width: int = 12, color: str | None = None,
                 bg: str = CARD, label_size: int = 20):
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0)
        self.size, self.width, self.fixed_color = size, width, color
        pad = width / 2 + 2
        box = (pad, pad, size - pad, size - pad)
        self.create_oval(*box, outline=TRACK, width=width)
        self._arc = self.create_arc(*box, start=90, extent=0, style="arc",
                                    outline=color or GREEN, width=width)
        self._txt = self.create_text(size / 2, size / 2, text="--", fill=TEXT,
                                     font=(FONT, label_size, "bold"))
        self._value = -1.0

    def set(self, value: float | None, text: str | None = None) -> None:
        if value is None:
            self.itemconfigure(self._arc, extent=0)
            self.itemconfigure(self._txt, text=text or "N/D")
            return
        value = max(0.0, min(100.0, value))
        if abs(value - self._value) < 0.1 and text is None:
            return
        self._value = value
        color = self.fixed_color or level_color(value)
        self.itemconfigure(self._arc, extent=-3.6 * value if value < 100 else -359.9, outline=color)
        self.itemconfigure(self._txt, text=text if text is not None else f"{value:.0f}%")


class LineChart(tk.Canvas):
    """Gráfica de línea simple para el historial de uso."""

    def __init__(self, master, width: int = 360, height: int = 120, color: str = GREEN, bg: str = CARD):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0)
        self.color = color
        self.bind("<Configure>", lambda e: self._redraw())
        self._data: list[float] = []

    def set(self, data) -> None:
        self._data = list(data)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or len(self._data) < 2:
            return
        for frac in (0.25, 0.5, 0.75):
            y = h - frac * (h - 8) - 4
            self.create_line(0, y, w, y, fill=BORDER, dash=(2, 4))
        step = w / (len(self._data) - 1)
        pts = []
        for i, v in enumerate(self._data):
            pts += [i * step, h - (max(0, min(100, v)) / 100) * (h - 8) - 4]
        self.create_polygon(0, h, *pts, w, h, fill="#14322a" if self.color == GREEN else "#1a2a4a",
                            outline="")
        self.create_line(*pts, fill=self.color, width=2, smooth=True)
        x, y = pts[-2], pts[-1]
        self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=self.color, outline="")


class Badge(ctk.CTkLabel):
    def __init__(self, master, text: str, color: str = ACCENT, text_color_: str = "#0b1220", **kw):
        super().__init__(master, text=f" {text} ", fg_color=color, text_color=text_color_,
                         corner_radius=6, font=font(11, "bold"), height=20, **kw)


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, size: int = 16, **kw):
        super().__init__(master, text=text, font=font(size, "bold"), text_color=TEXT,
                         anchor="w", **kw)


class Muted(ctk.CTkLabel):
    def __init__(self, master, text: str, size: int = 12, wrap: int = 0, **kw):
        kw.setdefault("anchor", "w")
        kw.setdefault("justify", "left")
        kw.setdefault("text_color", MUTED)
        super().__init__(master, text=text, font=font(size),
                         wraplength=wrap, **kw)


def button(master, text: str, command=None, primary: bool = True, **kw) -> ctk.CTkButton:
    kw.setdefault("height", 34)
    kw.setdefault("corner_radius", 8)
    kw.setdefault("font", font(13, "bold"))
    if primary:
        return ctk.CTkButton(master, text=text, command=command, fg_color=ACCENT,
                             hover_color=ACCENT_HOVER, text_color="#111827", **kw)
    return ctk.CTkButton(master, text=text, command=command, fg_color=CARD_HOVER,
                         hover_color=BORDER, text_color=TEXT, **kw)


def switch(master, command=None, **kw) -> ctk.CTkSwitch:
    return ctk.CTkSwitch(master, text="", command=command, progress_color=BLUE,
                         button_color="#ffffff", button_hover_color="#dbeafe",
                         fg_color=TRACK, width=46, **kw)
