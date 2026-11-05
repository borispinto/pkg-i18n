# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: tests/test_i18n.py

import unittest
import shutil
import tempfile
from pathlib import Path
import sys
import json

# Agregar carpeta raíz al path de importación
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import i18n.engine
from i18n.engine import I18nManager, t18n
from i18n.sync import prepare_new_language
from i18n.extractor import extract_base_language

DEFAULT_LANG = "es"
DEFAULT_LANG_NAME = "Español"
DEFAULT_LANG_DIC = {
    "_language_name": DEFAULT_LANG_NAME,
    "_default": {
        "btn_open": "Abrir",
        "btn_save": "Guardar"
    },
    "modulo1": {
        "sec1": {
            "valor_clave": "Valor interno ES",
            "campo_user": "Usuario base"
        }
    }
}

class TestI18nSystem(unittest.TestCase):

    def setUp(self):
        # Crear directorios temporales aislados para 'interno' y 'externo'
        self.temp_dir = tempfile.mkdtemp()
        self.internal_dir = Path(self.temp_dir) / "internal" / "Recursos" / "idiomas"
        self.external_dir = Path(self.temp_dir) / "external" / "Recursos" / "idiomas"

        self.internal_dir.mkdir(parents=True)
        self.external_dir.mkdir(parents=True)

        # 1. Crear es.json interno (base) con estructura con sección "_default"
        with open(self.internal_dir / f"{DEFAULT_LANG}.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(DEFAULT_LANG_DIC, ensure_ascii=False, indent=4))

        # 2. Crear pt.json interno
        with open(self.internal_dir / "pt.json", "w", encoding="utf-8") as f:
            f.write('''{
                "_language_name": "Português",
                "_default": {
                    "btn_open": "Abrir Ficheiro"
                },
                "modulo1": {
                    "sec1": {
                        "valor_clave": "Valor interno PT"
                    }
                }
            }''')

        # 3. Crear pt-BR.json interno
        with open(self.internal_dir / "pt-BR.json", "w", encoding="utf-8") as f:
            f.write('''{
                "_language_name": "Português (Brasil)",
                "_default": {
                    "btn_open": "Abrir Arquivo"
                }
            }''')

        self.i18n = I18nManager(
            internal_dir=str(self.internal_dir),
            external_dir=str(self.external_dir),
            default_lang="es"
        )
        i18n.engine._global_instance = self.i18n

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_default_section_and_dot_notation(self):
        """Verifica búsqueda de claves bajo la sección _default (simples o compuestas)."""
        # Búsqueda simple en sección _default
        self.assertEqual(self.i18n.t18n("btn_open", "Abrir"), "Abrir")
        self.assertEqual(self.i18n.t18n("_default.btn_open", "Abrir"), "Abrir")

        # Búsqueda en sección compuesta
        self.assertEqual(t18n("modulo1.sec1.valor_clave", "Default"), "Valor interno ES")

    def test_fallback_to_default_text(self):
        """Verifica que las claves no existentes retornen el default_text."""
        self.assertEqual(self.i18n.t18n("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(self.i18n.t18n("modulo1.sec1.inexistente", "Hola {u}", u="Carlos"), "<Hola Carlos>")

    def test_suppress_markers_fallback(self):
        """Valida el control de marcadores de fallback con suppress_markers."""
        # 1. Invocación de clave inexistente con el comportamiento por defecto (retorna <texto>)
        self.assertEqual(self.i18n.t18n("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(self.i18n.t18n("clave_inexistente", "Texto Defecto", suppress_markers=False), "<Texto Defecto>")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto", suppress_markers=False), "<Texto Defecto>")

        # 2. Invocación de clave inexistente indicando no colocar marcadores (retorna texto sin < >)
        self.assertEqual(self.i18n.t18n("clave_inexistente", "Texto Defecto", suppress_markers=True), "Texto Defecto")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto", suppress_markers=True), "Texto Defecto")
        self.assertEqual(t18n("clave_inexistente", "", suppress_markers=True), "")
        self.assertEqual(t18n("clave_inexistente", "", suppress_markers=False), "<>")

        # 3. Invocación con interpolación de variables **kwargs en combinación con la bandera
        self.assertEqual(self.i18n.t18n("modulo1.sec1.inexistente", "Hola {u}", suppress_markers=False, u="Carlos"), "<Hola Carlos>")
        self.assertEqual(self.i18n.t18n("modulo1.sec1.inexistente", "Hola {u}", suppress_markers=True, u="Carlos"), "Hola Carlos")
        self.assertEqual(t18n("clave_inexistente", "Usuario: {u}", suppress_markers=True, u="Ana"), "Usuario: Ana")
        self.assertEqual(t18n("clave_inexistente", "Usuario: {u}", suppress_markers=False, u="Ana"), "<Usuario: Ana>")

    def test_cascade_loading_regional(self):
        """Verifica cascada pt-BR hereda de pt y es."""
        self.i18n.set_language("pt-BR")

        self.assertEqual(self.i18n.t18n("btn_open", "Abrir"), "Abrir Arquivo")
        self.assertEqual(self.i18n.t18n("modulo1.sec1.valor_clave", "Default"), "Valor interno PT")
        self.assertEqual(self.i18n.t18n("modulo1.sec1.campo_user", "Default"), "Usuario base")

    def test_external_user_override(self):
        """Verifica que un archivo en el directorio externo sobreescriba al interno."""
        with open(self.external_dir / "pt-BR.json", "w", encoding="utf-8") as f:
            f.write('''{
                "_language_name": "Português do Brasil (Usuario)",
                "_default": {
                    "btn_open": "Abrir Ficheiro Modificado por Usuario"
                }
            }''')

        self.i18n.set_language("pt-BR")
        self.assertEqual(self.i18n.t18n("btn_open", "Abrir"), "Abrir Ficheiro Modificado por Usuario")

    def test_seven_layer_hierarchy(self):
        """
        Verifica la jerarquía completa de las 7 capas en orden ascendente:
        Capa 0: Código Python (register_defaults)
        Capa 1: Interno es.json (Base empaquetado)
        Capa 2: Externo es.json (Base usuario)
        Capa 3: Interno pt.json (Idioma solicitado empaquetado)
        Capa 4: Externo pt.json (Idioma solicitado usuario)
        Capa 5: Interno pt-BR.json (Regional solicitado empaquetado)
        Capa 6: Externo pt-BR.json (Regional solicitado usuario)
        """
        # Capa 0
        self.i18n.register_defaults({
            "k0": "L0", "k1": "L0", "k2": "L0", "k3": "L0", "k4": "L0", "k5": "L0", "k6": "L0"
        })

        # Capa 1: Interno es.json
        with open(self.internal_dir / "es.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k1": "L1", "k2": "L1", "k3": "L1", "k4": "L1", "k5": "L1", "k6": "L1"
                }
            }, f)

        # Capa 2: Externo es.json
        with open(self.external_dir / "es.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k2": "L2", "k3": "L2", "k4": "L2", "k5": "L2", "k6": "L2"
                }
            }, f)

        # Capa 3: Interno pt.json
        with open(self.internal_dir / "pt.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k3": "L3", "k4": "L3", "k5": "L3", "k6": "L3"
                }
            }, f)

        # Capa 4: Externo pt.json
        with open(self.external_dir / "pt.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k4": "L4", "k5": "L4", "k6": "L4"
                }
            }, f)

        # Capa 5: Interno pt-BR.json
        with open(self.internal_dir / "pt-BR.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k5": "L5", "k6": "L5"
                }
            }, f)

        # Capa 6: Externo pt-BR.json
        with open(self.external_dir / "pt-BR.json", "w", encoding="utf-8") as f:
            json.dump({
                "_default": {
                    "k6": "L6"
                }
            }, f)

        self.i18n.set_language("pt-BR")

        self.assertEqual(self.i18n.t18n("k0"), "L0")
        self.assertEqual(self.i18n.t18n("k1"), "L1")
        self.assertEqual(self.i18n.t18n("k2"), "L2")
        self.assertEqual(self.i18n.t18n("k3"), "L3")
        self.assertEqual(self.i18n.t18n("k4"), "L4")
        self.assertEqual(self.i18n.t18n("k5"), "L5")
        self.assertEqual(self.i18n.t18n("k6"), "L6")

    def test_dynamic_language_scanner(self):
        """Verifica escaneo dinámico de idiomas."""
        langs = self.i18n.get_available_languages()
        codes = [l["code"] for l in langs]
        self.assertIn(DEFAULT_LANG, codes)
        self.assertIn("pt", codes)
        self.assertIn("pt-BR", codes)

    def test_observer_callbacks(self):
        """Verifica notificación a observadores UI."""
        received = []
        def on_change(lang):
            received.append(lang)

        self.i18n.subscribe(on_change)
        self.i18n.set_language("pt")
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], "pt")

    def test_sync_tool_nested(self):
        """Verifica la herramienta de preparación de nuevo idioma."""
        res = prepare_new_language("fr", "Français", DEFAULT_LANG_DIC, base_code=DEFAULT_LANG, target_dir=str(self.internal_dir), auto_translate=False)
        self.assertEqual(res["status"], "success")

        fr_file = self.internal_dir / "fr.json"
        self.assertTrue(fr_file.exists())

        self.i18n.set_language("fr")
        self.assertEqual(self.i18n.t18n("btn_open", "Abrir"), "Abrir")

    def test_base_language_extractor_tool(self):
        """Verifica la herramienta de extracción de idioma base para desarrollo (extract_base_language)."""
        src_code_dir = Path(self.temp_dir) / "code_src"
        src_code_dir.mkdir()
        
        sample_code = src_code_dir / "sample_app.py"
        sample_code.write_text('''
            title = t18n("app_title", "Mi Aplicación")
            btn = t18n("modulo1.sec2.btn_procesar", "Procesar datos")
        ''', encoding="utf-8")

        res = extract_base_language(
            origin_dir=str(src_code_dir),
            output_dir=str(self.internal_dir),
            language_name="Español",
            target_filename="es_extracted.json"
        )
        
        self.assertEqual(res["status"], "success")
        extracted_file = self.internal_dir / "es_extracted.json"
        self.assertTrue(extracted_file.exists())

        # Probar cargar el diccionario extraído
        self.i18n.set_internal_languages_dir(str(self.internal_dir))
        self.i18n.default_lang = "es_extracted"
        self.i18n.set_language("es_extracted")
        
        self.assertEqual(self.i18n.t18n("app_title", "Default"), "Mi Aplicación")
        self.assertEqual(self.i18n.t18n("modulo1.sec2.btn_procesar", "Default"), "Procesar datos")

    def test_base_language_extractor_show_source(self):
        """Verifica extract_base_language con show_source=True y ordenamiento recursivo."""
        src_code_dir = Path(self.temp_dir) / "code_src_source"
        src_code_dir.mkdir()

        app_py = src_code_dir / "app.py"
        app_py.write_text(
            '# linea 1\nt18n("btn_save", "Guardar")\nt18n("btn_open", "Abrir")\nt18n("modulo_b.sec1.clave", "Valor B")\n',
            encoding="utf-8"
        )

        view_py = src_code_dir / "view.py"
        view_py.write_text(
            '\n\nt18n("btn_open", "Abrir")\nt18n("modulo_a.clave", "Valor A")\n',
            encoding="utf-8"
        )

        res = extract_base_language(
            origin_dir=str(src_code_dir),
            output_dir=str(self.internal_dir),
            language_name="Español",
            target_filename="es_custom.json",
            show_source=True
        )

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["show_source"])
        self.assertIn("source_file", res)

        standard_file = self.internal_dir / "es_custom.json"
        source_file = self.internal_dir / "es_custom_source.json"
        self.assertTrue(standard_file.exists())
        self.assertTrue(source_file.exists())

        # 1. Validar archivo normal (strings directos)
        with open(standard_file, "r", encoding="utf-8") as f:
            std_data = json.load(f)
        self.assertEqual(std_data["_default"]["btn_open"], "Abrir")
        self.assertEqual(std_data["_default"]["btn_save"], "Guardar")
        self.assertEqual(std_data["modulo_a"]["clave"], "Valor A")

        # 2. Validar archivo _source con metadatos
        with open(source_file, "r", encoding="utf-8") as f:
            src_data = json.load(f)

        self.assertEqual(src_data.get("_language_name"), "Español")

        origin_clean = str(src_code_dir).replace("\\", "/").rstrip("/")
        btn_open = src_data["_default"]["btn_open"]
        self.assertEqual(btn_open["valor"], "Abrir")
        self.assertIn(f"{origin_clean}/app.py", btn_open["source"])
        self.assertIn(f"{origin_clean}/view.py", btn_open["source"])
        self.assertEqual(btn_open["source"][f"{origin_clean}/app.py"], [3])
        self.assertEqual(btn_open["source"][f"{origin_clean}/view.py"], [3])

        # 3. Validar ordenamiento: _language_name primero, _default segundo, luego el resto
        all_keys = list(src_data.keys())
        self.assertEqual(all_keys, ["_language_name", "_default", "modulo_a", "modulo_b"])
        default_keys = list(src_data["_default"].keys())
        self.assertEqual(default_keys, ["btn_open", "btn_save"])

    def test_omit_empty_default_section(self):
        """Verifica que si no hay claves en _default, dicha sección se purga y no aparece en el JSON."""
        src_code_dir = Path(self.temp_dir) / "code_no_default"
        src_code_dir.mkdir()

        app_py = src_code_dir / "app.py"
        app_py.write_text(
            't18n("modulo1.sec1.clave_a", "Valor A")\nt18n("modulo2.clave_b", "Valor B")\n',
            encoding="utf-8"
        )

        res = extract_base_language(
            origin_dir=str(src_code_dir),
            output_dir=str(self.internal_dir),
            language_name="Español",
            target_filename="es_nested_only.json",
            show_source=True
        )

        self.assertEqual(res["status"], "success")
        standard_file = self.internal_dir / "es_nested_only.json"
        source_file = self.internal_dir / "es_nested_only_source.json"

        with open(standard_file, "r", encoding="utf-8") as f:
            std_data = json.load(f)

        with open(source_file, "r", encoding="utf-8") as f:
            src_data = json.load(f)

        # Validar que _default NO existe en ninguno de los dos archivos
        self.assertNotIn("_default", std_data)
        self.assertNotIn("_default", src_data)
        self.assertIn("modulo1", std_data)
        self.assertIn("modulo2", std_data)
        self.assertEqual(list(std_data.keys()), ["_language_name", "modulo1", "modulo2"])
        self.assertEqual(list(src_data.keys()), ["_language_name", "modulo1", "modulo2"])

    def test_extractor_filters_return_dict_by_i18n_function_name(self):
        """Verifica que 'return { ... }' solo se extraiga si el nombre de la función contiene 'i18n'."""
        src_code_dir = Path(self.temp_dir) / "code_return_dict"
        src_code_dir.mkdir()

        code_file = src_code_dir / "schema.py"
        code_file.write_text('''
def normalize_field_def(raw_def):
    return {
        "default": raw_def,
        "type": "str",
        "description": ""
    }

def get_i18n_dictionary():
    return {
        "btn_custom": "Texto de botón",
        "modulo.sub.clave": "Texto sub"
    }

async def async_i18n_fallback():
    return {
        "msg_ok": "Operación exitosa"
    }
''', encoding="utf-8")

        res = extract_base_language(
            origin_dir=str(src_code_dir),
            output_dir=str(self.internal_dir),
            language_name="Español",
            target_filename="es_func_filter.json",
            show_source=True
        )

        self.assertEqual(res["status"], "success")
        standard_file = self.internal_dir / "es_func_filter.json"

        with open(standard_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # "description" de normalize_field_def NO debe estar en _default ni en la raíz
        self.assertNotIn("description", data.get("_default", {}))
        self.assertNotIn("description", data)

        # Claves de funciones con 'i18n' en el nombre SÍ deben estar
        self.assertEqual(data["_default"]["btn_custom"], "Texto de botón")
        self.assertEqual(data["_default"]["msg_ok"], "Operación exitosa")
        self.assertEqual(data["modulo"]["sub"]["clave"], "Texto sub")

    def test_export_active_dictionary(self):
        """Verifica la exportación del active_dictionary a archivo JSON."""
        # 1. Exportación con nombre de archivo personalizado
        custom_export_path = Path(self.temp_dir) / "exports" / "custom_dict.json"
        exported_file = self.i18n.export_active_dictionary(custom_export_path)

        self.assertTrue(exported_file.exists())
        self.assertEqual(exported_file, custom_export_path)

        with open(exported_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Debe contener exactamente las claves aplanadas del active_dictionary
        self.assertEqual(data, self.i18n.active_dictionary)
        self.assertEqual(data.get("_default.btn_open"), "Abrir")
        self.assertEqual(data.get("modulo1.sec1.valor_clave"), "Valor interno ES")

        # 2. Exportación especificando solo el directorio (debe usar 'dictionary.json')
        export_dir = Path(self.temp_dir) / "exports_dir"
        export_dir.mkdir(parents=True, exist_ok=True)
        exported_in_dir = self.i18n.export_active_dictionary(export_dir)

        self.assertEqual(exported_in_dir, export_dir / "dictionary.json")
        self.assertTrue(exported_in_dir.exists())

        # 3. Exportación mediante función global
        global_export_path = Path(self.temp_dir) / "global_dict.json"
        from i18n import export_active_dictionary
        exported_global = export_active_dictionary(global_export_path)
        self.assertTrue(exported_global.exists())
        self.assertEqual(exported_global, global_export_path)


    def test_translator_engines_and_frozen_environment(self):
        """Verifica la inicialización de motores y la detección de entorno congelado."""
        from i18n.translator import GoogleTranslatorEngine, ArgosTranslatorEngine, get_translator

        # 1. Probar inicialización con warn_if_missing=False
        google_engine = GoogleTranslatorEngine(warn_if_missing=False)
        self.assertIsInstance(google_engine.is_available, bool)

        argos_engine = ArgosTranslatorEngine(warn_if_missing=False)
        self.assertIsInstance(argos_engine.is_available, bool)

        # 2. Probar get_translator en modo auto y mock
        auto_tr = get_translator("auto")
        self.assertIsNotNone(auto_tr)

        mock_tr = get_translator("mock")
        self.assertIsNotNone(mock_tr)

        # 3. Simular entorno congelado (sys.frozen) cuando un motor no está disponible
        saved_frozen = getattr(sys, "frozen", None)
        try:
            sys.frozen = True
            dummy_google = GoogleTranslatorEngine(warn_if_missing=False)
            dummy_google._available = False
            with self.assertRaises(RuntimeError) as ctx:
                dummy_google.translate("Hola", "es", "en")
            self.assertIn("ejecutable empaquetado", str(ctx.exception))
        finally:
            if saved_frozen is None:
                if hasattr(sys, "frozen"):
                    del sys.frozen
            else:
                sys.frozen = saved_frozen

    def test_format_partial_missing_keys(self):
        """Verifica el formateo parcial tolerante ante variables no suministradas en t18n."""
        from i18n import t18n
        # 1. Caso explícito solicitado por el usuario con clave no encontrada y suppress_markers=True
        texto_sin = t18n(
            'seccion1.clave_inexistente',
            'El usuario ({usuario}) tiene nombre {nombre}',
            suppress_markers=True,
            usuario="dayi"
        )
        self.assertEqual(texto_sin, 'El usuario (dayi) tiene nombre {nombre}')

        # 2. Con marcadores por defecto (<texto>)
        texto_con = t18n(
            'seccion1.clave_inexistente',
            'El usuario ({usuario}) tiene nombre {nombre}',
            usuario="dayi"
        )
        self.assertEqual(texto_con, '<El usuario (dayi) tiene nombre {nombre}>')

        # 3. Caso completo sin variables faltantes
        texto_ok = t18n(
            'seccion1.clave_inexistente',
            'El usuario ({usuario}) tiene nombre {nombre}',
            suppress_markers=True,
            usuario="dayi",
            nombre="Dayana"
        )
        self.assertEqual(texto_ok, 'El usuario (dayi) tiene nombre Dayana')

    def test_i18n_manager_slots(self):
        """Verifica la optimización de memoria extrema con __slots__ = True."""
        from i18n import I18nManager
        manager = I18nManager(internal_dir=str(self.internal_dir))
        self.assertFalse(hasattr(manager, "__dict__"))

    def test_o1_lookup_and_preindexed_defaults(self):
        """Verifica que las claves de _default se resuelven tanto con o sin prefijo en O(1)."""
        from i18n import I18nManager
        manager = I18nManager(internal_dir=str(self.internal_dir))
        self.assertTrue(manager.has_key("btn_open"))
        self.assertTrue(manager.has_key("_default.btn_open"))
        self.assertEqual(manager.t18n("btn_open"), "Abrir")
        self.assertEqual(manager.t18n("_default.btn_open"), "Abrir")

    def test_lazy_tool_isolation_in_subprocess(self):
        """Verifica que la importación ligera de i18n no cargue módulos pesados en memoria."""
        import subprocess
        code = (
            "import sys, i18n; "
            "assert 'deep_translator' not in sys.modules, 'deep_translator cargado indebidamente'; "
            "assert 'i18n.sync' not in sys.modules, 'i18n.sync cargado indebidamente'; "
            "assert 'i18n.extractor' not in sys.modules, 'i18n.extractor cargado indebidamente'; "
            "assert 'i18n.translator' not in sys.modules, 'i18n.translator cargado indebidamente'; "
            "# Acceso a una herramienta perezosa; "
            "masker = i18n.PlaceholderMasker; "
            "assert 'i18n.translator' in sys.modules, 'i18n.translator no se cargó on-demand'"
        )
        cmd = [sys.executable, "-c", code]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Error en test de aislamiento perezoso: {res.stderr}")

    def test_none_translator_direct_and_batch(self):
        """Verifica que NoneTranslator actúe como identidad y emita progreso."""
        from i18n import get_translator, NoneTranslator
        translator = get_translator("none")
        self.assertIsInstance(translator, NoneTranslator)

        # Prueba unitaria simple
        self.assertEqual(translator.translate("Texto de prueba", "es", "en"), "Texto de prueba")

        # Prueba por lotes con callback
        texts = ["Uno", "Dos", "Tres"]
        calls = []
        def on_prog(cur, tot, txt):
            calls.append((cur, tot, txt))

        results = translator.translate_batch(texts, "es", "fr", progress_callback=on_prog)
        self.assertEqual(results, texts)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0], (1, 3, "Uno"))
        self.assertEqual(calls[2], (3, 3, "Tres"))

    def test_prepare_new_language_none_engine_overwrite_behavior(self):
        """Verifica la generación determinista con motor 'none' y respeto de overwrite."""
        test_dict = {
            "_language_name": "Español",
            "btn_open": "Abrir",
            "btn_save": "Guardar",
            "sub": {
                "label": "Etiqueta Base"
            }
        }
        target_dir = Path(self.temp_dir) / "test_langs"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "it.json"

        # 1. Crear destino previo con traducción manual existente
        pre_existing = {
            "_language_name": "Italiano",
            "btn_open": "Apri",
            "btn_save": "Guardar"  # Igual al default, debe ser procesado
        }
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(pre_existing, f, indent=4)

        # 2. Ejecutar con overwrite=False
        res = prepare_new_language(
            target_code="it",
            target_name="Italiano",
            default_dict=test_dict,
            target_dir=str(target_dir),
            engine="none",
            overwrite=False
        )
        self.assertEqual(res["status"], "success")

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # btn_open ('Apri') debe preservarse intacto
        self.assertEqual(data["btn_open"], "Apri")
        # sub.label debe agregarse
        self.assertEqual(data["sub"]["label"], "Etiqueta Base")
        self.assertEqual(data["_language_name"], "Italiano")

        # 3. Ejecutar con overwrite=True
        res_ov = prepare_new_language(
            target_code="it",
            target_name="Italiano",
            default_dict=test_dict,
            target_dir=str(target_dir),
            engine="none",
            overwrite=True
        )
        self.assertEqual(res_ov["status"], "success")

        with open(target_file, "r", encoding="utf-8") as f:
            data_ov = json.load(f)

        # Con overwrite=True, btn_open se reemplaza con el valor base ('Abrir')
        self.assertEqual(data_ov["btn_open"], "Abrir")
        self.assertEqual(data_ov["btn_save"], "Guardar")
        self.assertEqual(data_ov["sub"]["label"], "Etiqueta Base")

    def test_prepare_new_language_exclusive_file_source(self):
        """Verifica que el modo archivo sea estrictamente determinista y fail-fast."""
        target_dir = Path(self.temp_dir) / "test_langs_file"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Archivo inexistente debe fallar de inmediato
        with self.assertRaises(FileNotFoundError):
            prepare_new_language(
                target_code="de",
                target_name="Deutsch",
                base_file=str(target_dir / "inexistente.json"),
                target_dir=str(target_dir)
            )

        # Archivo válido debe cargarse exclusivamente
        custom_base = target_dir / "custom_base.json"
        with open(custom_base, "w", encoding="utf-8") as f:
            json.dump({"_language_name": "Base", "clave_especial": "Valor Único"}, f)

        res = prepare_new_language(
            target_code="de",
            target_name="Deutsch",
            base_file=str(custom_base),
            target_dir=str(target_dir),
            engine="none"
        )
        self.assertEqual(res["status"], "success")
        with open(target_dir / "de.json", "r", encoding="utf-8") as f:
            de_data = json.load(f)
        self.assertEqual(de_data["clave_especial"], "Valor Único")
        self.assertEqual(de_data["_language_name"], "Deutsch")

    def test_engine_registry_declarative_resolution(self):
        """Verifica que ENGINE_REGISTRY contenga la definición esperada y resuelva los motores."""
        from i18n import ENGINE_REGISTRY, get_translator, NoneTranslator, MockTranslator
        self.assertIn("auto", ENGINE_REGISTRY)
        self.assertIn("google", ENGINE_REGISTRY)
        self.assertIn("argos", ENGINE_REGISTRY)
        self.assertIn("none", ENGINE_REGISTRY)
        self.assertIn("mock", ENGINE_REGISTRY)

        # Verificación de instanciación declarativa y engine_id
        none_tr = get_translator("none")
        self.assertIsInstance(none_tr, NoneTranslator)
        self.assertEqual(none_tr.engine_id, "none")

        mock_tr = get_translator("mock")
        self.assertIsInstance(mock_tr, MockTranslator)
        self.assertEqual(mock_tr.engine_id, "mock")

        # Motor desconocido debe retornar MockTranslator como fallback seguro
        self.assertIsInstance(get_translator("motor_inexistente"), MockTranslator)

        # Verificación de formateador declarativo de presentación (get_engine_display_name)
        from i18n import get_engine_display_name
        self.assertEqual(get_engine_display_name("none", "Ninguno"), "Ninguno")
        self.assertEqual(get_engine_display_name("google", "Con Internet"), "Con Internet")
        self.assertEqual(get_engine_display_name("argos", "Sin Internet"), "Sin Internet")
        self.assertTrue(get_engine_display_name("auto", "Auto").startswith("Auto ("))

    def test_compacta_and_descompacta_cadenas(self):
        """Verifica la compactación y descompactación estándar de cadenas con delimitador [#=$=%]."""
        from i18n import compacta_cadenas, descompacta_cadenas

        texts = ["Hola {nombre}", "", "Bienvenido a {app}", "   ", "Adiós"]
        config = {
            "delimiter": "\n\n[#=$=%]\n\n",
            "max_chars": 3000,
            "max_items": 10
        }

        chunks, empty_slots = compacta_cadenas(texts, config)
        self.assertEqual(len(empty_slots), 2)
        self.assertEqual(empty_slots[1], "")
        self.assertEqual(empty_slots[3], "   ")
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].is_delimited)
        self.assertEqual(len(chunks[0].items), 3)

        # Simular traducción del bloque delimitado
        translated_payload = "Hello [v0]\n\n[#=$=%]\n\nWelcome to [v0]\n\n[#=$=%]\n\nGoodbye"
        calls = []

        def on_prog(curr, tot, txt):
            calls.append((curr, tot, txt))

        results = descompacta_cadenas(
            translated_chunks=[(chunks[0], translated_payload)],
            empty_slots=empty_slots,
            total_texts=len(texts),
            progress_callback=on_prog
        )

        self.assertEqual(len(results), 5)
        self.assertEqual(results[0], "Hello {nombre}")
        self.assertEqual(results[1], "")
        self.assertEqual(results[2], "Welcome to {app}")
        self.assertEqual(results[3], "   ")
        self.assertEqual(results[4], "Goodbye")
        self.assertEqual(len(calls), 5)
        self.assertEqual(calls[-1][0], 5)

    def test_proceso_unico_pipeline_and_fallback(self):
        """Verifica el flujo integral de proceso_unico y el fallback resiliente ante delimitadores alterados."""
        from i18n import proceso_unico, MockTranslator

        # 1. Ejecución estándar con motor mock
        texts = ["Primero {v1}", "Segundo", "Tercero"]
        progress_calls = []

        def callback(curr, tot, txt):
            progress_calls.append((curr, tot, txt))

        results = proceso_unico(MockTranslator(), texts, "es", "en", progress_callback=callback)
        self.assertEqual(results, ["[EN] Primero {v1}", "[EN] Segundo", "[EN] Tercero"])
        self.assertEqual(len(progress_calls), 3)
        self.assertEqual(progress_calls[-1][0], 3)

        # 2. Resiliencia ante desincronización de delimitadores
        class MismatchDelimTranslator(MockTranslator):
            engine_id = "google"  # Usa configuración con delimitador

            def translate(self, text: str, source_lang: str, target_lang: str) -> str:
                # Retorna un texto sin delimitadores para forzar el fallback
                if "[#=$=%]" in text:
                    return "Texto corrupto sin delimitador"
                return f"[RECOVERED] {text}"

        bad_tr = MismatchDelimTranslator()
        recovered_results = proceso_unico(bad_tr, texts, "es", "en")
        self.assertEqual(len(recovered_results), 3)
        self.assertTrue(all(r.startswith("[RECOVERED]") for r in recovered_results))


if __name__ == "__main__":
    unittest.main()



