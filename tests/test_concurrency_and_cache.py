# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: tests/test_concurrency_and_cache.py

import sys
import json
import shutil
import asyncio
import unittest
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from i18n import (
    I18nManager,
    t18n,
    get_i18n_instance,
    set_context_language,
    get_context_language,
    reset_context_language,
    use_language,
    clear_cache,
    register_defaults,
)


class TestConcurrencyAndCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.internal_dir = Path(self.temp_dir) / "internal"
        self.internal_dir.mkdir(parents=True, exist_ok=True)

        # Crear archivos de idiomas de prueba: es.json, pt.json, en.json, fr.json
        self.es_data = {
            "_language_name": "Español",
            "_default": {
                "btn_save": "Guardar",
                "btn_cancel": "Cancelar",
                "btn_open": "Abrir",
                "msg_welcome": "Bienvenido {usuario}"
            },
            "modulo1": {
                "sec1": {
                    "titulo": "Título en Español"
                }
            }
        }
        self.pt_data = {
            "_language_name": "Português",
            "_default": {
                "btn_save": "Salvar",
                "btn_cancel": "Cancelar",
                "btn_open": "Abrir Arquivo",
                "msg_welcome": "Bem-vindo {usuario}"
            },
            "modulo1": {
                "sec1": {
                    "titulo": "Título em Português"
                }
            }
        }
        self.en_data = {
            "_language_name": "English",
            "_default": {
                "btn_save": "Save",
                "btn_cancel": "Cancel",
                "btn_open": "Open",
                "msg_welcome": "Welcome {usuario}"
            },
            "modulo1": {
                "sec1": {
                    "titulo": "Title in English"
                }
            }
        }

        with open(self.internal_dir / "es.json", "w", encoding="utf-8") as f:
            json.dump(self.es_data, f, ensure_ascii=False)
        with open(self.internal_dir / "pt.json", "w", encoding="utf-8") as f:
            json.dump(self.pt_data, f, ensure_ascii=False)
        with open(self.internal_dir / "en.json", "w", encoding="utf-8") as f:
            json.dump(self.en_data, f, ensure_ascii=False)

        # Crear instancia I18nManager dedicada
        self.mgr = I18nManager(
            internal_dir=str(self.internal_dir),
            external_dir=str(self.internal_dir),
            default_lang="es"
        )

        # Limpiar cualquier residuo de contexto en el hilo principal
        set_context_language(None)

    def tearDown(self):
        set_context_language(None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multi_language_cache_in_memory(self):
        """Verifica que el caché almacene múltiples idiomas simultáneamente en memoria."""
        self.assertEqual(len(self.mgr._loaded_languages), 1)
        self.assertIn("es", self.mgr._loaded_languages)

        # Cargar diccionario de inglés
        en_dict = self.mgr.get_language_dict("en")
        self.assertEqual(en_dict.get("btn_open"), "Open")
        self.assertIn("en", self.mgr._loaded_languages)
        self.assertIn("es", self.mgr._loaded_languages)
        self.assertEqual(len(self.mgr._loaded_languages), 2)

        # Cargar portugués
        pt_dict = self.mgr.get_language_dict("pt")
        self.assertEqual(pt_dict.get("btn_open"), "Abrir Arquivo")
        self.assertEqual(len(self.mgr._loaded_languages), 3)

        # Verificar que el objeto en caché es reutilizado (misma referencia O(1))
        self.assertIs(self.mgr.get_language_dict("en"), en_dict)
        self.assertIs(self.mgr.get_language_dict("pt"), pt_dict)

        # Limpieza de caché
        self.mgr.clear_cache()
        self.assertEqual(len(self.mgr._loaded_languages), 0)

    def test_cache_invalidation_on_register_defaults(self):
        """Verifica que registrar defaults invalida el caché y actualiza todos los idiomas."""
        # Poblar caché de es y en
        self.assertEqual(self.mgr.t18n("btn_save", lang="es"), "Guardar")
        self.assertEqual(self.mgr.t18n("btn_save", lang="en"), "Save")
        self.assertEqual(len(self.mgr._loaded_languages), 2)

        # Clave nueva que no existe en los JSONs
        self.assertEqual(self.mgr.t18n("nueva_clave", "Defecto", lang="en"), "<Defecto>")

        # Registrar un valor por defecto en Capa 0
        self.mgr.register_defaults({"_default": {"nueva_clave": "Valor Capa 0"}})

        # Tras register_defaults, reload limpió el caché y recargó el actual
        # Ahora al consultar 'en', debe heredar el nuevo valor por defecto
        self.assertEqual(self.mgr.t18n("nueva_clave", "Defecto", lang="en"), "Valor Capa 0")

    def test_t18n_explicit_lang_parameter(self):
        """Verifica que t18n(key, default, lang=...) consulte el idioma exacto solicitado."""
        self.assertEqual(self.mgr.current_lang, "es")

        # Consultas explícitas sin alterar el idioma actual de la aplicación
        self.assertEqual(self.mgr.t18n("btn_open", lang="es"), "Abrir")
        self.assertEqual(self.mgr.t18n("btn_open", lang="pt"), "Abrir Arquivo")
        self.assertEqual(self.mgr.t18n("btn_open", lang="en"), "Open")

        # El idioma activo sigue siendo español
        self.assertEqual(self.mgr.current_lang, "es")
        self.assertEqual(self.mgr.t18n("btn_open"), "Abrir")

        # Formateo con variables e idioma explícito
        self.assertEqual(
            self.mgr.t18n("msg_welcome", lang="en", usuario="Boris"),
            "Welcome Boris"
        )
        self.assertEqual(
            self.mgr.t18n("msg_welcome", lang="pt", usuario="Boris"),
            "Bem-vindo Boris"
        )

        # Verificación con has_key
        self.assertTrue(self.mgr.has_key("btn_open", lang="en"))
        self.assertFalse(self.mgr.has_key("clave_ficticia", lang="en"))

    def test_contextvar_utilities(self):
        """Verifica las utilidades canónicas de contextvars (set, get, reset, use_language)."""
        self.assertIsNone(get_context_language())

        token = set_context_language("en")
        self.assertEqual(get_context_language(), "en")
        reset_context_language(token)
        self.assertIsNone(get_context_language())

        # Probar context manager use_language
        with use_language("pt"):
            self.assertEqual(get_context_language(), "pt")
            # Anidamiento seguro
            with use_language("en"):
                self.assertEqual(get_context_language(), "en")
            # Al salir del bloque interno se restaura "pt"
            self.assertEqual(get_context_language(), "pt")

        # Al salir del bloque externo se restaura None
        self.assertIsNone(get_context_language())

    def test_t18n_with_contextvar_resolution(self):
        """Verifica que t18n resuelva transparentemente el idioma activo en ContextVar."""
        # Configurar instancia global apuntando al directorio temporal
        global_mgr = get_i18n_instance()
        global_mgr.set_internal_languages_dir(str(self.internal_dir))
        global_mgr.set_external_languages_dir(str(self.internal_dir))
        global_mgr.set_language("es")

        # Sin contextvar activo: resuelve idioma global ("es")
        self.assertEqual(t18n("btn_open"), "Abrir")

        # Con contextvar activo ("pt")
        with use_language("pt"):
            self.assertEqual(t18n("btn_open"), "Abrir Arquivo")
            self.assertEqual(t18n("btn_save"), "Salvar")
            # Si se pasa lang explícito, éste tiene prioridad sobre el contextvar
            self.assertEqual(t18n("btn_open", lang="en"), "Open")

        # Al salir del contextvar, retorna a "es"
        self.assertEqual(t18n("btn_open"), "Abrir")

    def test_async_concurrency_stress_isolation(self):
        """
        Simula 100 peticiones asíncronas concurrentes (tipo FastAPI / ASGI).
        Cada corrutina fija su propio idioma vía ContextVar y realiza múltiples
        consultas intercaladas con esperas no bloqueantes.
        Garantiza CERO fuga de contexto o condiciones de carrera.
        """
        global_mgr = get_i18n_instance()
        global_mgr.set_internal_languages_dir(str(self.internal_dir))
        global_mgr.set_external_languages_dir(str(self.internal_dir))
        global_mgr.set_language("es")

        expected_map = {
            "es": {"btn_open": "Abrir", "btn_save": "Guardar", "welcome": "Bienvenido Pedro"},
            "pt": {"btn_open": "Abrir Arquivo", "btn_save": "Salvar", "welcome": "Bem-vindo Pedro"},
            "en": {"btn_open": "Open", "btn_save": "Save", "welcome": "Welcome Pedro"},
        }

        async def simulate_request(req_id: int, lang_code: str):
            token = set_context_language(lang_code)
            try:
                # Simular tiempo de procesamiento I/O asíncrono
                await asyncio.sleep(0.005)

                val1 = t18n("btn_open")
                self.assertEqual(
                    val1,
                    expected_map[lang_code]["btn_open"],
                    f"Req #{req_id}: Conflicto en btn_open para idioma {lang_code}"
                )

                await asyncio.sleep(0.005)

                val2 = t18n("btn_save")
                self.assertEqual(
                    val2,
                    expected_map[lang_code]["btn_save"],
                    f"Req #{req_id}: Conflicto en btn_save para idioma {lang_code}"
                )

                await asyncio.sleep(0.005)

                val3 = t18n("msg_welcome", usuario="Pedro")
                self.assertEqual(
                    val3,
                    expected_map[lang_code]["welcome"],
                    f"Req #{req_id}: Conflicto en msg_welcome para idioma {lang_code}"
                )
            finally:
                reset_context_language(token)

        async def run_stress():
            languages = ["es", "pt", "en"]
            tasks = [
                simulate_request(i, languages[i % len(languages)])
                for i in range(120)
            ]
            await asyncio.gather(*tasks)

        asyncio.run(run_stress())

    def test_multithreading_concurrency_isolation(self):
        """
        Simula 20 hilos paralelos ejecutando miles de consultas t18n.
        Garantiza que cada hilo mantiene su contexto aislado y seguro.
        """
        global_mgr = get_i18n_instance()
        global_mgr.set_internal_languages_dir(str(self.internal_dir))
        global_mgr.set_external_languages_dir(str(self.internal_dir))
        global_mgr.set_language("es")

        def worker_task(thread_id: int, lang_code: str):
            with use_language(lang_code):
                for _ in range(50):
                    if lang_code == "en":
                        self.assertEqual(t18n("btn_open"), "Open")
                        self.assertEqual(t18n("btn_save"), "Save")
                    elif lang_code == "pt":
                        self.assertEqual(t18n("btn_open"), "Abrir Arquivo")
                        self.assertEqual(t18n("btn_save"), "Salvar")
                    elif lang_code == "es":
                        self.assertEqual(t18n("btn_open"), "Abrir")
                        self.assertEqual(t18n("btn_save"), "Guardar")

        languages = ["es", "pt", "en"]
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(worker_task, i, languages[i % len(languages)])
                for i in range(30)
            ]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()

