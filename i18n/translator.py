# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/translator.py

"""
Módulo de Traducción y Enmascarado de Elementos Especiales para i18n.
Soporta enmascarado de variables, HTML, saltos de línea y URLs, así como
motores de traducción modulares: MockTranslator, GoogleTranslator (deep-translator) y ArgosTranslator.
Soporta códigos regionalizados (ej. pt-BR, es-VE), callback de progreso y detector de alucinaciones.
"""
import sys
import re
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Callable, Dict, Any, Union

from .engine import resolve_languages_directory, t18n

logger = logging.getLogger("i18n.translator")


class PlaceholderMasker:
    """
    Se encarga de enmascarar y desenmascarar elementos especiales en cadenas de texto
    (variables de formato Python, etiquetas HTML, saltos de línea, URLs)
    para evitar que los motores de traducción los alteren o traduzcan.
    """

    TOKEN_REGEX = re.compile(
        r"(\{[^{}]+\}"
        r"|%(?:\([^)]+\))?[sdfr]"
        r"|<[^>]+>"
        r"|\r?\n"
        r"|https?://[^\s<>]+)"
    )

    # Soporta tokens en formato [v0], <x0/>, o ___PH_0___
    MASK_FIND_REGEX = re.compile(
        r"\[\s*v\s*(\d+)\s*\]|<\s*x\s*(\d+)\s*/?>|___\s*PH\s*_\s*(\d+)\s*___",
        re.IGNORECASE
    )

    @classmethod
    def mask(cls, text: str) -> Tuple[str, List[str]]:
        """
        Enmascara los elementos especiales de una cadena de texto usando tokens NMT limpios [v0], [v1]...
        """
        if not text:
            return text, []

        tokens: List[str] = []

        def replacer(match: re.Match) -> str:
            token = match.group(0)
            token_idx = len(tokens)
            tokens.append(token)
            return f"[v{token_idx}]"

        masked_text = cls.TOKEN_REGEX.sub(replacer, text)
        return masked_text, tokens

    @classmethod
    def is_hallucinated(cls, translated_text: str, original_text: str) -> bool:
        """
        Detecta si el motor de traducción generó alucinaciones o bucles repetitivos infinitos.
        """
        if not translated_text:
            return False
        # Si el texto traducido es anormalmente largo respecto al original
        if len(translated_text) > max(3 * len(original_text), 60):
            # Patrón de bucle repetitivo de 4 a 25 caracteres repetidos más de 4 veces seguidas
            if re.search(r"(.{4,25})\1{4,}", translated_text):
                return True
        return False

    @classmethod
    def unmask(cls, masked_text: str, tokens: List[str], original_text: Optional[str] = None) -> str:
        """
        Restaura los tokens originales en el texto traducido a partir de sus máscaras.
        Si se detecta alucinación o corrupción severa por el motor, retorna el texto original.
        """
        if not masked_text or not tokens:
            return masked_text

        # Detectar alucinaciones del motor de traducción
        if original_text and cls.is_hallucinated(masked_text, original_text):
            logger.error("Detector de alucinaciones: El motor generó un texto repetitivo/corrupto. Usando texto original.")
            return original_text

        used_indices = set()

        def replacer(match: re.Match) -> str:
            raw_idx = match.group(1) or match.group(2) or match.group(3)
            try:
                idx = int(raw_idx)
                if 0 <= idx < len(tokens):
                    used_indices.add(idx)
                    return tokens[idx]
            except (ValueError, TypeError):
                pass
            return match.group(0)

        result = cls.MASK_FIND_REGEX.sub(replacer, masked_text)

        # Si el resultado desenmascarado tiene alucinación repetitiva, restaurar original
        if original_text and cls.is_hallucinated(result, original_text):
            logger.error("Detector de alucinaciones post-unmask: Usando texto original.")
            return original_text

        for i, token in enumerate(tokens):
            if i not in used_indices:
                logger.warning(f"El motor de traducción omitió la máscara [v{i}] ({token})")

        return result

def _normalize_lang_code(code: str) -> str:
    """Normaliza un código de idioma (ej: 'pt_BR' -> 'pt-BR', 'ES-ve' -> 'es-VE')."""
    if not code:
        return code
    clean = code.replace("_", "-").strip()
    parts = clean.split("-")
    if len(parts) == 1:
        return parts[0].lower()
    return f"{parts[0].lower()}-{parts[1].upper()}"

def _get_primary_lang_code(code: str) -> str:
    """Obtiene el código de idioma primario sin regionalización (ej: 'pt-BR' -> 'pt')."""
    norm = _normalize_lang_code(code)
    return norm.split("-")[0]

class CompactChunk:
    """
    Estructura de datos que encapsula un bloque de cadenas compactadas.
    """
    __slots__ = ("payload", "items", "is_delimited")

    def __init__(
        self,
        payload: str,
        items: List[Tuple[int, str, List[str], str]],
        is_delimited: bool = False
    ):
        self.payload = payload
        self.items = items  # Lista de tuplas: (orig_idx, orig_text, tokens, masked_text)
        self.is_delimited = is_delimited


def compacta_cadenas(
    texts: List[str],
    config: Optional[Dict[str, Any]] = None
) -> Tuple[List[CompactChunk], Dict[int, str]]:
    """
    Agrupa cadenas de texto de forma estándar según las restricciones de longitud
    y delimitador configuradas para cada motor de traducción.
    Preserva los textos vacíos y enmascara los textos válidos.
    """
    if config is None:
        config = {}

    delimiter = config.get("delimiter")
    max_chars = config.get("max_chars") or 3000
    max_items = config.get("max_items") or 1

    empty_slots: Dict[int, str] = {}
    valid_items: List[Tuple[int, str, List[str], str]] = []

    for i, t in enumerate(texts):
        if not t or not t.strip():
            empty_slots[i] = t
        else:
            masked_str, tokens = PlaceholderMasker.mask(t)
            valid_items.append((i, t, tokens, masked_str))

    if not valid_items:
        return [], empty_slots

    chunks: List[CompactChunk] = []

    if delimiter and max_items > 1:
        curr_items: List[Tuple[int, str, List[str], str]] = []
        curr_len = 0
        del_len = len(delimiter)

        for item in valid_items:
            item_len = len(item[3]) + del_len
            if curr_items and (curr_len + item_len > max_chars or len(curr_items) >= max_items):
                payload = delimiter.join(it[3] for it in curr_items)
                chunks.append(CompactChunk(payload=payload, items=curr_items, is_delimited=True))
                curr_items = [item]
                curr_len = item_len
            else:
                curr_items.append(item)
                curr_len += item_len

        if curr_items:
            payload = delimiter.join(it[3] for it in curr_items)
            chunks.append(CompactChunk(payload=payload, items=curr_items, is_delimited=True))
    else:
        for item in valid_items:
            chunks.append(CompactChunk(payload=item[3], items=[item], is_delimited=False))

    return chunks, empty_slots


def descompacta_cadenas(
    translated_chunks: List[Tuple[CompactChunk, str]],
    empty_slots: Dict[int, str],
    total_texts: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    """
    Reconstruye la lista de textos traducidos a partir de los bloques traducidos,
    desenmascarando elementos especiales y notificando el progreso de manera uniforme.
    """
    results: List[str] = ["" for _ in range(total_texts)]

    # Colocar textos vacíos en sus posiciones originales
    for idx, t in empty_slots.items():
        results[idx] = t

    processed_count = 0

    # Notificar progreso para textos vacíos si hay observador
    if progress_callback and empty_slots:
        for idx in sorted(empty_slots.keys()):
            processed_count += 1
            try:
                progress_callback(processed_count, total_texts, empty_slots[idx])
            except Exception:
                pass

    DELIMITER_SPLIT = "[#=$=%]"

    for chunk, translated_payload in translated_chunks:
        if chunk.is_delimited:
            parts = [p.strip() for p in translated_payload.split(DELIMITER_SPLIT)]
            if len(parts) == len(chunk.items):
                for (orig_idx, orig_text, tokens, _), trans_part in zip(chunk.items, parts):
                    if PlaceholderMasker.is_hallucinated(trans_part, orig_text):
                        results[orig_idx] = orig_text
                    else:
                        results[orig_idx] = PlaceholderMasker.unmask(trans_part, tokens, orig_text)
                    processed_count += 1
                    if progress_callback:
                        try:
                            progress_callback(processed_count, total_texts, orig_text)
                        except Exception:
                            pass
            else:
                logger.warning(
                    f"Desalineación de delimitadores en descompacta_cadenas "
                    f"(esperados {len(chunk.items)}, obtenidos {len(parts)}). Usando texto original."
                )
                for (orig_idx, orig_text, _, _) in chunk.items:
                    results[orig_idx] = orig_text
                    processed_count += 1
                    if progress_callback:
                        try:
                            progress_callback(processed_count, total_texts, orig_text)
                        except Exception:
                            pass
        else:
            orig_idx, orig_text, tokens, _ = chunk.items[0]
            if PlaceholderMasker.is_hallucinated(translated_payload, orig_text):
                results[orig_idx] = orig_text
            else:
                results[orig_idx] = PlaceholderMasker.unmask(translated_payload, tokens, orig_text)
            processed_count += 1
            if progress_callback:
                try:
                    progress_callback(processed_count, total_texts, orig_text)
                except Exception:
                    pass

    return results


def proceso_unico(
    translator: "BaseTranslator",
    texts: List[str],
    source_lang: str,
    target_lang: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    """
    Pipeline único y estandarizado de traducción por lotes.
    Compacta cadenas según la configuración del motor, ejecuta la traducción
    por bloques con tolerancia a fallos, descompacta y notifica el progreso.
    """
    if not texts:
        return []

    # 1. Configuración de compactación directa según engine_id
    engine_id = getattr(translator, "engine_id", "mock")
    registry_entry = ENGINE_REGISTRY.get(engine_id, {})
    compact_config = registry_entry.get("compacta_cadenas", {
        "delimiter": None,
        "max_chars": None,
        "max_items": 1
    })

    # 2. Normalización de códigos de idioma
    src_primary = _get_primary_lang_code(source_lang)
    tgt_primary = _get_primary_lang_code(target_lang)

    # 3. Compactar cadenas con longitud y delimitador configurados
    chunks, empty_slots = compacta_cadenas(texts, compact_config)

    total_texts = len(texts)
    translated_chunks: List[Tuple[CompactChunk, str]] = []
    DELIMITER_SPLIT = "[#=$=%]"

    # 4. Ciclo único de traducción
    for chunk in chunks:
        try:
            tt = translator.translate(chunk.payload, source_lang, target_lang)
        except Exception as exc:
            logger.warning(f"Error al traducir bloque ({src_primary} -> {tgt_primary}): {exc}")
            tt = chunk.payload

        # Si el bloque es delimitado y la respuesta alteró delimitadores, fallback por elemento
        if chunk.is_delimited:
            parts = [p.strip() for p in tt.split(DELIMITER_SPLIT)]
            if len(parts) != len(chunk.items):
                logger.warning(
                    f"Respuesta de bloque alteró delimitadores ({len(parts)} != {len(chunk.items)}). "
                    f"Ejecutando fallback elemento por elemento."
                )
                recovered_parts: List[str] = []
                for item in chunk.items:
                    try:
                        elem_tt = translator.translate(item[3], source_lang, target_lang)
                    except Exception:
                        elem_tt = item[3]
                    recovered_parts.append(elem_tt)
                tt = f" {DELIMITER_SPLIT} ".join(recovered_parts)

        translated_chunks.append((chunk, tt))

    # 5. Descompactar cadenas y reportar progreso
    texts_result = descompacta_cadenas(
        translated_chunks=translated_chunks,
        empty_slots=empty_slots,
        total_texts=total_texts,
        progress_callback=progress_callback
    )

    return texts_result


class BaseTranslator(ABC):
    """
    Interfaz base abstracta para los motores de traducción.
    """
    engine_id: str = "unknown"
    status_callback: Optional[Callable[[str, Optional[float]], None]] = None

    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Traduce una sola cadena de texto.
        """
        pass

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        """
        Traduce una lista de cadenas de texto delegando en el pipeline unificado proceso_unico.
        """
        return proceso_unico(
            translator=self,
            texts=texts,
            source_lang=source_lang,
            target_lang=target_lang,
            progress_callback=progress_callback
        )

    def verify_language(
        self,
        source_lang: str,
        target_lang: str,
        is_online: bool = True,
        **kwargs: Any,
    ) -> bool:
        """
        Verifica si el motor puede procesar el par de idiomas bajo las condiciones dadas.
        Por defecto, los motores base o neutros retornan True.
        """
        return True


class MockTranslator(BaseTranslator):
    """
    Motor de traducción ficticio (Mock) para pruebas unitarias e integración sin red ni modelos.
    """
    engine_id: str = "mock"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text
        return f"[{target_lang.upper()}] {text}"


class NoneTranslator(BaseTranslator):
    """
    Motor de traducción neutro (identidad) para clonación o copia directa sin traducción.
    Preserva intacto el texto original y notifica el progreso en lote a la UI.
    """
    engine_id: str = "none"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return text


class GoogleTranslatorEngine(BaseTranslator):
    """
    Motor de traducción que utiliza la librería `deep-translator` (Google Translate Backend gratis).
    Soporta códigos de idiomas regionalizados como pt-BR, zh-CN, es-VE.
    Incluye respaldo online ante límites de tasa HTTP 429.
    """
    engine_id: str = "google"

    def __init__(self, warn_if_missing: bool = True):
        try:
            from deep_translator import GoogleTranslator as DeepGoogleTranslator
            self._backend_cls = DeepGoogleTranslator
            self._available = True
        except ImportError:
            self._available = False
            if warn_if_missing:
                if getattr(sys, "frozen", False):
                    logger.warning("El motor `deep-translator` no fue incluido en el ejecutable empaquetado.")
                else:
                    logger.warning("`deep-translator` no está instalado. Instálalo con `pip install deep-translator`.")

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_translator_instance(self, source_lang: str, target_lang: str):
        src_norm = _normalize_lang_code(source_lang)
        tgt_norm = _normalize_lang_code(target_lang)
        try:
            return self._backend_cls(source=src_norm, target=tgt_norm)
        except Exception:
            src_primary = _get_primary_lang_code(src_norm)
            tgt_primary = _get_primary_lang_code(tgt_norm)
            return self._backend_cls(source=src_primary, target=tgt_primary)

    def _get_backup_translator_instance(self, source_lang: str, target_lang: str):
        """Instancia de respaldo online (MyMemory) en caso de que Google bloquee la IP con 429."""
        try:
            from deep_translator import MyMemoryTranslator
            from deep_translator.constants import MY_MEMORY_LANGUAGES_TO_CODES

            valid_codes = set(MY_MEMORY_LANGUAGES_TO_CODES.values())

            def _resolve_mm_code(code: str) -> str:
                norm = _normalize_lang_code(code)
                if norm in valid_codes:
                    return norm
                primary = _get_primary_lang_code(norm)
                same_country = f"{primary}-{primary.upper()}"
                if same_country in valid_codes:
                    return same_country
                if primary == "en":
                    return "en-GB"
                match = next((c for c in valid_codes if c.lower().startswith(f"{primary}-")), None)
                return match or norm

            src_mm = _resolve_mm_code(source_lang)
            tgt_mm = _resolve_mm_code(target_lang)
            return MyMemoryTranslator(source=src_mm, target=tgt_mm)
        except Exception:
            return None

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text

        if not self._available:
            if getattr(sys, "frozen", False):
                raise RuntimeError("`deep-translator` no está incluido en el ejecutable empaquetado.")
            raise RuntimeError("`deep-translator` no está disponible en la instalación de Python.")

        translator = self._get_translator_instance(source_lang, target_lang)
        try:
            return translator.translate(text)
        except Exception:
            backup_tr = self._get_backup_translator_instance(source_lang, target_lang)
            if backup_tr:
                return backup_tr.translate(text)
            raise

    def verify_language(
        self,
        source_lang: str,
        target_lang: str,
        is_online: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Verifica disponibilidad de la librería deep_translator y conexión a Internet."""
        return self._available and is_online


class ArgosTranslatorEngine(BaseTranslator):
    """
    Motor de traducción 100% offline utilizando `argostranslate`.
    Soporta fallback de idiomas regionalizados al código primario (ej. pt-BR -> pt),
    traducción directa y cadenas compuestas por pivote (ej. es -> en -> it) con
    descarga e instalación en el directorio dedicado `languages/argos`.
    """
    engine_id: str = "argos"

    def __init__(
        self,
        warn_if_missing: bool = True,
        models_dir: Optional[Union[str, Path]] = None,
        target_dir: Optional[Union[str, Path]] = None,
        status_callback: Optional[Callable[[str, Optional[float]], None]] = None,
        **kwargs: Any,
    ):
        self._translators: Dict[str, Any] = {}
        self.status_callback = status_callback
        if models_dir:
            self.models_dir = Path(models_dir)
        elif target_dir:
            self.models_dir = Path(target_dir) / "argos"
        else:
            self.models_dir = resolve_languages_directory() / "argos"
        try:
            import argostranslate.package
            import argostranslate.translate
            import argostranslate.settings
            import ctranslate2
            self._argos_pkg = argostranslate.package
            self._argos_tr = argostranslate.translate
            self._argos_settings = argostranslate.settings
            self._ctranslate2 = ctranslate2
            self._available = True

            # Configuración estricta del directorio de paquetes dedicado
            self.models_dir.mkdir(parents=True, exist_ok=True)
            self._argos_settings.package_data_dir = self.models_dir
            self._argos_settings.package_dirs = [self.models_dir]
        except ImportError:
            self._available = False
            if warn_if_missing:
                if getattr(sys, "frozen", False):
                    logger.warning("El motor `argostranslate` no fue incluido en el ejecutable.")
                else:
                    logger.warning("`argostranslate` no está instalado. Instálalo con `pip install argostranslate`.")

    @property
    def is_available(self) -> bool:
        return self._available

    def is_pair_installed(self, source_lang: str, target_lang: str) -> bool:
        """
        Verifica si los paquetes de traducción requeridos para el par (directo o con pivote en inglés)
        ya se encuentran instalados en el directorio local dedicado.
        """
        if not self._available:
            return False
        src_primary = _get_primary_lang_code(source_lang)
        tgt_primary = _get_primary_lang_code(target_lang)
        if src_primary == tgt_primary:
            return True

        try:
            installed_packages = self._argos_pkg.get_installed_packages()
            installed_pairs = {(p.from_code, p.to_code) for p in installed_packages}
            # 1. Par directo
            if (src_primary, tgt_primary) in installed_pairs:
                return True

            # 2. Pivote mediante inglés ('en')
            has_src_to_en = (src_primary == "en") or ((src_primary, "en") in installed_pairs)
            has_en_to_tgt = (tgt_primary == "en") or (("en", tgt_primary) in installed_pairs)
            if has_src_to_en and has_en_to_tgt:
                return True
        except Exception as e:
            logger.debug(f"Error al verificar paquetes instalados en Argos: {e}")

        return False

    def verify_language(
        self,
        source_lang: str,
        target_lang: str,
        is_online: bool = True,
        **kwargs: Any,
    ) -> bool:
        """
        Verifica si el par de idiomas está instalado localmente en 'languages/argos'
        o si existe conexión a Internet para descargarlo e instalarlo.
        """
        if not self._available:
            return False
        if self.is_pair_installed(source_lang, target_lang):
            return True
        return is_online

    def _ensure_packages(self, source_lang: str, target_lang: str) -> None:
        """Resuelve los paquetes de idioma de Argos requeridos (directo o vía pivote) o los descarga si están ausentes."""
        src_primary = _get_primary_lang_code(source_lang)
        tgt_primary = _get_primary_lang_code(target_lang)

        if src_primary == tgt_primary or self.is_pair_installed(source_lang, target_lang):
            return

        if self.status_callback:
            self.status_callback(
                t18n("i18n_ui.msg_status_updating_packages", "Actualizando índice de paquetes de traducción..."),
                0.10,
            )
        logger.info(f"Actualizando índice de paquetes Argos para ({src_primary} -> {tgt_primary})...")
        try:
            self._argos_pkg.update_package_index()
            available_packages = self._argos_pkg.get_available_packages()
        except Exception as exc:
            raise RuntimeError(f"No se pudo consultar el repositorio de paquetes Argos: {exc}")

        avail_map = {(p.from_code, p.to_code): p for p in available_packages}
        installed_packages = self._argos_pkg.get_installed_packages()
        installed_pairs = {(p.from_code, p.to_code) for p in installed_packages}

        # 1. Comprobar si existe paquete directo
        if (src_primary, tgt_primary) in avail_map:
            pkg_obj = avail_map[(src_primary, tgt_primary)]
            logger.info(f"Descargando e instalando paquete Argos directo ({src_primary} -> {tgt_primary}) en {self.models_dir}...")
            pair_label = f"{src_primary} -> {tgt_primary}"
            if self.status_callback:
                self.status_callback(
                    t18n("i18n_ui.msg_status_downloading_package", "Descargando paquete de idioma ({pair})...", pair=pair_label),
                    0.20,
                )
            downloaded = pkg_obj.download()
            if self.status_callback:
                self.status_callback(
                    t18n("i18n_ui.msg_status_installing_package", "Instalando paquete de idioma..."),
                    0.35,
                )
            self._argos_pkg.install_from_path(downloaded)
            return

        # 2. Comprobar si es posible resolver mediante pivote en inglés ('en')
        need_src_en = (src_primary != "en") and ((src_primary, "en") not in installed_pairs)
        need_en_tgt = (tgt_primary != "en") and (("en", tgt_primary) not in installed_pairs)

        can_src_en = (src_primary == "en") or ((src_primary, "en") in installed_pairs) or ((src_primary, "en") in avail_map)
        can_en_tgt = (tgt_primary == "en") or (("en", tgt_primary) in installed_pairs) or (("en", tgt_primary) in avail_map)

        if can_src_en and can_en_tgt:
            if need_src_en:
                pkg_src = avail_map[(src_primary, "en")]
                logger.info(f"Descargando e instalando paquete pivote Argos ({src_primary} -> en) en {self.models_dir}...")
                pair_src = f"{src_primary} -> en"
                if self.status_callback:
                    self.status_callback(
                        t18n("i18n_ui.msg_status_downloading_package", "Descargando paquete de idioma ({pair})...", pair=pair_src),
                        0.15,
                    )
                downloaded_src = pkg_src.download()
                if self.status_callback:
                    self.status_callback(
                        t18n("i18n_ui.msg_status_installing_package", "Instalando paquete de idioma..."),
                        0.25,
                    )
                self._argos_pkg.install_from_path(downloaded_src)
            if need_en_tgt:
                pkg_tgt = avail_map[("en", tgt_primary)]
                logger.info(f"Descargando e instalando paquete pivote Argos (en -> {tgt_primary}) en {self.models_dir}...")
                pair_tgt = f"en -> {tgt_primary}"
                if self.status_callback:
                    self.status_callback(
                        t18n("i18n_ui.msg_status_downloading_package", "Descargando paquete de idioma ({pair})...", pair=pair_tgt),
                        0.30,
                    )
                downloaded_tgt = pkg_tgt.download()
                if self.status_callback:
                    self.status_callback(
                        t18n("i18n_ui.msg_status_installing_package", "Instalando paquete de idioma..."),
                        0.38,
                    )
                self._argos_pkg.install_from_path(downloaded_tgt)
            return

        raise RuntimeError(f"No se encontró ni pudo instalar el paquete de traducción Argos ({source_lang} -> {target_lang})")

    def _get_translator_for_pkg(self, pkg) -> Any:
        """Obtiene una instancia cacheada del motor CTranslate2 para el paquete de idioma."""
        model_path = str(pkg.package_path / "model")
        if model_path not in self._translators:
            if self.status_callback:
                self.status_callback(
                    t18n("i18n_ui.msg_status_loading_model", "Cargando modelo de traducción..."),
                    0.40,
                )
            self._translators[model_path] = self._ctranslate2.Translator(model_path)
        return self._translators[model_path]

    def _translate_single_pkg(self, pkg: Any, text: str, translator: Any) -> str:
        """Ejecuta la traducción CTranslate2 nativa para un solo paquete sin dependencias externas."""
        tokens = pkg.tokenizer.encode(text)
        translated_batches = translator.translate_batch(
            [tokens],
            beam_size=4,
            num_hypotheses=1,
            length_penalty=0.2,
        )
        if translated_batches and translated_batches[0].hypotheses:
            best_tokens = translated_batches[0].hypotheses[0]
            decoded_str = pkg.tokenizer.decode(best_tokens)
            if pkg.target_prefix and decoded_str.startswith(pkg.target_prefix):
                decoded_str = decoded_str[len(pkg.target_prefix):]
            if decoded_str.startswith(" "):
                decoded_str = decoded_str[1:]
            return decoded_str
        return text

    def _resolve_package_pipeline(self, source_lang: str, target_lang: str) -> List[Any]:
        """
        Retorna la lista ordenada de paquetes [pkg] (directo) o [pkg1, pkg2] (pivote)
        requeridos para la traducción.
        """
        src_primary = _get_primary_lang_code(source_lang)
        tgt_primary = _get_primary_lang_code(target_lang)

        installed_packages = self._argos_pkg.get_installed_packages()
        pkg_direct = next(
            (p for p in installed_packages if p.from_code in (source_lang, src_primary) and p.to_code in (target_lang, tgt_primary)),
            None
        )
        if pkg_direct:
            return [pkg_direct]

        pkg_src_en = next(
            (p for p in installed_packages if p.from_code in (source_lang, src_primary) and p.to_code == "en"),
            None
        )
        pkg_en_tgt = next(
            (p for p in installed_packages if p.from_code == "en" and p.to_code in (target_lang, tgt_primary)),
            None
        )
        if pkg_src_en and pkg_en_tgt:
            return [pkg_src_en, pkg_en_tgt]

        # Si falta alguno, asegurar descarga
        self._ensure_packages(source_lang, target_lang)

        installed_packages = self._argos_pkg.get_installed_packages()
        pkg_direct = next(
            (p for p in installed_packages if p.from_code in (source_lang, src_primary) and p.to_code in (target_lang, tgt_primary)),
            None
        )
        if pkg_direct:
            return [pkg_direct]

        pkg_src_en = next(
            (p for p in installed_packages if p.from_code in (source_lang, src_primary) and p.to_code == "en"),
            None
        )
        pkg_en_tgt = next(
            (p for p in installed_packages if p.from_code == "en" and p.to_code in (target_lang, tgt_primary)),
            None
        )
        if pkg_src_en and pkg_en_tgt:
            return [pkg_src_en, pkg_en_tgt]

        raise RuntimeError(f"No se encontró ni pudo instalar el paquete de traducción Argos ({source_lang} -> {target_lang})")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text

        if not self._available:
            raise RuntimeError("`argostranslate` no está disponible en la instalación de Python.")

        # Proteger variables y formatos si text contiene marcadores
        masked_text, mapping = PlaceholderMasker.mask(text)

        pkgs = self._resolve_package_pipeline(source_lang, target_lang)
        curr_text = masked_text
        for pkg in pkgs:
            tr = self._get_translator_for_pkg(pkg)
            curr_text = self._translate_single_pkg(pkg, curr_text, tr)

        if mapping:
            curr_text = PlaceholderMasker.unmask(curr_text, mapping)

        return curr_text


def _resolve_auto_engine(**kwargs) -> BaseTranslator:
    """Resuelve dinámicamente el mejor motor disponible para el modo 'auto'."""
    google = GoogleTranslatorEngine(warn_if_missing=False)
    if google.is_available:
        return google
    argos = ArgosTranslatorEngine(warn_if_missing=False, **kwargs)
    if argos.is_available:
        return argos
    if getattr(sys, "frozen", False):
        logger.warning(
            "Motores de traducción (`deep-translator` / `argostranslate`) no incluidos en el ejecutable. "
            "Usando MockTranslator."
        )
    else:
        logger.info("Motores externos no instalados (`deep-translator` / `argostranslate`). Usando MockTranslator.")
    return MockTranslator()


def _resolve_specific_engine(engine_name: str, engine_cls, **kwargs) -> BaseTranslator:
    """Instancia un motor específico emitiendo advertencia y fallback a Mock si no está disponible."""
    inst = engine_cls(warn_if_missing=False, **kwargs)
    if hasattr(inst, "is_available") and not inst.is_available:
        logger.warning(f"Motor '{engine_name}' no disponible, usando MockTranslator.")
        return MockTranslator()
    return inst


ENGINE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "auto": {
        "ui_key": "i18n_ui.engine_opt_auto",
        "ui_default": "Auto",
        "factory": lambda **kwargs: _resolve_auto_engine(**kwargs),
        "is_selectable_in_ui": True,
        "check_internet": False,
        "verify_language": "verify_auto_language",
        "type_verify_language": "routine",
        "format_display": lambda label: f"{label} ({getattr(_resolve_auto_engine(), 'engine_id', 'mock')})",
        "compacta_cadenas": {
            "delimiter": "\n\n[#=$=%]\n\n",
            "max_chars": 3000,
            "max_items": 20,
        },
    },
    "google": {
        "ui_key": "i18n_ui.engine_opt_online",
        "ui_default": "Con Internet (Google)",
        "factory": lambda **kwargs: _resolve_specific_engine("google", GoogleTranslatorEngine),
        "is_selectable_in_ui": True,
        "check_internet": True,
        "verify_language": "verify_language",
        "type_verify_language": "method",
        "format_display": lambda label: f"{label}",
        "compacta_cadenas": {
            "delimiter": "\n\n[#=$=%]\n\n",
            "max_chars": 3000,
            "max_items": 20,
        },
    },
    "argos": {
        "ui_key": "i18n_ui.engine_opt_offline",
        "ui_default": "Sin Internet (Argos)",
        "factory": lambda **kwargs: _resolve_specific_engine("argos", ArgosTranslatorEngine, **kwargs),
        "is_selectable_in_ui": True,
        "check_internet": False,
        "verify_language": "verify_language",
        "type_verify_language": "method",
        "format_display": lambda label: f"{label}",
        "compacta_cadenas": {
            "delimiter": None,
            "max_chars": None,
            "max_items": 1,
        },
    },
    "none": {
        "ui_key": "i18n_ui.engine_opt_none",
        "ui_default": "Ninguno (Solo copiar)",
        "factory": lambda **kwargs: NoneTranslator(),
        "is_selectable_in_ui": True,
        "check_internet": False,
        "verify_language": None,
        "type_verify_language": None,
        "format_display": lambda label: label,
        "compacta_cadenas": {
            "delimiter": None,
            "max_chars": None,
            "max_items": 1,
        },
    },
    "mock": {
        "ui_key": None,
        "ui_default": "Mock",
        "factory": lambda **kwargs: MockTranslator(),
        "is_selectable_in_ui": False,
        "check_internet": False,
        "verify_language": None,
        "type_verify_language": None,
        "format_display": lambda label: f"{label}",
        "compacta_cadenas": {
            "delimiter": None,
            "max_chars": None,
            "max_items": 1,
        },
    },
}


def verify_auto_language(
    source_lang: str,
    target_lang: str,
    is_online: bool,
    target_dir: Optional[Union[str, Path]] = None,
    models_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> bool:
    """
    Evalúa si alguno de los motores seleccionables en la interfaz es viable
    para el par de idiomas solicitado.
    """
    for code, meta in ENGINE_REGISTRY.items():
        if code == "auto" or not meta.get("is_selectable_in_ui", False):
            continue
        if is_engine_available_in_ui(
            code, source_lang, target_lang, is_online, target_dir=target_dir, models_dir=models_dir, **kwargs
        ):
            return True
    return False


def get_engine_display_name(engine_code: str, display_label: str) -> str:
    """
    Retorna la representación de visualización formateada para el motor indicado
    según la definición declarativa en ENGINE_REGISTRY.
    """
    entry = ENGINE_REGISTRY.get((engine_code or "").strip().lower())
    if entry and "format_display" in entry:
        return entry["format_display"](display_label)
    return display_label


def is_engine_available_in_ui(
    engine_code: str,
    source_lang: str,
    target_lang: str,
    is_online: bool,
    target_dir: Optional[Union[str, Path]] = None,
    models_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> bool:
    """
    Evalúa deterministamente si un motor de traducción es viable para ser ofrecido
    en la interfaz de usuario en base a las reglas declarativas de ENGINE_REGISTRY.

    Args:
        engine_code: Código identificador del motor ('google', 'argos', 'auto', etc.).
        source_lang: Código del idioma origen.
        target_lang: Código del idioma destino.
        is_online: Si existe conexión activa a Internet.
        target_dir: Directorio destino general de idiomas (ej. 'languages').
        models_dir: Directorio local explícito para modelos dedicados.

    Returns:
        bool: True si el motor puede procesar el par de idiomas en las condiciones actuales.
    """
    code_lower = (engine_code or "").strip().lower()
    entry = ENGINE_REGISTRY.get(code_lower)
    if not entry or not entry.get("is_selectable_in_ui", False):
        return False

    if entry.get("check_internet", False) and not is_online:
        return False

    vtype = entry.get("type_verify_language")
    verify_spec = entry.get("verify_language")

    if not vtype or not verify_spec:
        return True

    engine_kwargs = dict(kwargs)
    if target_dir is not None:
        engine_kwargs["target_dir"] = target_dir
    if models_dir is not None:
        engine_kwargs["models_dir"] = models_dir

    if vtype == "method":
        inst = entry["factory"](**engine_kwargs)
        method = getattr(inst, verify_spec)
        return bool(method(source_lang, target_lang, is_online=is_online, **engine_kwargs))

    if vtype == "routine":
        fn = globals()[verify_spec] if isinstance(verify_spec, str) else verify_spec
        return bool(fn(source_lang, target_lang, is_online=is_online, **engine_kwargs))

    return False


def get_translator(engine: str = "auto", **kwargs) -> BaseTranslator:
    """
    Factory declarativo para obtener la instancia del motor de traducción.

    Args:
        engine: 'auto', 'none', 'google', 'argos', o 'mock'.
        **kwargs: Parámetros opcionales de configuración para los motores (ej. models_dir).

    Returns:
        BaseTranslator: Instancia del motor seleccionado.
    """
    engine_lower = (engine or "auto").strip().lower()
    entry = ENGINE_REGISTRY.get(engine_lower)
    if entry:
        return entry["factory"](**kwargs)

    valid_engines = ", ".join(f"'{k}'" for k in ENGINE_REGISTRY.keys())
    logger.warning(
        f"Motor de traducción no reconocido: '{engine}'. Opciones válidas: {valid_engines}. Usando mock."
    )
    return MockTranslator()
