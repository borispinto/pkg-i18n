# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/__init__.py

"""
Sistema de Internacionalización (i18n) para Python.
Ofrece motor de carga en cascada (archivos empaquetados vs externos de usuario),
búsqueda con notación de puntos (modulo1.sec1.clave y sección _default), función t18n,
observadores en tiempo real, herramienta de preparación/sincronización y traducción automática de JSONs
y extractor de idioma base para desarrollo.
"""
__title__ = "pkg-i18n"
__version__ = "1.0.0"
__author__ = "Boris Pinto"
__email__ = "borispinto@gmail.com"
__copyright__ = "Copyright (c) 2026 ASISNET Computación, CA"
__license__ = "MIT"


from .engine import (
    I18nManager,
    get_i18n_instance,
    t18n,
    resolve_languages_directory,
    export_active_dictionary,
    register_defaults,
    register_section_defaults,
    set_context_language,
    get_context_language,
    reset_context_language,
    use_language,
    clear_cache
)

_LAZY_EXPORTS = {
    "prepare_new_language": ("i18n.sync", "prepare_new_language"),
    "translate_dictionary": ("i18n.sync", "translate_dictionary"),
    "extract_base_language": ("i18n.extractor", "extract_base_language"),
    "PlaceholderMasker": ("i18n.translator", "PlaceholderMasker"),
    "BaseTranslator": ("i18n.translator", "BaseTranslator"),
    "NoneTranslator": ("i18n.translator", "NoneTranslator"),
    "MockTranslator": ("i18n.translator", "MockTranslator"),
    "GoogleTranslatorEngine": ("i18n.translator", "GoogleTranslatorEngine"),
    "ArgosTranslatorEngine": ("i18n.translator", "ArgosTranslatorEngine"),
    "ENGINE_REGISTRY": ("i18n.translator", "ENGINE_REGISTRY"),
    "get_engine_display_name": ("i18n.translator", "get_engine_display_name"),
    "get_translator": ("i18n.translator", "get_translator"),
    "proceso_unico": ("i18n.translator", "proceso_unico"),
    "compacta_cadenas": ("i18n.translator", "compacta_cadenas"),
    "descompacta_cadenas": ("i18n.translator", "descompacta_cadenas"),
    "LanguageDialog": ("i18n.ui", "LanguageDialog"),
    "launch_new_language_dialog": ("i18n.ui", "launch_new_language_dialog")
}

def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_path, attr_name = _LAZY_EXPORTS[name]
        import importlib
        module = importlib.import_module(module_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))

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
    "t18n",
    "export_active_dictionary",
    "register_defaults",
    "register_section_defaults",
    "set_context_language",
    "get_context_language",
    "reset_context_language",
    "use_language",
    "clear_cache",
    "prepare_new_language",
    "translate_dictionary",
    "extract_base_language",
    "PlaceholderMasker",
    "BaseTranslator",
    "NoneTranslator",
    "MockTranslator",
    "GoogleTranslatorEngine",
    "ArgosTranslatorEngine",
    "ENGINE_REGISTRY",
    "get_engine_display_name",
    "get_translator",
    "proceso_unico",
    "compacta_cadenas",
    "descompacta_cadenas",
    "LanguageDialog",
    "launch_new_language_dialog"
]
