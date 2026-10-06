# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: tests/test_i18n.py

import unittest
import os
import shutil
import tempfile
from pathlib import Path
import sys
import json

# Agregar carpeta raíz al path de importación
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import i18n.engine
from i18n.engine import I18nManager, translate, t18n
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
        self.assertEqual(self.i18n.translate("btn_open", "Abrir"), "Abrir")
        self.assertEqual(self.i18n.translate("_default.btn_open", "Abrir"), "Abrir")

        # Búsqueda en sección compuesta
        self.assertEqual(t18n("modulo1.sec1.valor_clave", "Default"), "Valor interno ES")

    def test_fallback_to_default_text(self):
        """Verifica que las claves no existentes retornen el default_text."""
        self.assertEqual(self.i18n.translate("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(self.i18n.translate("modulo1.sec1.inexistente", "Hola {u}", u="Carlos"), "<Hola Carlos>")

    def test_suppress_markers_fallback(self):
        """Valida el control de marcadores de fallback con suppress_markers."""
        # 1. Invocación de clave inexistente con el comportamiento por defecto (retorna <texto>)
        self.assertEqual(self.i18n.translate("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto"), "<Texto Defecto>")
        self.assertEqual(self.i18n.translate("clave_inexistente", "Texto Defecto", suppress_markers=False), "<Texto Defecto>")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto", suppress_markers=False), "<Texto Defecto>")

        # 2. Invocación de clave inexistente indicando no colocar marcadores (retorna texto sin < >)
        self.assertEqual(self.i18n.translate("clave_inexistente", "Texto Defecto", suppress_markers=True), "Texto Defecto")
        self.assertEqual(t18n("clave_inexistente", "Texto Defecto", suppress_markers=True), "Texto Defecto")
        self.assertEqual(t18n("clave_inexistente", "", suppress_markers=True), "")
        self.assertEqual(t18n("clave_inexistente", "", suppress_markers=False), "<>")

        # 3. Invocación con interpolación de variables **kwargs en combinación con la bandera
        self.assertEqual(self.i18n.translate("modulo1.sec1.inexistente", "Hola {u}", suppress_markers=False, u="Carlos"), "<Hola Carlos>")
        self.assertEqual(self.i18n.translate("modulo1.sec1.inexistente", "Hola {u}", suppress_markers=True, u="Carlos"), "Hola Carlos")
        self.assertEqual(t18n("clave_inexistente", "Usuario: {u}", suppress_markers=True, u="Ana"), "Usuario: Ana")
        self.assertEqual(t18n("clave_inexistente", "Usuario: {u}", suppress_markers=False, u="Ana"), "<Usuario: Ana>")

    def test_cascade_loading_regional(self):
        """Verifica cascada pt-BR hereda de pt y es."""
        self.i18n.set_language("pt-BR")

        self.assertEqual(self.i18n.translate("btn_open", "Abrir"), "Abrir Arquivo")
        self.assertEqual(self.i18n.translate("modulo1.sec1.valor_clave", "Default"), "Valor interno PT")
        self.assertEqual(self.i18n.translate("modulo1.sec1.campo_user", "Default"), "Usuario base")

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
        self.assertEqual(self.i18n.translate("btn_open", "Abrir"), "Abrir Ficheiro Modificado por Usuario")

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

        self.assertEqual(self.i18n.translate("k0"), "L0")
        self.assertEqual(self.i18n.translate("k1"), "L1")
        self.assertEqual(self.i18n.translate("k2"), "L2")
        self.assertEqual(self.i18n.translate("k3"), "L3")
        self.assertEqual(self.i18n.translate("k4"), "L4")
        self.assertEqual(self.i18n.translate("k5"), "L5")
        self.assertEqual(self.i18n.translate("k6"), "L6")

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
        self.assertEqual(self.i18n.translate("btn_open", "Abrir"), "Abrir")

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
        
        self.assertEqual(self.i18n.translate("app_title", "Default"), "Mi Aplicación")
        self.assertEqual(self.i18n.translate("modulo1.sec2.btn_procesar", "Default"), "Procesar datos")

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


if __name__ == "__main__":
    unittest.main()

