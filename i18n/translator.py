# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: i18n/translator.py

"""
Módulo de Traducción y Enmascarado de Elementos Especiales para i18n.
Soporta enmascarado de variables, HTML, saltos de línea y URLs, así como
motores de traducción modulares: MockTranslator, GoogleTranslator (deep-translator) y ArgosTranslator.
Soporta códigos regionalizados (ej. pt-BR, es-VE), callback de progreso y detector de alucinaciones.
"""
import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Any, Callable

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

class BaseTranslator(ABC):
    """
    Interfaz base abstracta para los motores de traducción.
    """

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
        Traduce una lista de cadenas de texto notificando el progreso.
        """
        results: List[str] = []
        total = len(texts)
        #print("translator.translate_batch ORIGINAL:", texts)
        for i, t in enumerate(texts):
            if progress_callback:
                try:
                    progress_callback(i + 1, total, t)
                except Exception as cb_err:
                    logger.warning(f"Error en progress_callback: {cb_err}")

            if not t or not t.strip():
                results.append(t)
            else:
                results.append(self.translate(t, source_lang, target_lang))
        #print("translator.translate_batch TRADUCIDO:", results)
        return results

class MockTranslator(BaseTranslator):
    """
    Motor de traducción ficticio (Mock) para pruebas unitarias e integración sin red ni modelos.
    """
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text
        masked, tokens = PlaceholderMasker.mask(text)
        translated_masked = f"[{target_lang.upper()}] {masked}"
        return PlaceholderMasker.unmask(translated_masked, tokens, text)

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        results: List[str] = []
        total = len(texts)
        for i, t in enumerate(texts):
            if progress_callback:
                try:
                    progress_callback(i + 1, total, t)
                except Exception:
                    pass
            results.append(self.translate(t, source_lang, target_lang))
        return results

class GoogleTranslatorEngine(BaseTranslator):
    """
    Motor de traducción que utiliza la librería `deep-translator` (Google Translate Backend gratis).
    Soporta códigos de idiomas regionalizados como pt-BR, zh-CN, es-VE.
    """

    def __init__(self):
        try:
            from deep_translator import GoogleTranslator as DeepGoogleTranslator
            self._backend_cls = DeepGoogleTranslator
            self._available = True
        except ImportError:
            self._available = False
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

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text

        if not self._available:
            raise RuntimeError("`deep-translator` no está disponible en la instalación de Python.")

        masked, tokens = PlaceholderMasker.mask(text)
        translator = self._get_translator_instance(source_lang, target_lang)
        translated_masked = translator.translate(masked)

        # Si el motor alucina o corrompe, retornar texto original
        if PlaceholderMasker.is_hallucinated(translated_masked, text):
            logger.error(f"GoogleTranslatorEngine alucinación detectada en '{text[:20]}...'. Usando texto original.")
            return text

        return PlaceholderMasker.unmask(translated_masked, tokens, text)

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        if not texts:
            return []
        if not self._available:
            raise RuntimeError("`deep-translator` no está disponible.")

        results: List[str] = []
        total = len(texts)
        translator = self._get_translator_instance(source_lang, target_lang)

        for i, text in enumerate(texts):
            if progress_callback:
                try:
                    progress_callback(i + 1, total, text)
                except Exception as cb_err:
                    logger.warning(f"Error en progress_callback: {cb_err}")

            if not text or not text.strip():
                results.append(text)
                continue

            masked, tokens = PlaceholderMasker.mask(text)
            try:
                translated_masked = translator.translate(masked)
                if PlaceholderMasker.is_hallucinated(translated_masked, text):
                    results.append(text)
                else:
                    results.append(PlaceholderMasker.unmask(translated_masked, tokens, text))
            except Exception as e:
                try:
                    primary_tgt = _get_primary_lang_code(target_lang)
                    fallback_tr = self._backend_cls(source=_get_primary_lang_code(source_lang), target=primary_tgt)
                    translated_masked = fallback_tr.translate(masked)
                    if PlaceholderMasker.is_hallucinated(translated_masked, text):
                        results.append(text)
                    else:
                        results.append(PlaceholderMasker.unmask(translated_masked, tokens, text))
                except Exception as inner_e:
                    logger.error(f"Error al traducir '{text[:20]}...': {inner_e}")
                    results.append(text)

        return results

class ArgosTranslatorEngine(BaseTranslator):
    """
    Motor de traducción 100% offline utilizando `argostranslate`.
    Soporta fallback de idiomas regionalizados al código primario (ej. pt-BR -> pt).
    """

    def __init__(self):
        try:
            import argostranslate.package
            import argostranslate.translate
            self._argos_pkg = argostranslate.package
            self._argos_tr = argostranslate.translate
            self._available = True
        except ImportError:
            self._available = False
            logger.warning("`argostranslate` no está instalado. Instálalo con `pip install argostranslate`.")

    @property
    def is_available(self) -> bool:
        return self._available

    def _ensure_language_installed(self, source_lang: str, target_lang: str):
        src_primary = _get_primary_lang_code(source_lang)
        tgt_primary = _get_primary_lang_code(target_lang)

        installed_languages = self._argos_tr.get_installed_languages()
        from_lang = next((lang for lang in installed_languages if lang.code in (source_lang, src_primary)), None)
        to_lang = next((lang for lang in installed_languages if lang.code in (target_lang, tgt_primary)), None)

        if from_lang and to_lang and from_lang.get_translation(to_lang):
            return from_lang.get_translation(to_lang)

        logger.info(f"Instalando paquete de idioma ArgosTranslate ({src_primary} -> {tgt_primary})...")
        self._argos_pkg.update_package_index()
        available_packages = self._argos_pkg.get_available_packages()
        package_to_install = next(
            (pkg for pkg in available_packages if pkg.from_code in (source_lang, src_primary) and pkg.to_code in (target_lang, tgt_primary)),
            None
        )
        if package_to_install:
            self._argos_pkg.install_from_path(package_to_install.download())
            installed_languages = self._argos_tr.get_installed_languages()
            from_lang = next((lang for lang in installed_languages if lang.code in (source_lang, src_primary)), None)
            to_lang = next((lang for lang in installed_languages if lang.code in (target_lang, tgt_primary)), None)
            if from_lang and to_lang:
                return from_lang.get_translation(to_lang)

        raise RuntimeError(f"No se encontró ni pudo instalar el paquete de traducción Argos ({source_lang} -> {target_lang})")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return text

        if not self._available:
            raise RuntimeError("`argostranslate` no está disponible en la instalación de Python.")

        translation = self._ensure_language_installed(source_lang, target_lang)
        masked, tokens = PlaceholderMasker.mask(text)
        translated_masked = translation.translate(masked)

        # Si el motor alucina o corrompe (bucles en OpenNMT), retornar texto original
        if PlaceholderMasker.is_hallucinated(translated_masked, text):
            logger.error(f"ArgosTranslate alucinación detectada en '{text[:20]}...'. Usando texto original.")
            return text

        return PlaceholderMasker.unmask(translated_masked, tokens, text)

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        if not texts:
            return []
        if not self._available:
            raise RuntimeError("`argostranslate` no está disponible.")

        translation = self._ensure_language_installed(source_lang, target_lang)
        results = []
        total = len(texts)
        for i, t in enumerate(texts):
            if progress_callback:
                try:
                    progress_callback(i + 1, total, t)
                except Exception:
                    pass

            if not t or not t.strip():
                results.append(t)
                continue

            masked, tokens = PlaceholderMasker.mask(t)
            try:
                translated_masked = translation.translate(masked)
                if PlaceholderMasker.is_hallucinated(translated_masked, t):
                    results.append(t)
                else:
                    results.append(PlaceholderMasker.unmask(translated_masked, tokens, t))
            except Exception as e:
                logger.error(f"Error en ArgosTranslate al traducir '{t[:20]}...': {e}")
                results.append(t)

        return results

def get_translator(engine: str = "auto") -> BaseTranslator:
    """
    Factory para obtener la instancia del motor de traducción.

    Args:
        engine: 'auto', 'google', 'argos', o 'mock'.

    Returns:
        BaseTranslator: Instancia del motor seleccionado.
    """
    engine_lower = engine.lower()

    if engine_lower == "google" or engine_lower == "auto":
        engine_obj = GoogleTranslatorEngine()
        if engine_obj.is_available:
            return engine_obj
        if engine_lower == "google":
            logger.warning("Motor 'google' no disponible, usando MockTranslator.")

    if engine_lower == "argos" or engine_lower == "auto":
        engine_obj = ArgosTranslatorEngine()
        if engine_obj.is_available:
            return engine_obj
        if engine_lower == "argos":
            logger.warning("Motor 'argos' no disponible, usando MockTranslator.")

    if engine_lower == "auto":
        logger.info("Motores externos no instalados (`deep-translator` / `argostranslate`). Usando MockTranslator.")
    elif engine_lower == "mock":
        pass
    else:
        logger.warning(f"Motor de traducción no reconocido: '{engine}'. Opciones válidas: 'auto', 'google', 'argos', 'mock'. Usando mock.")
    return MockTranslator()
