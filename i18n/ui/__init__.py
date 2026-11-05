# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/ui/__init__.py

"""Módulo de Interfaz Gráfica CustomTkinter para pkg-i18n (Carga bajo demanda)."""

from i18n.ui.dialog import LanguageDialog, launch_new_language_dialog
from i18n.ui.strings import get_ui_default_dict

__all__ = ["LanguageDialog", "launch_new_language_dialog", "get_ui_default_dict"]

