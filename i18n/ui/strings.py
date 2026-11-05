# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/ui/strings.py

"""Cadenas de texto canónicas y registro de soporte t18n para la interfaz gráfica de i18n."""

from typing import Dict, Any
from i18n.engine import get_i18n_instance

DEFAULT_UI_TRANSLATIONS: Dict[str, Any] = {
    "dialog_title": "Generador de Diccionarios",
    "lbl_base_source": "Origen del diccionario base:",
    "source_memory": "Diccionario en memoria (código)",
    "source_file": "Archivo JSON base",
    "lbl_base_file": "Archivo JSON base de referencia:",
    "btn_browse": "Examinar...",
    "lbl_target_dir": "Directorio destino de idiomas:",
    "lbl_target_lang": "Nuevo idioma a generar:",
    "lbl_engine": "Motor de traducción:",
    "engine_opt_auto": "Auto",
    "engine_opt_online": "Con Internet (Google)",
    "engine_opt_offline": "Sin Internet (Argos)",
    "engine_opt_none": "Ninguno (Solo copiar)",
    "chk_online_translation": "Activar traducción en línea",
    "chk_overwrite": "Sobrescribir traducciones existentes",
    "btn_cancel": "Cancelar",
    "btn_accept": "Aceptar",
    "msg_starting_translation": "Iniciando traducción...",
    "msg_status_checking": "Verificando entorno y conexión...",
    "msg_status_updating_packages": "Actualizando índice de paquetes de traducción...",
    "msg_status_downloading_package": "Descargando paquete de idioma ({pair})...",
    "msg_status_installing_package": "Instalando paquete de idioma...",
    "msg_status_loading_model": "Cargando modelo de traducción...",
    "msg_status_analyzing_keys": "Analizando textos y claves a traducir...",
    "msg_status_saving_file": "Guardando archivo de idioma...",
    "msg_status_completed": "Completado",
    "msg_translating_progress": "Traduciendo {engine} ({current}/{total}): {preview}",
    "title_success": "Éxito",
    "msg_lang_created_success": "Archivo de idioma creado correctamente en:\n{file_path}\n\n¡Ya puedes seleccionarlo o integrarlo en tu aplicación!",
    "title_error": "Error",
    "err_empty_target_dir": "Debe especificar un directorio destino válido.",
    "err_base_file_not_found": "El archivo JSON base no existe o no es accesible:\n{file_path}",
    "err_invalid_base_json": "El archivo base no contiene un JSON válido:\n{error}",
    "err_no_base_memory": "No se suministró un diccionario base en memoria para la aplicación.",
    "msg_lang_created_fail": "No se pudo generar el archivo de idioma:\n{error}"
}

def ensure_ui_translations() -> None:
    """Registra las traducciones por defecto de la interfaz gráfica en la instancia global de i18n."""
    get_i18n_instance().register_section_defaults("i18n_ui", DEFAULT_UI_TRANSLATIONS)


def get_ui_default_dict(language_name: str = "Español") -> Dict[str, Any]:
    """Retorna el diccionario base canónico de la interfaz gráfica de pkg-i18n."""
    return {
        "_language_name": language_name,
        "i18n_ui": dict(DEFAULT_UI_TRANSLATIONS),
    }

