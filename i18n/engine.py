# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/engine.py

import sys
import json
import string
import logging
from pathlib import Path
from contextvars import ContextVar, Token
from contextlib import contextmanager
from typing import Dict, Any, Callable, List, Optional, Union

logger = logging.getLogger("i18n")

_current_context_lang: ContextVar[Optional[str]] = ContextVar("current_context_lang", default=None)

def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, str]:
    """
    Convierte una estructura JSON jerárquica con diccionarios anidados
    en un diccionario aplanado con notación de puntos.
    Ejemplo:
      {"_default": {"btn_open": "Abrir"}, "modulo1": {"sec1": {"clave": "valor"}}}
      => {"_default.btn_open": "Abrir", "btn_open": "Abrir", "modulo1.sec1.clave": "valor"}
    Pre-indexa claves de la sección _default directamente para permitir búsquedas O(1).
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
            val_str = str(v) if v is not None else ""
            items[new_key] = val_str
            # Pre-indexación directa de la sección _default para acceso O(1)
            if parent_key == "_default":
                items[k] = val_str
            elif parent_key.startswith(f"_default{sep}"):
                sub_key = new_key[len(f"_default{sep}"):]
                items[sub_key] = val_str

    return items


def _safe_format_partial(text: str, kwargs: Dict[str, Any]) -> str:
    """
    Realiza una sustitución parcial segura de variables en cadenas de texto,
    preservando los marcadores no suministrados (ej. '{nombre}').
    """
    try:
        formatter = string.Formatter()
        result: List[str] = []
        for literal_text, field_name, format_spec, conversion in formatter.parse(text):
            result.append(literal_text)
            if field_name is not None:
                if field_name in kwargs:
                    val = kwargs[field_name]
                    if conversion == "r":
                        val = repr(val)
                    elif conversion == "s":
                        val = str(val)
                    elif conversion == "a":
                        val = ascii(val)
                    if format_spec:
                        try:
                            val = format(val, format_spec)
                        except Exception:
                            pass
                    result.append(str(val))
                else:
                    conv = f"!{conversion}" if conversion else ""
                    spec = f":{format_spec}" if format_spec else ""
                    result.append(f"{{{field_name}{conv}{spec}}}")
        return "".join(result)
    except Exception:
        res = text
        for k, v in kwargs.items():
            res = res.replace(f"{{{k}}}", str(v))
        return res


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

    __slots__ = (
        "default_lang",
        "default_lang_name",
        "current_lang",
        "idioma_def_cod",
        "idioma_def_text",
        "idioma_def",
        "internal_dir",
        "external_dir",
        "registered_defaults",
        "active_dictionary",
        "_observers",
        "_loaded_languages",
    )

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

        # Caché en memoria de diccionarios completos por código de idioma
        self._loaded_languages: Dict[str, Dict[str, str]] = {}

        # Observer Pattern: Callbacks de notificación en tiempo real (perezoso)
        self._observers: Optional[List[Callable[[str], None]]] = None

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

    def clear_cache(self) -> None:
        """Limpia el caché de diccionarios cargados en memoria."""
        self._loaded_languages.clear()

    def reload(self) -> None:
        """Recarga el idioma actual re-evaluando la cascada e invalidando el caché."""
        self.clear_cache()
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

    def _build_language_dict(self, lang_code: str) -> Dict[str, str]:
        """
        Construye el diccionario para un código de idioma aplicando la cascada de 7 capas:
        Capa 0: Respaldos registrados en código Python
        Capa 1: Interno {default_lang}.json (Base empaquetado)
        Capa 2: Externo {default_lang}.json (Base usuario)
        Capa 3: Interno {lang_base}.json (Idioma base solicitado empaquetado)
        Capa 4: Externo {lang_base}.json (Idioma base usuario)
        Capa 5: Interno {lang_regional}.json (Idioma regional solicitado empaquetado)
        Capa 6: Externo {lang_regional}.json (Idioma regional usuario)
        """
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

        return merged

    def get_language_dict(self, lang_code: str) -> Dict[str, str]:
        """
        Retorna el diccionario completo para un código de idioma desde el caché en memoria O(1).
        Si no ha sido cargado previamente, lo compila a través de la cascada de 7 capas
        y lo almacena en el caché _loaded_languages.
        """
        cached = self._loaded_languages.get(lang_code)
        if cached is not None:
            return cached
        built = self._build_language_dict(lang_code)
        self._loaded_languages[lang_code] = built
        return built

    def set_language(self, lang_code: str) -> None:
        """
        Establece el idioma activo de la aplicación (entornos de escritorio/CLI),
        actualizando el diccionario activo en memoria y notificando a observadores.
        """
        self.current_lang = lang_code
        self.active_dictionary = self.get_language_dict(lang_code)
        self._notify_observers()

    def t18n(
        self,
        key: str,
        default_text: str = "",
        suppress_markers: bool = False,
        lang: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Busca la clave en el diccionario correspondiente en memoria.
        Ruta caliente O(1) pura directa por clave simple o compuesta.

        Resolución del diccionario:
        1. Si `lang` es provisto explícitamente, consulta en `get_language_dict(lang)`.
        2. Si no, si existe un idioma activo en el contexto actual (`ContextVar`), consulta en él.
        3. En caso contrario, consulta en `self.active_dictionary` (idioma global).

        Si no existe la clave:
        Retorna el default_text (formateado con **kwargs si existen).
        Si suppress_markers=False, envuelve el texto formateado en marcadores '<texto>'.
        Si suppress_markers=True, retorna el default_text limpio sin marcadores '<>'.
        """
        if lang is not None:
            dictionary = self.get_language_dict(lang)
        else:
            ctx_lang = _current_context_lang.get()
            if ctx_lang is not None:
                dictionary = self.get_language_dict(ctx_lang)
            else:
                dictionary = self.active_dictionary

        raw_text = dictionary.get(key)
        if raw_text is not None:
            return self._format_string(raw_text, **kwargs)

        formatted_default = self._format_string(default_text, **kwargs)
        if suppress_markers:
            return formatted_default

        return f"<{formatted_default}>"

    def _format_string(self, text: str, **kwargs) -> str:
        """Formatea la cadena de texto de forma segura con sustitución parcial ante variables faltantes."""
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except KeyError as ke:
            logger.warning(f"Variable faltante en texto '{text}': {ke}. Aplicando formateo parcial.")
            return _safe_format_partial(text, kwargs)
        except (ValueError, IndexError) as e:
            logger.warning(f"Error al formatear texto '{text}' con variables {kwargs}: {e}")
            return _safe_format_partial(text, kwargs)

    def has_key(self, key: str, lang: Optional[str] = None) -> bool:
        """Verifica si la clave existe en el diccionario activo o especificado (O(1))."""
        if lang is not None:
            dictionary = self.get_language_dict(lang)
        else:
            ctx_lang = _current_context_lang.get()
            if ctx_lang is not None:
                dictionary = self.get_language_dict(ctx_lang)
            else:
                dictionary = self.active_dictionary
        return key in dictionary

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Permite acceso tipo diccionario: self.translations.get('key', default)."""
        if self.has_key(key):
            return self.t18n(key, str(default) if default is not None else "")
        return default

    def __getitem__(self, key: str) -> str:
        """Permite acceso por corchetes: self.translations['key']."""
        if self.has_key(key):
            return self.t18n(key, "")
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
        if self._observers is None:
            self._observers = []
        if callback not in self._observers:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Desasocia un callback previamente suscrito."""
        if self._observers and callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notifica a todos los suscriptores pasando el código del idioma actual."""
        if not self._observers:
            return
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

def set_context_language(lang_code: Optional[str]) -> Token:
    """Establece el idioma activo para el contexto de ejecución actual (async/thread)."""
    return _current_context_lang.set(lang_code)

def get_context_language() -> Optional[str]:
    """Obtiene el idioma activo del contexto de ejecución actual, si está definido."""
    return _current_context_lang.get()

def reset_context_language(token: Token) -> None:
    """Restablece el idioma del contexto a su estado anterior usando el token de ContextVar."""
    _current_context_lang.reset(token)

@contextmanager
def use_language(lang_code: str):
    """
    Context manager para ejecutar un bloque de código bajo un idioma específico
    de forma aislada y segura para el contexto actual (async/thread).
    """
    token = _current_context_lang.set(lang_code)
    try:
        yield
    finally:
        _current_context_lang.reset(token)

def clear_cache() -> None:
    """Limpia el caché de diccionarios en memoria de la instancia global."""
    get_i18n_instance().clear_cache()

def t18n(
    key: str,
    default_text: str = "",
    suppress_markers: bool = False,
    lang: Optional[str] = None,
    **kwargs
) -> str:
    """Función global canónica de traducción."""
    global _global_instance
    if _global_instance is None:
        _global_instance = I18nManager()
    return _global_instance.t18n(
        key,
        default_text,
        suppress_markers=suppress_markers,
        lang=lang,
        **kwargs
    )

def export_active_dictionary(output_path: Optional[Union[str, Path]] = None) -> Path:
    """Exporta el diccionario activo de la instancia global a un archivo JSON."""
    return get_i18n_instance().export_active_dictionary(output_path)

def register_defaults(defaults_dict: Dict[str, Any]) -> None:
    """Registra un diccionario de valores por defecto global (Capa 0)."""
    get_i18n_instance().register_defaults(defaults_dict)

def register_section_defaults(section: str, section_dict: Dict[str, Any]) -> None:
    """Registra valores por defecto para una sección específica global."""
    get_i18n_instance().register_section_defaults(section, section_dict)

