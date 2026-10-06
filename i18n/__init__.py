# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: i18n/__init__.py

"""
Sistema de Internacionalización (i18n) para Python.
Ofrece motor de carga en cascada (archivos empaquetados vs externos de usuario),
búsqueda con notación de puntos (modulo1.sec1.clave y sección _default), alias t18n,
observadores en tiempo real, herramienta de preparación/sincronización y traducción automática de JSONs
y extractor de idioma base para desarrollo.
"""
__title__ = "pkg-i18n"
__version__ = "1.0.0"
__author__ = "Boris Pinto"
__email__ = "borispinto@asisnet.net"
__copyright__ = "Copyright (c) 2026 Asisnet Computacion, CA"
__license__ = "Proprietary"


from .engine import I18nManager, get_i18n_instance, translate, t18n, resolve_languages_directory, export_active_dictionary
from .sync import prepare_new_language, translate_dictionary
from .extractor import extract_base_language
from .translator import (
    PlaceholderMasker,
    BaseTranslator,
    MockTranslator,
    GoogleTranslatorEngine,
    ArgosTranslatorEngine,
    get_translator
)

__all__ = [
    "__title__",
    "__version__",
    "__author__",
    "__email__",
    "__copyright__",
    "__license__",
    "I18nManager",
    "get_i18n_instance",
    "resolve_languages_directory",
    "translate",
    "t18n",
    "export_active_dictionary",
    "prepare_new_language",
    "translate_dictionary",
    "extract_base_language",
    "PlaceholderMasker",
    "BaseTranslator",
    "MockTranslator",
    "GoogleTranslatorEngine",
    "ArgosTranslatorEngine",
    "get_translator"
]
