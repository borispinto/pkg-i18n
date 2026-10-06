# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 Asisnet Computacion, CA <proyectos@asisnet.net>
# SPDX-License-Identifier: Proprietary
# Autor: Boris Pinto <borispinto@asisnet.net>
# File: i18n/extractor.py

import os
import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

from .engine import get_i18n_instance, resolve_languages_directory

logger = logging.getLogger("i18n.extractor")

def _set_nested_key(
    d: Dict[str, Any],
    key_path: str,
    value: str,
    show_source: bool = False,
    rel_path: str = "",
    lineno: int = 1
) -> None:
    """
    Inserta una clave simple o anidada en un diccionario.
    Si la clave no contiene puntos, se asigna a la sección '_default'.
    Si show_source es True, estructura el valor como:
      {"valor": value, "source": {rel_path: [lineno]}}
    """
    if key_path.startswith("_default."):
        key_path = key_path[9:]
        parts = ["_default"] + key_path.split(".")
    elif "." not in key_path:
        parts = ["_default", key_path]
    else:
        parts = key_path.split(".")

    current = d
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]

    last_part = parts[-1]

    if not show_source:
        if isinstance(current.get(last_part), dict) and "valor" in current[last_part]:
            current[last_part] = value
        else:
            current[last_part] = value
    else:
        existing = current.get(last_part)
        if isinstance(existing, dict) and "source" in existing:
            existing["valor"] = value if value else existing.get("valor", "")
            src_dict = existing.setdefault("source", {})
            if rel_path:
                lines = src_dict.setdefault(rel_path, [])
                if lineno not in lines:
                    lines.append(lineno)
                    lines.sort()
        elif isinstance(existing, str):
            src_dict = {rel_path: [lineno]} if rel_path else {}
            current[last_part] = {
                "valor": value or existing,
                "source": src_dict
            }
        else:
            src_dict = {rel_path: [lineno]} if rel_path else {}
            current[last_part] = {
                "valor": value,
                "source": src_dict
            }


def _extract_dict_pairs(dict_node: ast.Dict, prefix: str = "", default_lineno: int = 1) -> List[Tuple[str, str, int]]:
    """Extrae recursivamente pares (clave, valor, lineno) de un nodo ast.Dict."""
    pairs: List[Tuple[str, str, int]] = []
    for k_node, v_node in zip(dict_node.keys, dict_node.values):
        if k_node is not None and isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
            key_str = k_node.value
            full_key = f"{prefix}.{key_str}" if prefix else key_str
            lineno = getattr(k_node, "lineno", default_lineno)
            if isinstance(v_node, ast.Constant) and isinstance(v_node.value, str):
                pairs.append((full_key, v_node.value.strip(), lineno))
            elif isinstance(v_node, ast.Dict):
                pairs.extend(_extract_dict_pairs(v_node, full_key, lineno))
    return pairs


class _I18nASTExtractor(ast.NodeVisitor):
    """
    Recorre el AST de un archivo Python extrayendo:
    - Llamadas a funciones de traducción (ej. t18n("clave", "texto")).
    - Diccionarios en llamadas a funciones registradas (ej. t18n({"clave": "texto"})).
    - Sentencias 'return { ... }' ÚNICAMENTE si la función contiene 'i18n' en su nombre.
    """
    def __init__(self, funcs: Set[str], rel_prog: str):
        self.funcs = funcs
        self.rel_prog = rel_prog
        self.extracted_items: List[Tuple[str, str, str, int]] = []
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_fn = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_fn

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_fn = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_fn

    def visit_Call(self, node: ast.Call):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in self.funcs:
            lineno = getattr(node, "lineno", 1)
            if len(node.args) >= 2:
                arg0 = node.args[0]
                arg1 = node.args[1]
                if (isinstance(arg0, ast.Constant) and isinstance(arg0.value, str) and
                    isinstance(arg1, ast.Constant) and isinstance(arg1.value, str)):
                    self.extracted_items.append((arg0.value.strip(), arg1.value.strip(), self.rel_prog, lineno))
            elif len(node.args) >= 1 and isinstance(node.args[0], ast.Dict):
                for k, v, l in _extract_dict_pairs(node.args[0], default_lineno=lineno):
                    self.extracted_items.append((k, v, self.rel_prog, l))
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        if isinstance(node.value, ast.Dict):
            if self.current_function and "i18n" in self.current_function.lower():
                lineno = getattr(node, "lineno", 1)
                for k, v, l in _extract_dict_pairs(node.value, default_lineno=lineno):
                    self.extracted_items.append((k, v, self.rel_prog, l))
        self.generic_visit(node)


def _sort_dictionary(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ordena recursivamente todas las claves del diccionario en todos los niveles.
    Coloca primero '_language_name', luego '_default', y luego el resto de claves ordenadas alfabéticamente.
    Si un nodo es una hoja con formato {'valor': ..., 'source': ...}, mantiene 'valor' primero y 'source' ordenado.
    """
    sorted_dict: Dict[str, Any] = {}

    # 1. Cabecera _language_name primero
    if "_language_name" in d:
        sorted_dict["_language_name"] = d["_language_name"]

    # 2. _default segundo (únicamente si contiene claves)
    if "_default" in d:
        v = d["_default"]
        if isinstance(v, dict):
            sorted_v = _sort_dictionary(v)
            if sorted_v:
                sorted_dict["_default"] = sorted_v
        elif v:
            sorted_dict["_default"] = v

    # 3. Resto de claves ordenadas alfabéticamente
    for k in sorted(d.keys()):
        if k in ("_language_name", "_default"):
            continue
        v = d[k]
        if isinstance(v, dict):
            if "valor" in v and "source" in v and isinstance(v["source"], dict) and len(v) == 2:
                sorted_src = {
                    src_prog: sorted(list(set(lines)))
                    for src_prog, lines in sorted(v["source"].items())
                }
                sorted_dict[k] = {
                    "valor": v["valor"],
                    "source": sorted_src
                }
            else:
                sorted_dict[k] = _sort_dictionary(v)
        else:
            sorted_dict[k] = v

    return sorted_dict


def _should_exclude(file_path: Path, exclude_list: Optional[List[str]]) -> bool:
    """Comprueba si un archivo debe ser excluido según la lista de programas/archivos a excluir."""
    if not exclude_list:
        return False
    
    file_name = file_path.name.lower()
    file_stem = file_path.stem.lower()
    norm_file_str = str(file_path).replace("\\", "/").lower()

    for item in exclude_list:
        if not item:
            continue
        item_clean = item.strip().lower()
        item_norm = item_clean.replace("\\", "/")
        
        if file_name == item_clean or file_stem == item_clean:
            return True
        if norm_file_str.endswith(item_norm) or norm_file_str.endswith(f"/{item_norm}"):
            return True
        if item_clean in [p.lower() for p in file_path.parts]:
            return True
            
    return False


def extract_base_language(
    origin_dir: str,
    output_dir: Optional[str] = None,
    file_extensions: Optional[List[str]] = None,
    recursive: bool = True,
    function_names: Optional[List[str]] = None,
    language_name: Optional[str] = None,
    target_filename: Optional[str] = None,
    exclude_programs: Optional[List[str]] = None,
    show_source: bool = False
) -> Dict[str, Any]:
    """
    Utilidad para desarrollo que escanea el código fuente buscando llamadas a funciones
    de internacionalización y diccionarios de respaldo para generar/actualizar el archivo JSON base.

    :param origin_dir: Ruta a la carpeta o archivo de origen a escanear.
    :param output_dir: Ruta de destino para el archivo JSON (si no se indica, se usa resources/languages/).
    :param file_extensions: Extensiones de archivos a escanear (por defecto [".py"]).
    :param recursive: Si es True, busca de manera recursiva en subdirectorios.
    :param function_names: Nombres de funciones i18n a buscar.
    :param language_name: Nombre del idioma base (ej. "Español").
    :param target_filename: Nombre del archivo JSON a generar (ej. "es.json").
    :param exclude_programs: Lista de nombres de archivos/programas o rutas a excluir del escaneo.
    :param show_source: Si es True, genera adicionalmente un archivo con sufijo '_source' (ej. 'es_source.json')
                        que incluye la ubicación del programa y líneas para cada clave:
                        {"valor": "...", "source": {"programa.py": [10, 20]}}
    """
    i18n_inst = get_i18n_instance()
    if not language_name:
        language_name = i18n_inst.idioma_def_text
    if not target_filename:
        target_filename = f"{i18n_inst.idioma_def_cod}.json"
    origin_path = Path(origin_dir)
    if not origin_path.exists():
        raise FileNotFoundError(f"El origen '{origin_dir}' no existe.")

    out_path = resolve_languages_directory(output_dir, base_path=origin_path)
    out_path.mkdir(parents=True, exist_ok=True)
    target_json = out_path / target_filename

    exts = set(e.lower() if e.startswith(".") else f".{e.lower()}" for e in (file_extensions or [".py"]))
    funcs = set(function_names or ["t18n"])
    
    func_pattern = "|".join(re.escape(fn) for fn in sorted(funcs, key=len, reverse=True))
    regex = re.compile(
        rf"\b(?:{func_pattern})\s*\(\s*(['\"])([^'\"\r\n]+)\1\s*,\s*(['\"])(.*?)\3\s*\)"
    )

    extracted_items: List[Tuple[str, str, str, int]] = []
    origin_clean = str(origin_dir).replace("\\", "/").rstrip("/")

    def scan_file(file_file: Path):
        try:
            content = file_file.read_text(encoding="utf-8", errors="ignore")
            
            if origin_path.is_file():
                rel_prog = origin_clean
            else:
                try:
                    rel_in_dir = file_file.relative_to(origin_path).as_posix()
                except ValueError:
                    rel_in_dir = os.path.relpath(file_file, origin_path).replace("\\", "/")

                if origin_clean and origin_clean != ".":
                    rel_prog = f"{origin_clean}/{rel_in_dir}"
                else:
                    rel_prog = rel_in_dir

            # Para archivos Python, utilizar análisis de AST 100% preciso
            if file_file.suffix.lower() == ".py":
                try:
                    tree = ast.parse(content, filename=str(file_file))
                    visitor = _I18nASTExtractor(funcs=funcs, rel_prog=rel_prog)
                    visitor.visit(tree)
                    extracted_items.extend(visitor.extracted_items)
                    return
                except Exception as ast_err:
                    logger.debug(f"AST falló en {file_file}, usando fallback regex: {ast_err}")

            # Fallback seguro con regex delimitado por límite de palabra \b
            for m in regex.finditer(content):
                key = m.group(2).strip()
                default_text = m.group(4).strip()
                if key and default_text and not re.search(r"[\s\n\r\t]", key):
                    lineno = content[:m.start()].count("\n") + 1
                    extracted_items.append((key, default_text, rel_prog, lineno))
        except Exception as e:
            logger.warning(f"Error al escanear archivo {file_file}: {e}")

    ignored_dirs = {".venv", ".venv64", "__pycache__", ".git", ".idea", ".vscode", "build", "build64", "dist", "dist64"}

    if origin_path.is_file():
        if not _should_exclude(origin_path, exclude_programs):
            scan_file(origin_path)
    elif recursive:
        for ext in exts:
            for f in origin_path.rglob(f"*{ext}"):
                if any(part in ignored_dirs for part in f.parts):
                    continue
                if _should_exclude(f, exclude_programs):
                    continue
                scan_file(f)
    else:
        for ext in exts:
            for f in origin_path.glob(f"*{ext}"):
                if _should_exclude(f, exclude_programs):
                    continue
                scan_file(f)

    existing_data: Dict[str, Any] = {}
    if target_json.exists():
        try:
            with open(target_json, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo leer archivo JSON existente {target_json}: {e}")

    def _normalize_from_source(data: Dict[str, Any]) -> Dict[str, Any]:
        res: Dict[str, Any] = {}
        for k, v in data.items():
            if k == "_language_name":
                res[k] = v
            elif isinstance(v, dict):
                if "valor" in v and "source" in v:
                    res[k] = v["valor"]
                else:
                    res[k] = _normalize_from_source(v)
            else:
                res[k] = v
        return res

    clean_existing = _normalize_from_source(existing_data)

    final_dict: Dict[str, Any] = {
        "_language_name": language_name
    }
    for k, v in clean_existing.items():
        if k != "_language_name":
            final_dict[k] = v

    new_keys_count = 0
    for key, text, rel_prog, lineno in extracted_items:
        _set_nested_key(final_dict, key, text, show_source=False)
        new_keys_count += 1

    final_dict = _sort_dictionary(final_dict)

    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, indent=4, ensure_ascii=False)

    result_payload: Dict[str, Any] = {
        "status": "success",
        "target_file": str(target_json),
        "total_extracted": len(extracted_items),
        "unique_keys_processed": new_keys_count,
        "show_source": show_source
    }

    if show_source:
        source_filename = f"{target_json.stem}_source{target_json.suffix}"
        source_json = out_path / source_filename

        existing_source_data: Dict[str, Any] = {}
        if source_json.exists():
            try:
                with open(source_json, "r", encoding="utf-8") as f:
                    existing_source_data = json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo leer archivo JSON de fuente existente {source_json}: {e}")

        def _normalize_to_source(data: Dict[str, Any]) -> Dict[str, Any]:
            res: Dict[str, Any] = {}
            for k, v in data.items():
                if k == "_language_name":
                    res[k] = v
                elif isinstance(v, dict):
                    if "valor" in v and "source" in v:
                        res[k] = v
                    else:
                        res[k] = _normalize_to_source(v)
                elif isinstance(v, str):
                    res[k] = {"valor": v, "source": {}}
                else:
                    res[k] = v
            return res

        source_dict: Dict[str, Any] = {
            "_language_name": language_name
        }
        for k, v in _normalize_to_source(existing_source_data or existing_data).items():
            if k != "_language_name":
                source_dict[k] = v

        for key, text, rel_prog, lineno in extracted_items:
            _set_nested_key(source_dict, key, text, show_source=True, rel_path=rel_prog, lineno=lineno)

        source_dict = _sort_dictionary(source_dict)

        with open(source_json, "w", encoding="utf-8") as f:
            json.dump(source_dict, f, indent=4, ensure_ascii=False)

        result_payload["source_file"] = str(source_json)

    return result_payload
