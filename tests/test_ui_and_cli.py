# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: tests/test_ui_and_cli.py

"""Pruebas unitarias para el módulo CLI y la interfaz gráfica bajo demanda de pkg-i18n."""

import io
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import i18n
from i18n import t18n
from i18n.cli import create_parser, main
from i18n.sync import KNOWN_LANG_NAMES, prepare_new_language
from i18n.translator import ArgosTranslatorEngine
from i18n.ui.dialog import LanguageDialog
from i18n.ui.strings import DEFAULT_UI_TRANSLATIONS, ensure_ui_translations, get_ui_default_dict


class TestUiAndCli(unittest.TestCase):
    """Batería de pruebas para CLI y carga perezosa de UI."""

    def test_cli_parser_options(self):
        """Verifica que el parser de CLI contenga todos los argumentos requeridos."""
        parser = create_parser()
        args = parser.parse_args(["--ui", "--target-dir", "test_dir", "--base", "test.json", "--theme", "blue", "--appearance", "dark"])
        self.assertTrue(args.ui)
        self.assertEqual(args.target_dir, "test_dir")
        self.assertEqual(args.base, "test.json")
        self.assertEqual(args.theme, "blue")
        self.assertEqual(args.appearance, "dark")

    def test_cli_help_without_args(self):
        """Verifica que ejecutar main sin argumentos imprima la ayuda y retorne 0."""
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("Herramienta CLI del motor de internacionalización", captured_output.getvalue())

    def test_ui_lazy_loading_attribute(self):
        """Verifica que los símbolos de UI se exporten perezosamente desde i18n."""
        self.assertTrue(hasattr(i18n, "launch_new_language_dialog"))
        self.assertTrue(hasattr(i18n, "LanguageDialog"))
        self.assertIn("launch_new_language_dialog", dir(i18n))
        self.assertIn("LanguageDialog", dir(i18n))

    def test_ui_strings_registration(self):
        """Verifica que las cadenas de texto de UI se registren correctamente en t18n."""
        ensure_ui_translations()
        title = t18n("i18n_ui.dialog_title")
        self.assertEqual(title, "Generador de Diccionarios")
        cancel = t18n("i18n_ui.btn_cancel")
        self.assertEqual(cancel, "Cancelar")
        accept = t18n("i18n_ui.btn_accept")
        self.assertEqual(accept, "Aceptar")
        lbl_target = t18n("i18n_ui.lbl_target_lang")
        self.assertEqual(lbl_target, "Nuevo idioma a generar:")
        status_checking = t18n("i18n_ui.msg_status_checking")
        self.assertEqual(status_checking, "Verificando entorno y conexión...")
        status_saving = t18n("i18n_ui.msg_status_saving_file")
        self.assertEqual(status_saving, "Guardando archivo de idioma...")
        status_completed = t18n("i18n_ui.msg_status_completed")
        self.assertEqual(status_completed, "Completado")

    def test_font_and_color_resolution(self):
        """Verifica que las fuentes y colores se resuelvan dinámicamente sin valores hardcodeados."""
        import customtkinter as ctk

        root = ctk.CTk()
        root.withdraw()
        try:
            # 1. Sin especificar fuente: debe resolver usando el tema nativo
            dlg_default = LanguageDialog(parent=root)
            self.assertIn("label", dlg_default.ui_fonts)
            self.assertIn("entry", dlg_default.ui_fonts)
            self.assertIn("button", dlg_default.ui_fonts)
            dlg_default.close()

            # 2. Con font_family y paleta personalizada desde el anfitrión
            dlg_custom = LanguageDialog(parent=root, font_family="Consolas", font_size=13, colors={"btn_accept_fg": "#107c41"})
            self.assertEqual(dlg_custom.ui_fonts["label"].cget("family"), "Consolas")
            self.assertEqual(dlg_custom.ui_fonts["label"].cget("size"), 13)
            self.assertEqual(dlg_custom.ui_colors["btn_accept_fg"], "#107c41")
            dlg_custom.close()
        finally:
            root.destroy()

    def test_get_ui_default_dict(self):
        """Verifica que get_ui_default_dict construya la estructura canónica jerárquica."""
        ui_dict = get_ui_default_dict("Español")
        self.assertEqual(ui_dict["_language_name"], "Español")
        self.assertIn("i18n_ui", ui_dict)
        self.assertEqual(ui_dict["i18n_ui"]["dialog_title"], DEFAULT_UI_TRANSLATIONS["dialog_title"])

    def test_standalone_dialog_loads_default_dict(self):
        """Verifica que LanguageDialog en modo standalone cargue el diccionario propio en self.default_dict."""
        dlg = LanguageDialog(parent=None)
        dlg.window.withdraw()
        try:
            self.assertTrue(dlg.has_memory_dict)
            self.assertIsNotNone(dlg.default_dict)
            self.assertIn("i18n_ui", dlg.default_dict)
            self.assertEqual(dlg.source_var.get(), dlg.opt_mem)
            self.assertEqual(dlg.rb_mem.cget("state"), "normal")
        finally:
            dlg.close()

    def test_standalone_dialog_with_base_file_prioritizes_file_mode(self):
        """Verifica que si se pasa base_file, el modo inicial sea el archivo JSON base."""
        dlg = LanguageDialog(parent=None, base_file="fake_base.json")
        dlg.window.withdraw()
        try:
            self.assertTrue(dlg.has_memory_dict)
            self.assertEqual(dlg.source_var.get(), dlg.opt_file)
        finally:
            dlg.close()

    def test_cli_passes_default_dict_to_ui(self):
        """Verifica que i18n --ui suministre default_dict al invocar launch_new_language_dialog."""
        with patch("i18n.ui.launch_new_language_dialog") as mock_launch:
            code = main(["--ui"])
            self.assertEqual(code, 0)
            mock_launch.assert_called_once()
            call_kwargs = mock_launch.call_args[1]
            self.assertIn("default_dict", call_kwargs)
            self.assertIsNotNone(call_kwargs["default_dict"])

    def test_language_selector_populated_from_known_langs(self):
        """Verifica que el selector de idiomas en LanguageDialog se pueble desde KNOWN_LANG_NAMES."""
        dlg = LanguageDialog(parent=None)
        dlg.window.withdraw()
        try:
            self.assertTrue(hasattr(dlg, "cmb_target_lang"))
            self.assertEqual(len(dlg._lang_display_to_tuple), len(KNOWN_LANG_NAMES))
            selected = dlg.cmb_target_lang.get()
            self.assertIn(selected, dlg._lang_display_to_tuple)
            code, name = dlg._lang_display_to_tuple[selected]
            self.assertEqual(KNOWN_LANG_NAMES[code], name)
            self.assertNotEqual(code, dlg.base_code)
        finally:
            dlg.close()

    def test_status_callback_in_prepare_new_language(self):
        """Verifica que prepare_new_language emita las fases de estado canónicas."""
        tmp_dir = tempfile.mkdtemp()
        try:
            status_events = []

            def _track_status(msg: str, progress: float = None):
                status_events.append((msg, progress))

            base_dict = {"saludo": "Hola", "despedida": "Adiós"}
            prepare_new_language(
                target_code="en",
                target_name="English",
                default_dict=base_dict,
                target_dir=tmp_dir,
                engine="mock",
                status_callback=_track_status,
            )

            messages = [e[0] for e in status_events]
            progresses = [e[1] for e in status_events]

            self.assertTrue(any("Analizando" in m for m in messages))
            self.assertTrue(any("Guardando" in m for m in messages))
            self.assertTrue(any("Completado" in m for m in messages))
            self.assertIn(1.0, progresses)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_status_callback_in_argos_engine_mocked(self):
        """Verifica que ArgosTranslatorEngine emita estados al actualizar y descargar paquetes."""
        status_events = []

        def _track_status(msg: str, progress: float = None):
            status_events.append((msg, progress))

        engine = ArgosTranslatorEngine(warn_if_missing=False, status_callback=_track_status)
        if not engine.is_available:
            return

        engine.is_pair_installed = MagicMock(return_value=False)
        engine._argos_pkg.update_package_index = MagicMock()

        mock_pkg = MagicMock()
        mock_pkg.from_code = "es"
        mock_pkg.to_code = "en"
        mock_pkg.download.return_value = "/fake/path/model.argosmodel"
        engine._argos_pkg.get_available_packages.return_value = [mock_pkg]
        engine._argos_pkg.get_installed_packages.return_value = []
        engine._argos_pkg.install_from_path = MagicMock()

        engine._ensure_packages("es", "en")

        messages = [e[0] for e in status_events]
        self.assertTrue(any("Actualizando índice" in m for m in messages))
        self.assertTrue(any("Descargando paquete" in m for m in messages))
        self.assertTrue(any("Instalando paquete" in m for m in messages))


if __name__ == "__main__":
    unittest.main()
