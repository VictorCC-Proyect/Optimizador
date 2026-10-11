"""Punto de entrada de Optimizador.

Uso:  python main.py            (pide permisos de administrador)
      python main.py --no-admin (abre en modo limitado)
"""

import sys

from optimizador.winutils import IS_WINDOWS, is_admin, relaunch_as_admin


def run() -> None:
    if IS_WINDOWS and not is_admin() and "--no-admin" not in sys.argv:
        # Muchas optimizaciones necesitan administrador: se vuelve a abrir con UAC.
        # Si el usuario cancela el aviso, se continúa en modo limitado.
        if relaunch_as_admin():
            return
    from optimizador.ui.app import main

    main()


if __name__ == "__main__":
    run()
