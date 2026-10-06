# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: i18n/engine.py

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional, Union

logger = logging.getLogger("i18n")

def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, str]:
    """
    Convierte una estructura JSON jerárquica con diccionarios anidados
    en un diccionario aplanado con notación de puntos.
    Ejemplo:
      {"_default": {"btn_open": "Abrir"}, "modulo1": {"sec1": {"clave": "valor"}}}
      => {"_default.btn_open": "Abrir", "modulo1.sec1.clave": "valor"}
    Ignora metadatos en la raíz como _language_name pero procesa la sección _default.
    """
    items: Dict[str, str] = {}
    for k, v in d.items():
        if k.startswith("_") and not parent_key and k != "_default":
            continue

        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key, sep=sep))
        else:
            items[new_key] = str(v) if v is not None else ""

    return items


def resolve_languages_directory(
    custom_dir: Optional[Union[str, Path]] = None,
    base_path: Optional[Union[str, Path]] = None
) -> Path:
    """
    Resuelve de forma centralizada la ruta del directorio de idiomas (`resources/languages`).

    Prioridad:
    1. Si `custom_dir` es provisto explícitamente, se usa dicha ruta.
    2. Si se especifica `base_path` (archivo o directorio base):
       - Si es un archivo: `<base_path.parent>/resources/languages`
       - Si es un directorio: `<base_path>/resources/languages`
    3. Si existe empaquetado PyInstaller (`sys._MEIPASS/resources/languages`), se usa este.
    4. Directorio por defecto: `Path.cwd() / "resources" / "languages"`
    """
    if custom_dir:
        return Path(custom_dir)

    if base_path:
        p = Path(base_path)
        if p.is_file() or (p.suffix and not p.is_dir()):
            return p.parent / "resources" / "languages"
        return p / "resources" / "languages"

    if hasattr(sys, "_MEIPASS"):
        meipass_dir = Path(sys._MEIPASS) / "resources" / "languages"
        if meipass_dir.exists():
            return meipass_dir

    return Path.cwd() / "resources" / "languages"


class I18nManager:
    """
    Gestor principal de i18n para Python con estrategia de carga en cascada y sobreescritura:
    0. Diccionario de respaldos registrados en código (Capa 0)
    1. Interno es.json (Base empaquetado)
    2. Externo es.json (Base usuario)
    3. Interno {lang_base}.json (Idioma base solicitado, ej. pt.json)
    4. Externo {lang_base}.json (Idioma base usuario, ej. pt.json)
    5. Interno {lang_regional}.json (Idioma regional solicitado, ej. pt-BR.json)
    6. Externo {lang_regional}.json (Idioma regional usuario, ej. pt-BR.json)
    """

    def __init__(
        self,
        internal_dir: Optional[str] = None,
        external_dir: Optional[str] = None,
        default_lang: Optional[Union[Dict[str, str], str]] = None
    ):
        # Configuración del idioma base/por defecto
        if isinstance(default_lang, dict) and default_lang:
            code, name = list(default_lang.items())[0]
            self.idioma_def_cod = code
            self.idioma_def_text = name
            self.idioma_def = {code: name}
        elif isinstance(default_lang, str) and default_lang:
            self.idioma_def_cod = default_lang
            self.idioma_def_text = "Español" if default_lang == "es" else default_lang.upper()
            self.idioma_def = {self.idioma_def_cod: self.idioma_def_text}
        else:
            self.idioma_def_cod = "es"
            self.idioma_def_text = "Español"
            self.idioma_def = {"es": "Español"}

        self.default_lang = self.idioma_def_cod
        self.default_lang_name = self.idioma_def_text
        self.current_lang = self.idioma_def_cod

        # Directorio interno (empaquetado / recursos de app)
        self.internal_dir = Path(internal_dir) if internal_dir else self._find_internal_dir()
        # Directorio externo (usuario / editable)
        self.external_dir = Path(external_dir) if external_dir else self._find_external_dir()

        # Diccionario de respaldos registrados en código (Capa 0)
        self.registered_defaults: Dict[str, str] = {}

        # Diccionario activo fusionado en memoria
        self.active_dictionary: Dict[str, str] = {}

        # Observer Pattern: Callbacks de notificación en tiempo real
        self._observers: List[Callable[[str], None]] = []

        # Cargar idioma inicial
        self.set_language(self.idioma_def_cod)

    def register_defaults(self, defaults_dict: Dict[str, Any]) -> None:
        """Registra un diccionario de valores por defecto (Capa 0 de respaldo)."""
        flattened = _flatten_dict(defaults_dict)
        self.registered_defaults.update(flattened)
        self.reload()

    def register_section_defaults(self, section: str, section_dict: Dict[str, Any]) -> None:
        """Registra valores por defecto para una sección específica (ej: 'licencia', 'ayuda')."""
        self.register_defaults({section: section_dict})

    def _find_internal_dir(self) -> Path:
        """Determina la ruta de la carpeta interna (empaquetada en PyInstaller o recursos)."""
        if hasattr(sys, "_MEIPASS"):
            meipass_dir = Path(sys._MEIPASS) / "resources" / "languages"
            if meipass_dir.exists():
                return meipass_dir

        for candidate in [
            Path.cwd() / "resources" / "languages",
            Path(__file__).resolve().parent.parent / "resources" / "languages",
            Path(__file__).resolve().parent.parent.parent / "resources" / "languages",
        ]:
            if candidate.exists():
                return candidate

        return resolve_languages_directory()

    def _find_external_dir(self) -> Path:
        """Determina la ruta por defecto para idiomas externos de usuario."""
        return resolve_languages_directory()

    def set_internal_languages_dir(self, directory: str) -> None:
        """Establece la ruta del directorio interno de idiomas."""
        self.internal_dir = Path(directory)
        self.reload()

    def set_external_languages_dir(self, directory: str) -> None:
        """Establece la ruta del directorio externo de idiomas (usuario)."""
        self.external_dir = Path(directory)
        self.reload()

    def reload(self) -> None:
        """Recarga el idioma actual re-evaluando la cascada."""
        self.set_language(self.current_lang)

    def _load_and_flatten_json(self, file_path: Path) -> Dict[str, str]:
        """Carga un archivo JSON y lo aplana a notación de puntos."""
        if not file_path.exists():
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return _flatten_dict(data)
        except Exception as e:
            logger.error(f"Error al leer o procesar archivo JSON {file_path}: {e}")
        return {}

    def set_language(self, lang_code: str) -> None:
        """
        Establece el idioma activo aplicando la cascada de capas:
        Capa 0: Respaldos registrados en código Python
        Capa 1: Interno {default_lang}.json (Base empaquetado)
        Capa 2: Externo {default_lang}.json (Base usuario)
        Capa 3: Interno {lang_base}.json (Idioma base solicitado empaquetado)
        Capa 4: Externo {lang_base}.json (Idioma base usuario)
        Capa 5: Interno {lang_regional}.json (Idioma regional solicitado empaquetado)
        Capa 6: Externo {lang_regional}.json (Idioma regional usuario)
        """
        self.current_lang = lang_code
        merged: Dict[str, str] = {}

        # Capa 0: Diccionario de respaldos registrados en código
        merged.update(self.registered_defaults)

        parts = lang_code.split("-")
        base_code = parts[0]
        regional_code = lang_code if len(parts) > 1 else None
        has_external = self.external_dir != self.internal_dir

        # Capa 1: Interno base (es.json)
        merged.update(self._load_and_flatten_json(self.internal_dir / f"{self.default_lang}.json"))

        # Capa 2: Externo base (es.json) si existe
        if has_external:
            merged.update(self._load_and_flatten_json(self.external_dir / f"{self.default_lang}.json"))

        # Capa 3: Interno idioma base (ej: pt.json)
        if base_code != self.default_lang:
            merged.update(self._load_and_flatten_json(self.internal_dir / f"{base_code}.json"))

            # Capa 4: Externo idioma base (ej: pt.json)
            if has_external:
                merged.update(self._load_and_flatten_json(self.external_dir / f"{base_code}.json"))

        # Capa 5: Interno idioma regional (ej: pt-BR.json)
        if regional_code:
            merged.update(self._load_and_flatten_json(self.internal_dir / f"{regional_code}.json"))

            # Capa 6: Externo idioma regional (ej: pt-BR.json)
            if has_external:
                merged.update(self._load_and_flatten_json(self.external_dir / f"{regional_code}.json"))

        self.active_dictionary = merged
        self._notify_observers()

    def translate(self, key: str, default_text: str = "", suppress_markers: bool = False, **kwargs) -> str:
        """
        Busca la clave en el diccionario activo en memoria.
        Las claves sin notación de puntos (ej: 'btn_open') se buscan automáticamente bajo la sección '_default.btn_open'.
        Las claves compuestas (ej: 'modulo1.sec1.clave') se buscan directamente.
        
        Si no existe la clave:
        Retorna el default_text (formateado con **kwargs si existen).
        Si suppress_markers=False, envuelve el texto formateado en marcadores '<texto>'.
        Si suppress_markers=True, retorna el default_text limpio sin marcadores '<>'.
        """
        full_key = f"_default.{key}" if "." not in key else key
        raw_text = self.active_dictionary.get(full_key)

        if raw_text is None and key in self.active_dictionary:
            raw_text = self.active_dictionary.get(key)

        if raw_text is not None:
            return self._format_string(raw_text, **kwargs)

        formatted_default = self._format_string(default_text, **kwargs)
        if suppress_markers:
            return formatted_default

        return f"<{formatted_default}>"

    def _format_string(self, text: str, **kwargs) -> str:
        """Formatea la cadena de texto de forma segura sin lanzar excepciones."""
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError) as e:
            logger.warning(f"Error al formatear texto '{text}' con variables {kwargs}: {e}")
            return text

    def has_key(self, key: str) -> bool:
        """Verifica si la clave existe en el diccionario activo (con o sin prefijo '_default.')."""
        if key in self.active_dictionary:
            return True
        if "." not in key and f"_default.{key}" in self.active_dictionary:
            return True
        return False

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Permite acceso tipo diccionario: self.translations.get('key', default)."""
        if self.has_key(key):
            return self.translate(key, str(default) if default is not None else "")
        return default

    def __getitem__(self, key: str) -> str:
        """Permite acceso por corchetes: self.translations['key']."""
        if self.has_key(key):
            return self.translate(key, "")
        raise KeyError(key)

    def get_available_languages(
        self,
        custom_default: Optional[Dict[str, str]] = None,
        by_name: bool = False
    ) -> Union[List[Dict[str, str]], Dict[str, str]]:
        """
        Escanea tanto el directorio interno como el externo buscando archivos .json.
        Lee '_language_name' de cada uno y fusiona la lista por código.
        Asegura que el idioma por defecto configurado siempre esté incluido.

        Si by_name=True, retorna un diccionario {nombre: código} (ej. {'Español': 'es'}).
        De lo contrario, retorna una lista de diccionarios [{'code': 'es', 'name': 'Español'}, ...].
        """
        lang_map: Dict[str, str] = {}

        # 1. Registrar siempre el idioma por defecto configurado en i18n
        lang_map.update(self.idioma_def)

        # 2. Si se provee un custom_default adicional
        if custom_default:
            lang_map.update(custom_default)

        # 3. Escanear directorio interno y externo
        self._scan_dir_into_map(self.internal_dir, lang_map)

        if self.external_dir and self.external_dir.exists():
            self._scan_dir_into_map(self.external_dir, lang_map)

        if by_name:
            return {name: code for code, name in sorted(lang_map.items())}

        return [{"code": code, "name": name} for code, name in sorted(lang_map.items())]

    def _scan_dir_into_map(self, directory: Path, target_map: Dict[str, str]) -> None:
        """Auxiliar para escanear archivos .json en un directorio."""
        if not directory.exists():
            return
        for file in sorted(directory.glob("*.json")):
            if file.name == "default.json" or " " in file.name:
                continue
            code = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        name = data.get("_language_name", code.upper())
                        target_map[code] = name
            except Exception as e:
                logger.warning(f"Error al escanear lenguaje en {file}: {e}")

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Suscribe un callback para notificar cambios de idioma."""
        if callback not in self._observers:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Desasocia un callback previamente suscrito."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notifica a todos los suscriptores pasando el código del idioma actual."""
        for callback in self._observers:
            try:
                callback(self.current_lang)
            except Exception as e:
                logger.error(f"Error en observer de i18n: {e}")

    def export_active_dictionary(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Exporta el diccionario activo en memoria (self.active_dictionary) tal como está a un archivo JSON.

        :param output_path: Ruta de archivo o directorio destino.
                            - Si es None o vacío, se guarda en '{cwd}/dictionary.json'.
                            - Si es un directorio o ruta terminada en separador, se guarda como 'dictionary.json' en dicha carpeta.
                            - Si es una ruta completa de archivo, se utiliza el nombre especificado.
        :return: Path del archivo JSON exportado.
        """
        if not output_path:
            target_file = Path.cwd() / "dictionary.json"
        else:
            p = Path(output_path)
            if p.is_dir() or str(output_path).endswith(("/", "\\")):
                target_file = p / "dictionary.json"
            else:
                target_file = p

        target_file.parent.mkdir(parents=True, exist_ok=True)

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(self.active_dictionary, f, ensure_ascii=False, indent=2)

        return target_file


# Instancia Singleton global para fácil consumo en toda la aplicación
_global_instance: Optional[I18nManager] = None

def get_i18n_instance(default_lang: Optional[Union[Dict[str, str], str]] = None) -> I18nManager:
    global _global_instance
    if _global_instance is None:
        _global_instance = I18nManager(default_lang=default_lang)
    elif default_lang is not None:
        if isinstance(default_lang, dict) and default_lang:
            code, name = list(default_lang.items())[0]
            _global_instance.idioma_def_cod = code
            _global_instance.idioma_def_text = name
            _global_instance.idioma_def = {code: name}
            _global_instance.default_lang = code
            _global_instance.default_lang_name = name
        elif isinstance(default_lang, str) and default_lang:
            _global_instance.idioma_def_cod = default_lang
            _global_instance.idioma_def_text = "Español" if default_lang == "es" else default_lang.upper()
            _global_instance.idioma_def = {default_lang: _global_instance.idioma_def_text}
            _global_instance.default_lang = default_lang
            _global_instance.default_lang_name = _global_instance.idioma_def_text
    return _global_instance

def translate(key: str, default_text: str = "", suppress_markers: bool = False, **kwargs) -> str:
    """Función global de traducción."""
    return get_i18n_instance().translate(key, default_text, suppress_markers=suppress_markers, **kwargs)

def export_active_dictionary(output_path: Optional[Union[str, Path]] = None) -> Path:
    """Exporta el diccionario activo de la instancia global a un archivo JSON."""
    return get_i18n_instance().export_active_dictionary(output_path)

# Alias t18n explícitamente solicitado por el usuario
t18n = translate
register_defaults = lambda d: get_i18n_instance().register_defaults(d)
register_section_defaults = lambda sec, d: get_i18n_instance().register_section_defaults(sec, d)

