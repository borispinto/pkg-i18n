# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/sync.py

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable, Union

from .engine import get_i18n_instance, resolve_languages_directory, t18n
from .translator import get_translator, BaseTranslator, _normalize_lang_code
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

def _merge_nested_dicts(base: Dict[str, Any], target: Dict[str, Any], nested_level: int = 0) -> Dict[str, Any]:
    """
    Combina recursivamente la estructura anidada del diccionario base en el diccionario destino.
    Preserva traducciones previamente existentes en target y agrega claves nuevas provenientes de base.
    Preserva metadatos de configuración (claves que inician con `_`), a excepción de `_language_name`.
    """
    result: Dict[str, Any] = {}
    for key, base_val in base.items():
        if key == "_language_name":
            continue

        if key in target:
            target_val = target[key]
            if isinstance(base_val, dict) and isinstance(target_val, dict):
                result[key] = _merge_nested_dicts(base_val, target_val, nested_level=nested_level + 1)
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

def _get_value_at_path(data: Optional[Dict[str, Any]], path: List[str]) -> Optional[Any]:
    """Obtiene un valor en una ruta de subclaves dentro de un diccionario."""
    if not isinstance(data, dict):
        return None
    curr: Any = data
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
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    status_callback: Optional[Callable[[str, Optional[float]], None]] = None,
    target_dir: Optional[Union[str, Path]] = None,
    models_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Recorre recursivamente un diccionario base traducible y genera una versión traducida/copiada
    al idioma destino en un único ciclo lineal gracias a los motores polimórficos de traducción.
    
    Preserva:
    - La estructura y jerarquía exacta del diccionario origen.
    - Claves metadato que inician con `_` (actualizando `_language_name`).
    - Traducciones previamente existentes en `existing_target` si `overwrite=False`.
    - Variables, etiquetas HTML y saltos de línea (mediante el PlaceholderMasker del motor).
    - Códigos regionalizados (ej. pt-BR, es-VE).
    """
    tr_kwargs = dict(kwargs)
    if target_dir is not None:
        tr_kwargs["target_dir"] = target_dir
    if models_dir is not None:
        tr_kwargs["models_dir"] = models_dir
    if status_callback is not None:
        tr_kwargs["status_callback"] = status_callback

    translator = translator_instance or get_translator(engine, **tr_kwargs)
    if status_callback is not None and getattr(translator, "status_callback", None) is None:
        translator.status_callback = status_callback
    existing_target = {} if overwrite else (existing_target or {})

    effective_base = base_data if base_data else (default_dict or {})

    source_code = _normalize_lang_code(source_code)
    target_code = _normalize_lang_code(target_code)
    resolved_name = resolve_language_name(target_code, target_name)

    if status_callback:
        status_callback(
            t18n("i18n_ui.msg_status_analyzing_keys", "Analizando textos y claves a traducir..."),
            0.40,
        )

    # 1. Recolección unificada de textos pendientes para procesamiento en lote
    pending_items: List[Tuple[List[str], str]] = []

    def _collect_texts(current_base: Dict[str, Any], current_existing: Dict[str, Any], current_path: List[str]):
        for key, base_val in current_base.items():
            if key.startswith("_") and not current_path and key != "_default":
                continue

            existing_val = current_existing.get(key) if isinstance(current_existing, dict) else None

            if isinstance(base_val, dict):
                sub_existing = existing_val if isinstance(existing_val, dict) else {}
                _collect_texts(base_val, sub_existing, current_path + [key])
            elif isinstance(base_val, str):
                default_val = _get_value_at_path(default_dict, current_path + [key]) if default_dict else None
                is_untranslated = overwrite or (
                    existing_val is None or
                    existing_val == base_val or
                    (default_val is not None and existing_val == default_val)
                )
                if is_untranslated:
                    pending_items.append((current_path + [key], base_val))

    _collect_texts(effective_base, existing_target, [])

    # 2. Inicializar estructura combinada
    result_data = _merge_nested_dicts(effective_base, existing_target)
    result_data["_language_name"] = resolved_name

    # 3. Ciclo único de procesamiento (traducción real o clonación neutra via NoneTranslator)
    if pending_items:
        paths = [item[0] for item in pending_items]
        raw_texts = [item[1] for item in pending_items]

        try:
            processed_texts = translator.translate_batch(
                raw_texts,
                source_code,
                target_code,
                progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Error al procesar lote de textos ({source_code} -> {target_code}): {e}")
            processed_texts = raw_texts

        # 4. Asignación directa en el árbol destino
        for (path, _), trans_str in zip(pending_items, processed_texts):
            curr = result_data
            for step in path[:-1]:
                curr = curr.setdefault(step, {})
            curr[path[-1]] = trans_str

    return _sort_dictionary(result_data)

def prepare_new_language(
    target_code: str,
    target_name: str,
    default_dict: Optional[Dict[str, Any]] = None,
    base_code: Optional[str] = None,
    base_file: Optional[Union[str, Path]] = None,
    target_dir: Optional[Union[str, Path]] = None,
    auto_translate: bool = True,
    engine: str = "auto",
    overwrite: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    status_callback: Optional[Callable[[str, Optional[float]], None]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Prepara o sincroniza un archivo JSON de idioma en el directorio destino.
    Orquesta en un único pipeline determinista la lectura del origen (memoria vs archivo),
    la detección de sobreescritura, la traducción/copia por lotes y el ordenamiento canónico.
    """
    if not base_code:
        base_code = get_i18n_instance().idioma_def_cod
    else:
        base_code = _normalize_lang_code(base_code)

    target_code = _normalize_lang_code(target_code)
    resolved_name = resolve_language_name(target_code, target_name)

    output_dir = resolve_languages_directory(target_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target_file = output_dir / f"{target_code}.json"

    # 1. Resolución de origen estrictamente determinista y excluyente
    if base_file:
        base_path = Path(base_file)
        if not base_path.exists() or not base_path.is_file():
            raise FileNotFoundError(f"El archivo JSON base no existe: {base_file}")
        with open(base_path, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        if not isinstance(base_data, dict):
            raise ValueError(f"El archivo base debe contener un objeto JSON raíz: {base_file}")
    elif default_dict is not None and isinstance(default_dict, dict):
        base_data = default_dict
    else:
        base_data = get_i18n_instance().get_registered_defaults()

    # 2. Carga de archivo destino si existe y no se solicita sobreescritura
    target_data: Dict[str, Any] = {}
    if not overwrite and target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    target_data = loaded
        except Exception as e:
            logger.warning(f"No se pudo leer archivo destino existente {target_file}: {e}")
            target_data = {}

    # 3. Resolución de motor canónico
    effective_engine = "none" if not auto_translate else engine

    # 4. Procesamiento en pipeline único
    final_output = translate_dictionary(
        base_data=base_data,
        target_code=target_code,
        source_code=base_code,
        target_name=resolved_name,
        engine=effective_engine,
        overwrite=overwrite,
        existing_target=target_data,
        default_dict=default_dict if base_file else None,
        progress_callback=progress_callback,
        status_callback=status_callback,
        target_dir=output_dir,
        **kwargs,
    )

    if status_callback:
        status_callback(
            t18n("i18n_ui.msg_status_saving_file", "Guardando archivo de idioma..."),
            0.98,
        )

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    if status_callback:
        status_callback(
            t18n("i18n_ui.msg_status_completed", "Completado"),
            1.0,
        )

    return {
        "status": "success",
        "target_code": target_code,
        "target_name": final_output.get("_language_name", resolved_name),
        "file_path": str(target_file)
    }

