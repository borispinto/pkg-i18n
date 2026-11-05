# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: tests/test_argos_and_default.py

"""Pruebas unitarias para traducción de sección _default, soporte de pivote en Argos y validación de UI."""

import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from i18n.sync import translate_dictionary, prepare_new_language
from i18n.translator import (
    ArgosTranslatorEngine,
    GoogleTranslatorEngine,
    MockTranslator,
    get_translator,
    is_engine_available_in_ui,
)
from i18n.ui.dialog import check_internet_connection, LanguageDialog


class TestArgosAndDefault(unittest.TestCase):
    """Pruebas para sección _default, motor Argos con pivote y directivas de conectividad."""

    def test_default_section_translation(self):
        """Verifica que las claves bajo la sección canónica _default sean traducidas en translate_dictionary."""
        base_dict = {
            "_language_name": "Español",
            "_default": {
                "btn_open": "Abrir",
                "lbl_welcome": "Bienvenido"
            },
            "modulo1": {
                "action": "Guardar"
            }
        }
        res = translate_dictionary(
            base_data=base_dict,
            target_code="en",
            source_code="es",
            engine="mock"
        )
        # La sección _default debe estar traducida y no permanecer con los textos originales
        self.assertIn("_default", res)
        self.assertEqual(res["_default"]["btn_open"], "[EN] Abrir")
        self.assertEqual(res["_default"]["lbl_welcome"], "[EN] Bienvenido")
        self.assertEqual(res["modulo1"]["action"], "[EN] Guardar")
        self.assertEqual(res["_language_name"], "English")

    def test_argos_models_dir_configuration(self):
        """Verifica que ArgosTranslatorEngine configure el directorio dedicado languages/argos."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_argos = Path(tmp_dir) / "languages" / "argos"
            engine = ArgosTranslatorEngine(warn_if_missing=False, models_dir=custom_argos)
            self.assertEqual(engine.models_dir, custom_argos)
            if engine.is_available:
                self.assertTrue(custom_argos.exists())
                self.assertEqual(engine._argos_settings.package_data_dir, custom_argos)
                self.assertIn(custom_argos, engine._argos_settings.package_dirs)

    def test_argos_is_pair_installed_direct_and_pivot(self):
        """Verifica la lógica de detección de paquetes instalados directos y con pivote en inglés."""
        engine = ArgosTranslatorEngine(warn_if_missing=False)
        if not engine.is_available:
            self.skipTest("argostranslate no está disponible en este entorno.")

        # Simular paquetes instalados: 'es->en' y 'en->it' (sin par directo 'es->it')
        mock_pkg1 = MagicMock()
        mock_pkg1.from_code = "es"
        mock_pkg1.to_code = "en"

        mock_pkg2 = MagicMock()
        mock_pkg2.from_code = "en"
        mock_pkg2.to_code = "it"

        with patch.object(engine._argos_pkg, "get_installed_packages", return_value=[mock_pkg1, mock_pkg2]):
            # 1. Mismo idioma
            self.assertTrue(engine.is_pair_installed("es", "es"))
            # 2. Par directo instalado
            self.assertTrue(engine.is_pair_installed("es", "en"))
            # 3. Par por pivote ('es->en' y 'en->it')
            self.assertTrue(engine.is_pair_installed("es", "it"))
            # 4. Par ausente ('es->fr')
            self.assertFalse(engine.is_pair_installed("es", "fr"))

    def test_internet_connection_check(self):
        """Verifica que check_internet_connection retorne un booleano sin errores."""
        res = check_internet_connection(timeout=0.5)
        self.assertIsInstance(res, bool)

    def test_engine_verify_language_methods(self):
        """Verifica la implementación polimórfica del método verify_language en cada motor."""
        # 1. BaseTranslator / Mock retornan True siempre
        base = MockTranslator()
        self.assertTrue(base.verify_language("es", "it", is_online=False))

        # 2. GoogleTranslatorEngine requiere is_available e is_online
        google = GoogleTranslatorEngine(warn_if_missing=False)
        if google.is_available:
            self.assertFalse(google.verify_language("es", "it", is_online=False))
            self.assertTrue(google.verify_language("es", "it", is_online=True))

        # 3. ArgosTranslatorEngine evalúa is_pair_installed y conectividad
        argos = ArgosTranslatorEngine(warn_if_missing=False)
        if argos.is_available:
            with patch.object(argos, "is_pair_installed", return_value=True):
                self.assertTrue(argos.verify_language("es", "it", is_online=False))
            with patch.object(argos, "is_pair_installed", return_value=False):
                self.assertFalse(argos.verify_language("es", "it", is_online=False))
                self.assertTrue(argos.verify_language("es", "it", is_online=True))

    def test_verify_auto_language_routine(self):
        """Verifica la rutina verify_auto_language referenciada en ENGINE_REGISTRY."""
        from i18n.translator import verify_auto_language
        with patch("i18n.translator.is_engine_available_in_ui") as mock_avail:
            # Si al menos un motor UI está disponible -> True
            mock_avail.side_effect = lambda code, s, t, online, models_dir=None, **kwargs: code == "google"
            self.assertTrue(verify_auto_language("es", "it", is_online=True))

            # Si ningún motor UI está disponible -> False
            mock_avail.side_effect = lambda code, s, t, online, models_dir=None, **kwargs: False
            self.assertFalse(verify_auto_language("es", "it", is_online=False))

    def test_is_engine_available_in_ui_declarative(self):
        """Verifica la lógica declarativa de disponibilidad de motores según ENGINE_REGISTRY."""
        # Motor 'none' no requiere internet ni verificación de idioma
        self.assertTrue(is_engine_available_in_ui("none", "es", "it", is_online=False))
        self.assertTrue(is_engine_available_in_ui("none", "es", "it", is_online=True))

        # Motor 'google' requiere internet (check_internet: True)
        self.assertFalse(is_engine_available_in_ui("google", "es", "it", is_online=False))
        self.assertTrue(is_engine_available_in_ui("google", "es", "it", is_online=True))

        # Motor 'argos' delega en el método verify_language del motor
        with patch("i18n.translator.ArgosTranslatorEngine") as mock_engine_cls:
            mock_inst = MagicMock()
            mock_inst.is_available = True
            mock_engine_cls.return_value = mock_inst

            # Caso 1: verify_language retorna True (ej. modelo instalado)
            mock_inst.verify_language.return_value = True
            self.assertTrue(is_engine_available_in_ui("argos", "es", "it", is_online=False))

            # Caso 2: verify_language retorna False (sin modelo y sin red)
            mock_inst.verify_language.return_value = False
            self.assertFalse(is_engine_available_in_ui("argos", "es", "it", is_online=False))

            # Caso 3: verify_language retorna True con red (puede descargar)
            mock_inst.verify_language.return_value = True
            self.assertTrue(is_engine_available_in_ui("argos", "es", "it", is_online=True))

    def test_ui_dynamic_engine_options(self):
        """Verifica que LanguageDialog filtre las opciones consultando is_engine_available_in_ui."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = LanguageDialog(
                target_dir=tmp_dir,
                base_code="es"
            )
            try:
                # Caso A: is_engine_available_in_ui retorna False para 'argos'
                def fake_avail_offline(code, s, t, online, models_dir=None, **kwargs):
                    return code != "argos"

                with patch("i18n.ui.dialog.is_engine_available_in_ui", side_effect=fake_avail_offline), \
                     patch("i18n.ui.dialog.check_internet_connection", return_value=False):
                    dialog._update_engine_options("it")
                    current_options = dialog.cmb_engine.cget("values")
                    current_codes = [dialog._engine_display_to_code.get(opt) for opt in current_options]
                    self.assertNotIn("argos", current_codes)

                # Caso B: is_engine_available_in_ui retorna True para 'argos'
                def fake_avail_online(code, s, t, online, models_dir=None, **kwargs):
                    return True

                with patch("i18n.ui.dialog.is_engine_available_in_ui", side_effect=fake_avail_online), \
                     patch("i18n.ui.dialog.check_internet_connection", return_value=True):
                    dialog._update_engine_options("it")
                    current_options = dialog.cmb_engine.cget("values")
                    current_codes = [dialog._engine_display_to_code.get(opt) for opt in current_options]
                    self.assertIn("argos", current_codes)
            finally:
                dialog.close()

    def test_check_internet_connection_enabled_flag(self):
        """Verifica que check_internet_connection retorne False si enabled=False y verifique si enabled=True."""
        # Por defecto enabled=False -> False inmediato sin consultar socket
        self.assertFalse(check_internet_connection())
        self.assertFalse(check_internet_connection(enabled=False))

        # Cuando enabled=True
        with patch("socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__.return_value = MagicMock()
            from i18n.ui.dialog import _INTERNET_CACHE
            _INTERNET_CACHE["status"] = None
            _INTERNET_CACHE["timestamp"] = 0.0
            self.assertTrue(check_internet_connection(enabled=True, timeout=0.5))

    def test_ui_online_checkbox_behavior(self):
        """Verifica que el checkbox de traducción en línea inicie en False y controle la verificación."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dialog = LanguageDialog(target_dir=tmp_dir, base_code="es")
            try:
                # El checkbox debe estar inicializado en False (0)
                self.assertEqual(dialog.chk_online_var.get(), 0)

                with patch("i18n.ui.dialog.check_internet_connection") as mock_check:
                    mock_check.return_value = False
                    dialog._update_engine_options("it")
                    mock_check.assert_called_with(enabled=False)

                # Al activar el checkbox, debe pasar enabled=True
                dialog.chk_online_var.set(1)
                with patch("i18n.ui.dialog.check_internet_connection") as mock_check:
                    mock_check.return_value = True
                    dialog._on_online_toggled()
                    mock_check.assert_called_with(enabled=True)
            finally:
                dialog.close()


if __name__ == "__main__":
    unittest.main()
