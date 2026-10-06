# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: i18n/sync.py

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable

from .engine import get_i18n_instance, resolve_languages_directory
from .translator import get_translator, BaseTranslator, _normalize_lang_code, _get_primary_lang_code
from .extractor import _sort_dictionary

logger = logging.getLogger("i18n.sync")

KNOWN_LANG_NAMES: Dict[str, str] = {
    "en": "English",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "es": "Español",
    "es-VE": "Español (Venezuela)",
    "es-MX": "Español (México)",
    "es-ES": "Español (España)",
    "es-AR": "Español (Argentina)",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "pt-BR": "Português (Brasil)",
    "pt-PT": "Português (Portugal)",
    "ru": "Русский",
    "zh": "中文",
    "zh-CN": "中文 (简体)",
    "zh-TW": "中文 (繁體)",
    "ja": "日本語"
}

def resolve_language_name(code: str, custom_name: Optional[str] = None) -> str:
    """
    Resuelve el nombre legible de un idioma a partir de su código, soportando regionalizaciones.
    Ejemplos: 'pt-BR' -> 'Português (Brasil)', 'es-VE' -> 'Español (Venezuela)'.
    """
    code = _normalize_lang_code(code)
    if code in KNOWN_LANG_NAMES:
        return KNOWN_LANG_NAMES[code]

    parts = code.split("-")
    if len(parts) > 1:
        primary = parts[0]
        region = parts[1]
        if primary in KNOWN_LANG_NAMES:
            return f"{KNOWN_LANG_NAMES[primary]} ({region})"

    if custom_name and custom_name.strip():
        return custom_name.strip()

    return code.upper()

def _merge_nested_dicts(base: Dict[str, Any], target: Dict[str, Any], nested_level: int = 0, origen: str = "?", key_dest: str = "") -> Dict[str, Any]:
    """
    Combina recursivamente la estructura anidada del diccionario base en el diccionario destino.
    Preserva traducciones previamente existentes en target y agrega claves nuevas provenientes de base.
    Preserva metadatos de configuración (claves que inician con `_`), a excepción de `_language_name`.
    """
    result: Dict[str, Any] = {}
    if nested_level == 0:
        result["_language_name"] = origen
    for key, base_val in base.items():
        if key == "_language_name":
            continue

        if key in target:
            target_val = target[key]
            if isinstance(base_val, dict) and isinstance(target_val, dict):
                result[key] = _merge_nested_dicts(base_val, target_val,nested_level=nested_level+1,key_dest=key,origen=f"{origen}-_merge_nested_dicts")
            elif target_val:
                result[key] = target_val
            else:
                result[key] = base_val
        else:
            result[key] = base_val

    for key, target_val in target.items():
        if key != "_language_name" and key not in result:
            result[key] = target_val
            
    return result

def _get_value_at_path(data: Dict[str, Any], path: List[str]) -> Optional[Any]:
    """Obtiene un valor en una ruta de subclaves dentro de un diccionario."""
    curr = data
    for step in path:
        if isinstance(curr, dict) and step in curr:
            curr = curr[step]
        else:
            return None
    return curr

def translate_dictionary(
    base_data: Dict[str, Any],
    target_code: str,
    source_code: str = "es",
    target_name: Optional[str] = None,
    engine: str = "auto",
    overwrite: bool = False,
    existing_target: Optional[Dict[str, Any]] = None,
    default_dict: Optional[Dict[str, Any]] = None,
    translator_instance: Optional[BaseTranslator] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Recorre recursivamente un diccionario base traducible y genera una versión traducida al idioma destino.
    
    Preserva:
    - La estructura y jerarquía exacta del default_dict / base_data.
    - Claves metadato que inician con `_` (actualizando `_language_name`).
    - Traducciones previamente existentes en `existing_target` a menos que sean idénticas al default_dict o `overwrite=True`.
    - Variables, etiquetas HTML y saltos de línea (mediante el PlaceholderMasker del motor).
    - Soporte para códigos regionalizados (ej. pt-BR, es-VE).
    """
    translator = translator_instance or get_translator(engine)
    existing_target = existing_target or {}

    # 1. Asegurar respeto estricto de la estructura de default_dict
    if default_dict:
        effective_base = _merge_nested_dicts(default_dict, base_data,origen = "translate_dictionary-1")
    else:
        effective_base = base_data

    source_code = _normalize_lang_code(source_code)
    target_code = _normalize_lang_code(target_code)
    resolved_name = resolve_language_name(target_code, target_name)

    # 2. Recolección de textos traducibles para procesamiento en lote (batching)
    pending_items: List[Tuple[List[str], str]] = []

    def _collect_texts(current_base: Dict[str, Any], current_existing: Dict[str, Any], current_path: List[str]):
        for key, base_val in current_base.items():
            if key.startswith("_"):
                continue

            existing_val = current_existing.get(key) if isinstance(current_existing, dict) else None

            if isinstance(base_val, dict):
                sub_existing = existing_val if isinstance(existing_val, dict) else {}
                _collect_texts(base_val, sub_existing, current_path + [key])
            elif isinstance(base_val, str):
                # REGLA 2: Solo traducir si la clave no tiene traducción o si el valor existente
                # es EXACTAMENTE igual al valor del idioma base / default_dict (no ha sido traducido aún).
                default_val = _get_value_at_path(default_dict, current_path + [key]) if default_dict else None
                
                is_untranslated = overwrite
                if not is_untranslated:
                    is_untranslated = (
                        existing_val is None or
                        existing_val == base_val or
                        (default_val and existing_val == default_val)
                    )
                if is_untranslated:
                    pending_items.append((current_path + [key], base_val))

    _collect_texts(effective_base, existing_target, [])

    # 3. Copiar estructura inicial de existing_target combinada con base
    result_data = _merge_nested_dicts(effective_base, existing_target, origen="translate_dictionary-2")
    result_data["_language_name"] = resolved_name

    # 4. Realizar traducción en lote pasando el progress_callback
    if pending_items:
        paths = [item[0] for item in pending_items]
        raw_texts = [item[1] for item in pending_items]

        try:
            translated_texts = translator.translate_batch(
                raw_texts,
                source_code,
                target_code,
                progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Error al traducir lote de textos ({source_code} -> {target_code}): {e}")
            translated_texts = raw_texts

        # 5. Asignar los resultados traducidos en el diccionario final
        for (path, original_str), trans_str in zip(pending_items, translated_texts):
            curr = result_data
            for step in path[:-1]:
                curr = curr.setdefault(step, {})
            curr[path[-1]] = trans_str

    return _sort_dictionary(result_data)

def prepare_new_language(
    target_code: str,
    target_name: str,
    default_dict: Dict[str, Any],
    base_code: Optional[str] = None,
    target_dir: Optional[str] = None,
    auto_translate: bool = True,
    engine: str = "auto",
    overwrite: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Prepara o sincroniza un archivo JSON de idioma basado en el diccionario base.
    Si `auto_translate` es True, traduce automáticamente las claves nuevas o no traducidas.
    Preserva las traducciones y estructura jerárquica anidada previamente existente.
    """
    if not base_code:
        base_code = get_i18n_instance().idioma_def_cod
    else:
        base_code = _normalize_lang_code(base_code)

    target_code = _normalize_lang_code(target_code)
    target_name = resolve_language_name(target_code, target_name)

    output_dir = resolve_languages_directory(target_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    base_file = output_dir / f"{base_code}.json"
    target_file = output_dir / f"{target_code}.json"

    base_data: Dict[str, Any] = {}
    if base_file.exists():
        try:
            with open(base_file, "r", encoding="utf-8") as f:
                base_data_temp = json.load(f)
            base_data = _merge_nested_dicts(default_dict, base_data_temp, origen="prepare_new_language-1")
        except Exception as e:
            logger.error(f"Error al leer archivo base {base_file}: {e}")
    else:
        base_data = default_dict

    target_data: Dict[str, Any] = {}
    if target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                target_data = json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo leer archivo destino existente {target_file}: {e}")

    resolved_name = resolve_language_name(target_code, target_name)

    if auto_translate:
        final_output = translate_dictionary(
            base_data=base_data,
            target_code=target_code,
            source_code=base_code,
            target_name=resolved_name,
            engine=engine,
            overwrite=overwrite,
            existing_target=target_data,
            default_dict=default_dict,
            progress_callback=progress_callback
        )
    else:
        final_output = _merge_nested_dicts(base_data, target_data, origen="prepare_new_language-2")
    
    final_output = _sort_dictionary(final_output)

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    return {
        "status": "success",
        "target_code": target_code,
        "target_name": resolved_name,
        "file_path": str(target_file)
    }
