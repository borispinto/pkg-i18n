# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/cli.py

"""
Módulo de interfaz de línea de comandos (CLI) para pkg-i18n.
Permite lanzar la interfaz gráfica (--ui) y ejecutar herramientas de preparación de diccionarios.
"""

import argparse
import sys
from typing import Optional, Sequence

from i18n import __version__


def create_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de línea de comandos para i18n."""
    parser = argparse.ArgumentParser(
        prog="i18n",
        description="Herramienta CLI del motor de internacionalización pkg-i18n (Asisnet).",
        epilog="Ejemplo: i18n --ui --target-dir Recursos/idiomas --base Recursos/idiomas/es.json",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"pkg-i18n {__version__}",
        help="Muestra la versión instalada de pkg-i18n.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Lanza la interfaz gráfica interactiva para la creación y traducción de idiomas.",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Ruta inicial del directorio destino para los archivos de idioma.",
    )
    parser.add_argument(
        "--base",
        type=str,
        default=None,
        help="Ruta inicial al archivo base (.json) para la traducción.",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Tema de color para CustomTkinter (ej: 'blue', 'dark-blue', 'green').",
    )
    parser.add_argument(
        "--appearance",
        type=str,
        choices=["dark", "light", "system"],
        default=None,
        help="Modo de apariencia para la interfaz ('dark', 'light', 'system').",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada principal de la línea de comandos."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.ui:
        try:
            from i18n.ui import launch_new_language_dialog, get_ui_default_dict

            launch_new_language_dialog(
                parent=None,
                target_dir=args.target_dir,
                base_file=args.base,
                default_dict=get_ui_default_dict(),
                theme=args.theme,
                appearance_mode=args.appearance,
            )
            return 0
        except Exception as e:
            print(f"[ERROR] Error al iniciar la interfaz gráfica de i18n: {e}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
