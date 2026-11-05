# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/ui/dialog.py

"""
Diálogo gráfico en CustomTkinter para la preparación y traducción de idiomas en pkg-i18n.
Soporta ejecución modal subordinada (heredando tema, paleta y tipografía de la aplicación anfitriona)
y ejecución autónoma / CLI (--ui).
"""


import json
import logging
import os
import socket
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, Optional, Tuple, Union

import customtkinter as ctk

from i18n.engine import get_i18n_instance, resolve_languages_directory, t18n
from i18n.sync import prepare_new_language, KNOWN_LANG_NAMES
from i18n.translator import (
    ENGINE_REGISTRY,
    get_engine_display_name,
    get_translator,
    is_engine_available_in_ui,
)
from i18n.ui.strings import ensure_ui_translations

logger = logging.getLogger("i18n.ui")

_INTERNET_CACHE: Dict[str, Any] = {"status": None, "timestamp": 0.0}

def check_internet_connection(enabled: bool = False, timeout: float = 0.8, cache_ttl: float = 5.0) -> bool:
    """
    Verifica rápidamente la conectividad a Internet mediante intento de conexión
    socket a servidores DNS públicos conocidos (1.1.1.1 o 8.8.8.8) únicamente si enabled es True.
    Si enabled es False, retorna False inmediatamente sin realizar ninguna comprobación de red.
    Utiliza una caché temporal de corta duración para evitar bloquear la UI.
    """
    if not enabled:
        return False


    now = time.monotonic()
    if _INTERNET_CACHE["status"] is not None and (now - _INTERNET_CACHE["timestamp"]) < cache_ttl:
        return bool(_INTERNET_CACHE["status"])

    hosts = [("1.1.1.1", 53), ("8.8.8.8", 53)]
    connected = False
    for host, port in hosts:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                connected = True
                break
        except (OSError, socket.timeout):
            continue

    _INTERNET_CACHE["status"] = connected
    _INTERNET_CACHE["timestamp"] = now
    return connected


class LanguageDialog:
    """Ventana de generación de nuevos idiomas con selector dinámico de diccionario base."""

    def __init__(
        self,
        parent: Optional[Any] = None,
        target_dir: Optional[str] = None,
        base_code: Optional[str] = None,
        base_file: Optional[str] = None,
        default_dict: Optional[Dict[str, Any]] = None,
        icon_path: Optional[str] = None,
        theme: Optional[str] = None,
        appearance_mode: Optional[str] = None,
        font_family: Optional[str] = None,
        font_size: Optional[int] = None,
        fonts: Optional[Dict[str, Any]] = None,
        colors: Optional[Dict[str, Any]] = None,
        on_success: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        ensure_ui_translations()

        self.parent = parent
        self.is_standalone = parent is None
        if default_dict is None and self.is_standalone:
            from i18n.ui.strings import get_ui_default_dict
            self.default_dict = get_ui_default_dict()
        else:
            self.default_dict = default_dict
        self.base_code = base_code or get_i18n_instance().idioma_def_cod
        self.on_success_callback = on_success
        self.on_error_callback = on_error

        # Configuración de apariencia si es standalone o se especifica explícitamente
        if self.is_standalone:
            if appearance_mode:
                ctk.set_appearance_mode(appearance_mode)
            if theme:
                try:
                    ctk.set_default_color_theme(theme)
                except Exception as e:
                    logger.debug(f"No se pudo aplicar tema CustomTkinter '{theme}': {e}")

        # Creación de ventana
        if self.is_standalone:
            self.window = ctk.CTk()
        else:
            self.window = ctk.CTkToplevel(parent)

        # Resolución dinámica de fuentes y paleta (sin valores hardcodeados)
        self.ui_fonts = self._resolve_fonts(fonts, font_family, font_size)
        self.ui_colors = self._resolve_colors(colors)

        # Título y dimensiones
        title_text = t18n("i18n_ui.dialog_title", "Generador de Diccionarios")
        self.window.title(title_text)
        self.width = 540
        self.height = 470
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.resizable(False, False)

        # Icono
        if icon_path and os.path.exists(icon_path):
            try:
                self.window.iconbitmap(icon_path)
            except Exception:
                pass

        # Modalidad y centrado
        if not self.is_standalone:
            self.window.transient(parent)
            self.window.grab_set()
            self._center_over_parent()
        else:
            self._center_on_screen()

        # Rutas iniciales
        if target_dir:
            self.init_target_dir = os.path.abspath(target_dir)
        else:
            self.init_target_dir = str(resolve_languages_directory())

        self.init_base_file = os.path.abspath(base_file) if base_file else ""


        self._build_ui()

    def _resolve_fonts(
        self,
        fonts: Optional[Dict[str, Any]],
        font_family: Optional[str],
        font_size: Optional[int],
    ) -> Dict[str, ctk.CTkFont]:
        """
        Resuelve dinámicamente las fuentes de la interfaz.
        Si no se especifican familias, se omite 'family' en CTkFont para que CustomTkinter
        utilice la tipografía configurada en su tema activo sin hardcoding.
        """
        base_size = font_size if (isinstance(font_size, int) and font_size > 0) else 11
        family = font_family.strip() if (font_family and isinstance(font_family, str) and font_family.strip()) else None
        custom_fonts = fonts if isinstance(fonts, dict) else {}

        def _build(role: str, default_size: int, default_weight: str = "normal") -> ctk.CTkFont:
            if role in custom_fonts and isinstance(custom_fonts[role], ctk.CTkFont):
                return custom_fonts[role]
            if role in custom_fonts and isinstance(custom_fonts[role], (tuple, list)):
                return ctk.CTkFont(*custom_fonts[role])
            kw: Dict[str, Any] = {"size": default_size, "weight": default_weight}
            if family:
                kw["family"] = family
            return ctk.CTkFont(**kw)

        return {
            "title": _build("title", base_size + 2, "bold"),
            "label": _build("label", base_size, "bold"),
            "body": _build("body", base_size, "normal"),
            "entry": _build("entry", base_size, "normal"),
            "button": _build("button", base_size, "normal"),
            "status": _build("status", max(base_size - 1, 9), "normal"),
        }

    def _resolve_colors(self, colors: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Resuelve dinámicamente la paleta de colores para widgets específicos."""
        c = colors if isinstance(colors, dict) else {}
        return {
            "text_primary": c.get("text_primary", None),
            "text_muted": c.get("text_muted", ("gray50", "gray70")),
            "btn_accept_fg": c.get("btn_accept_fg", None),
            "btn_cancel_fg": c.get("btn_cancel_fg", None),
            "btn_browse_fg": c.get("btn_browse_fg", None),
            "progressbar_fg": c.get("progressbar_fg", None),
        }

    def _center_over_parent(self) -> None:
        """Centra la ventana respecto a la ventana padre."""
        try:
            self.parent.update_idletasks()
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            x = px + max((pw - self.width) // 2, 0)
            y = py + max((ph - self.height) // 2, 0)
            self.window.geometry(f"+{x}+{y}")
        except Exception:
            self._center_on_screen()

    def _center_on_screen(self) -> None:
        """Centra la ventana en la pantalla principal."""
        self.window.update_idletasks()
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        x = max((sw - self.width) // 2, 0)
        y = max((sh - self.height) // 2, 0)
        self.window.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        """Construye todos los elementos gráficos y selectores interactivos."""
        f_label = self.ui_fonts["label"]
        f_body = self.ui_fonts["body"]
        f_entry = self.ui_fonts["entry"]
        f_btn = self.ui_fonts["button"]
        f_status = self.ui_fonts["status"]

        container = ctk.CTkFrame(self.window, fg_color="transparent")
        container.pack(fill=tk.BOTH, expand=True, padx=22, pady=16)

        # 1. Selector de Origen de Diccionario Base
        lbl_source = ctk.CTkLabel(
            container,
            text=t18n("i18n_ui.lbl_base_source", "Origen del diccionario base:"),
            font=f_label,
        )
        lbl_source.pack(anchor="w", pady=(0, 2))

        self.opt_mem = t18n("i18n_ui.source_memory", "Diccionario en memoria (código)")
        self.opt_file = t18n("i18n_ui.source_file", "Archivo JSON base")

        self.has_memory_dict = bool(self.default_dict and isinstance(self.default_dict, dict))
        if self.init_base_file:
            initial_mode = self.opt_file
        else:
            initial_mode = self.opt_mem if self.has_memory_dict else self.opt_file

        self.source_var = tk.StringVar(value=initial_mode)
        row_source = ctk.CTkFrame(container, fg_color="transparent")
        row_source.pack(fill=tk.X, pady=(0, 8))

        self.rb_mem = ctk.CTkRadioButton(
            row_source,
            text=self.opt_mem,
            value=self.opt_mem,
            variable=self.source_var,
            command=lambda: self._on_source_mode_changed(self.source_var.get()),
            font=f_body,
        )
        self.rb_mem.pack(side=tk.LEFT, padx=(0, 20))
        if not self.has_memory_dict:
            self.rb_mem.configure(state="disabled")

        self.rb_file = ctk.CTkRadioButton(
            row_source,
            text=self.opt_file,
            value=self.opt_file,
            variable=self.source_var,
            command=lambda: self._on_source_mode_changed(self.source_var.get()),
            font=f_body,
        )
        self.rb_file.pack(side=tk.LEFT)

        # Fila selector de archivo base JSON
        self.frame_file = ctk.CTkFrame(container, fg_color="transparent")
        self.frame_file.pack(fill=tk.X, pady=(0, 8))

        self.lbl_file = ctk.CTkLabel(
            self.frame_file,
            text=t18n("i18n_ui.lbl_base_file", "Archivo JSON base de referencia:"),
            font=f_body,
        )
        self.lbl_file.pack(anchor="w", pady=(0, 2))

        box_file = ctk.CTkFrame(self.frame_file, fg_color="transparent")
        box_file.pack(fill=tk.X)

        self.entry_base_file = ctk.CTkEntry(box_file, font=f_entry, height=28)
        self.entry_base_file.insert(0, self.init_base_file)
        self.entry_base_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        browse_file_kw: Dict[str, Any] = {
            "text": t18n("i18n_ui.btn_browse", "Examinar..."),
            "width": 85,
            "height": 28,
            "font": f_btn,
            "command": self._browse_base_file,
        }
        if self.ui_colors["btn_browse_fg"]:
            browse_file_kw["fg_color"] = self.ui_colors["btn_browse_fg"]
        self.btn_browse_file = ctk.CTkButton(box_file, **browse_file_kw)
        self.btn_browse_file.pack(side=tk.RIGHT)

        # 2. Directorio Destino
        lbl_target = ctk.CTkLabel(
            container,
            text=t18n("i18n_ui.lbl_target_dir", "Directorio destino de idiomas:"),
            font=f_label,
        )
        lbl_target.pack(anchor="w", pady=(0, 2))

        box_target = ctk.CTkFrame(container, fg_color="transparent")
        box_target.pack(fill=tk.X, pady=(0, 8))

        self.entry_target_dir = ctk.CTkEntry(box_target, font=f_entry, height=28)
        self.entry_target_dir.insert(0, self.init_target_dir)
        self.entry_target_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        browse_target_kw: Dict[str, Any] = {
            "text": t18n("i18n_ui.btn_browse", "Examinar..."),
            "width": 85,
            "height": 28,
            "font": f_btn,
            "command": self._browse_target_dir,
        }
        if self.ui_colors["btn_browse_fg"]:
            browse_target_kw["fg_color"] = self.ui_colors["btn_browse_fg"]
        self.btn_browse_target = ctk.CTkButton(box_target, **browse_target_kw)
        self.btn_browse_target.pack(side=tk.RIGHT)

        # 3. Opciones de Configuración (Checkboxes en Horizontal)
        row_checkboxes = ctk.CTkFrame(container, fg_color="transparent")
        row_checkboxes.pack(fill=tk.X, pady=(0, 8))
        row_checkboxes.grid_columnconfigure(0, weight=1, uniform="subcols")
        row_checkboxes.grid_columnconfigure(1, weight=1, uniform="subcols")

        self.chk_overwrite_var = tk.IntVar(value=0)
        self.chk_overwrite = ctk.CTkCheckBox(
            row_checkboxes,
            text=t18n("i18n_ui.chk_overwrite", "Sobrescribir traducciones existentes"),
            variable=self.chk_overwrite_var,
            font=f_body,
        )
        self.chk_overwrite.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.chk_online_var = tk.IntVar(value=0)
        self.chk_online = ctk.CTkCheckBox(
            row_checkboxes,
            text=t18n("i18n_ui.chk_online_translation", "Activar traducción en línea"),
            variable=self.chk_online_var,
            command=self._on_online_toggled,
            font=f_body,
        )
        self.chk_online.grid(row=0, column=1, sticky="w")

        # 4. Selectores Alineados Horizontalmente: Idioma de Destino y Motor de Traducción
        row_options = ctk.CTkFrame(container, fg_color="transparent")
        row_options.pack(fill=tk.X, pady=(0, 8))
        row_options.grid_columnconfigure(0, weight=1, uniform="subcols")
        row_options.grid_columnconfigure(1, weight=1, uniform="subcols")

        # Columna Izquierda: Idioma
        col_lang = ctk.CTkFrame(row_options, fg_color="transparent")
        col_lang.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        lbl_target_lang = ctk.CTkLabel(
            col_lang,
            text=t18n("i18n_ui.lbl_target_lang", "Nuevo idioma a generar:"),
            font=f_label,
        )
        lbl_target_lang.pack(anchor="w", pady=(0, 2))

        self._lang_display_to_tuple: Dict[str, Tuple[str, str]] = {}
        lang_options = []
        for code, name in KNOWN_LANG_NAMES.items():
            display_label = f"{name} ({code})"
            self._lang_display_to_tuple[display_label] = (code, name)
            lang_options.append(display_label)

        self.cmb_target_lang = ctk.CTkOptionMenu(
            col_lang,
            values=lang_options,
            font=f_body,
            height=28,
            command=self._on_target_lang_changed,
        )
        default_lang = lang_options[0] if lang_options else ""
        for opt in lang_options:
            c, _ = self._lang_display_to_tuple[opt]
            if c != self.base_code:
                default_lang = opt
                break
        self.cmb_target_lang.set(default_lang)
        self.cmb_target_lang.pack(fill=tk.X)

        # Columna Derecha: Motor de Traducción
        col_engine = ctk.CTkFrame(row_options, fg_color="transparent")
        col_engine.grid(row=0, column=1, sticky="ew")

        lbl_engine = ctk.CTkLabel(
            col_engine,
            text=t18n("i18n_ui.lbl_engine", "Motor de traducción:"),
            font=f_label,
        )
        lbl_engine.pack(anchor="w", pady=(0, 2))

        # Construcción declarativa desde ENGINE_REGISTRY
        self._engine_display_to_code: Dict[str, str] = {}
        engine_options = []
        for code, meta in ENGINE_REGISTRY.items():
            if not meta.get("is_selectable_in_ui", False):
                continue
            display_label = t18n(meta["ui_key"], meta["ui_default"]) if meta.get("ui_key") else meta["ui_default"]
            self._engine_display_to_code[display_label] = code
            engine_options.append(display_label)

        self.cmb_engine = ctk.CTkOptionMenu(
            col_engine,
            values=engine_options,
            font=f_body,
            height=28,
        )
        default_label = engine_options[0] if engine_options else ""
        self.cmb_engine.set(default_label)
        self.cmb_engine.pack(fill=tk.X)

        default_target_tuple = self._lang_display_to_tuple.get(default_lang)
        if default_target_tuple:
            self._update_engine_options(default_target_tuple[0])

        # 5. Barra de Progreso y Mensaje de Estado
        status_kw: Dict[str, Any] = {
            "text": "",
            "font": f_status,
            "justify": "left",
            "anchor": "w",
        }
        if self.ui_colors["text_muted"]:
            status_kw["text_color"] = self.ui_colors["text_muted"]
        self.lbl_status = ctk.CTkLabel(container, **status_kw)
        self.lbl_status.pack(fill=tk.X, pady=(0, 4))

        prog_kw: Dict[str, Any] = {"height": 8}
        if self.ui_colors["progressbar_fg"]:
            prog_kw["progress_color"] = self.ui_colors["progressbar_fg"]
        self.progressbar = ctk.CTkProgressBar(container, **prog_kw)
        self.progressbar.set(0)
        self.progressbar.pack(fill=tk.X, pady=(0, 12))

        # 6. Botones de Acción
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill=tk.X)

        cancel_kw: Dict[str, Any] = {
            "text": t18n("i18n_ui.btn_cancel", "Cancelar"),
            "width": 90,
            "height": 30,
            "font": f_btn,
            "command": self.close,
        }
        if self.ui_colors["btn_cancel_fg"]:
            cancel_kw["fg_color"] = self.ui_colors["btn_cancel_fg"]
        self.btn_cancel = ctk.CTkButton(btn_frame, **cancel_kw)
        self.btn_cancel.pack(side=tk.RIGHT, padx=(6, 0))

        accept_kw: Dict[str, Any] = {
            "text": t18n("i18n_ui.btn_accept", "Aceptar"),
            "width": 90,
            "height": 30,
            "font": f_btn,
            "command": self._on_accept,
        }
        if self.ui_colors["btn_accept_fg"]:
            accept_kw["fg_color"] = self.ui_colors["btn_accept_fg"]
        self.btn_accept = ctk.CTkButton(btn_frame, **accept_kw)
        self.btn_accept.pack(side=tk.RIGHT)

        # Aplicar estado inicial según modo
        self._on_source_mode_changed(initial_mode)

    def _on_source_mode_changed(self, value: str) -> None:
        """Actualiza la disponibilidad de campos según la fuente seleccionada."""
        if value == self.opt_mem:
            self.entry_base_file.configure(state="disabled")
            self.btn_browse_file.configure(state="disabled")
            if self.ui_colors["text_muted"]:
                self.lbl_file.configure(text_color=self.ui_colors["text_muted"])
        else:
            self.entry_base_file.configure(state="normal")
            self.btn_browse_file.configure(state="normal")
            if self.ui_colors["text_primary"]:
                self.lbl_file.configure(text_color=self.ui_colors["text_primary"])
            else:
                self.lbl_file.configure(text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])

    def _on_target_lang_changed(self, selected_display: str) -> None:
        """Callback invocado al cambiar el idioma destino en el combobox."""
        target_tuple = self._lang_display_to_tuple.get(selected_display)
        if target_tuple:
            self._update_engine_options(target_tuple[0])

    def _on_online_toggled(self) -> None:
        """Callback invocado al activar o desactivar la traducción en línea."""
        selected_display = self.cmb_target_lang.get()
        target_tuple = self._lang_display_to_tuple.get(selected_display)
        if target_tuple:
            self._update_engine_options(target_tuple[0])

    def _update_engine_options(self, target_code: str) -> None:
        """
        Actualiza dinámicamente las opciones del selector de motores según la disponibilidad
        de modelos locales en 'languages/argos' y la conectividad a Internet para el idioma seleccionado,
        evaluando las directivas declarativas de ENGINE_REGISTRY sin ramificaciones hardcodeadas.
        """
        target_dir = self.entry_target_dir.get().strip() if hasattr(self, "entry_target_dir") else self.init_target_dir
        is_online_enabled = bool(self.chk_online_var.get() == 1) if hasattr(self, "chk_online_var") else False
        is_online = check_internet_connection(enabled=is_online_enabled)

        valid_options = []
        for code, meta in ENGINE_REGISTRY.items():
            if not meta.get("is_selectable_in_ui", False):
                continue
            if not is_engine_available_in_ui(code, self.base_code, target_code, is_online, target_dir=target_dir):
                continue
            display_label = t18n(meta["ui_key"], meta["ui_default"]) if meta.get("ui_key") else meta["ui_default"]
            self._engine_display_to_code[display_label] = code
            valid_options.append(display_label)

        curr_selection = self.cmb_engine.get()
        curr_code = self._engine_display_to_code.get(curr_selection)
        self.cmb_engine.configure(values=valid_options)

        if curr_code and not is_engine_available_in_ui(curr_code, self.base_code, target_code, is_online, target_dir=target_dir):
            fallback = next((opt for opt, c in self._engine_display_to_code.items() if c == "none"), valid_options[0] if valid_options else "")
            self.cmb_engine.set(fallback)
        elif curr_selection not in valid_options:
            self.cmb_engine.set(valid_options[0] if valid_options else "")

    def _browse_base_file(self) -> None:
        """Abre un explorador para seleccionar el archivo JSON base."""
        selected = filedialog.askopenfilename(
            parent=self.window,
            title=t18n("i18n_ui.lbl_base_file", "Seleccionar archivo JSON base"),
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if selected:
            self.entry_base_file.delete(0, tk.END)
            self.entry_base_file.insert(0, os.path.normpath(selected))

    def _browse_target_dir(self) -> None:
        """Abre un explorador para seleccionar el directorio destino."""
        selected = filedialog.askdirectory(
            parent=self.window,
            title=t18n("i18n_ui.lbl_target_dir", "Seleccionar directorio destino"),
        )
        if selected:
            self.entry_target_dir.delete(0, tk.END)
            self.entry_target_dir.insert(0, os.path.normpath(selected))
            selected_lang_str = self.cmb_target_lang.get()
            target_tuple = self._lang_display_to_tuple.get(selected_lang_str)
            if target_tuple:
                self._update_engine_options(target_tuple[0])

    def _on_accept(self) -> None:
        """Valida deterministamente los parámetros e inicia el proceso de traducción."""
        selected_lang_str = self.cmb_target_lang.get()
        if selected_lang_str not in self._lang_display_to_tuple:
            messagebox.showerror(
                t18n("i18n_ui.title_error", "Error"),
                t18n("i18n_ui.err_empty_target_lang", "Debe seleccionar un idioma válido."),
                parent=self.window,
            )
            return

        lang_code, lang_name = self._lang_display_to_tuple[selected_lang_str]
        target_dir = self.entry_target_dir.get().strip()
        engine_str = self.cmb_engine.get()
        source_mode = self.source_var.get()

        if not target_dir:
            messagebox.showerror(
                t18n("i18n_ui.title_error", "Error"),
                t18n("i18n_ui.err_empty_target_dir", "Debe especificar un directorio destino válido."),
                parent=self.window,
            )
            return

        # Cargar o resolver el diccionario base
        base_dict: Optional[Dict[str, Any]] = None
        base_file_param: Optional[str] = None
        if source_mode == self.opt_mem:
            if not self.default_dict or not isinstance(self.default_dict, dict):
                messagebox.showerror(
                    t18n("i18n_ui.title_error", "Error"),
                    t18n(
                        "i18n_ui.err_no_base_memory",
                        "No se suministró un diccionario base en memoria para la aplicación.",
                    ),
                    parent=self.window,
                )
                return
            base_dict = self.default_dict
        else:
            base_file_path = self.entry_base_file.get().strip()
            if not base_file_path or not os.path.exists(base_file_path):
                messagebox.showerror(
                    t18n("i18n_ui.title_error", "Error"),
                    t18n(
                        "i18n_ui.err_base_file_not_found",
                        "El archivo JSON base no existe o no es accesible:\n{file_path}",
                        file_path=base_file_path,
                    ),
                    parent=self.window,
                )
                return
            try:
                with open(base_file_path, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                if not isinstance(loaded_data, dict):
                    raise ValueError("El contenido raíz del JSON debe ser un diccionario.")
                base_file_param = base_file_path
            except Exception as e:
                messagebox.showerror(
                    t18n("i18n_ui.title_error", "Error"),
                    t18n(
                        "i18n_ui.err_invalid_base_json",
                        "El archivo base no contiene un JSON válido:\n{error}",
                        error=e,
                    ),
                    parent=self.window,
                )
                return

        # Resolver motor y presentación declarativamente sin condicionales
        selected_engine = self._engine_display_to_code.get(engine_str, "auto")
        engine_display = get_engine_display_name(selected_engine, engine_str)

        overwrite_val = bool(self.chk_overwrite_var.get() == 1)

        # Bloquear controles durante traducción
        self._set_controls_enabled(False)

        progress_template = t18n(
            "i18n_ui.msg_translating_progress",
            "Traduciendo {engine} ({current}/{total}): {preview}",
        )
        self.lbl_status.configure(
            text=f"{t18n('i18n_ui.msg_status_checking', 'Verificando entorno y conexión...')} ({engine_display})"
        )
        self.progressbar.set(0.05)

        def status_update_ui(message: str, progress: Optional[float] = None) -> None:
            def _update() -> None:
                self.lbl_status.configure(text=message)
                if progress is not None:
                    self.progressbar.set(progress)

            self.window.after(0, _update)

        def progress_update_ui(current: int, total: int, raw_text: str) -> None:
            def _update() -> None:
                frac = current / max(total, 1)
                scaled_prog = 0.40 + (frac * 0.55)
                self.progressbar.set(scaled_prog)
                preview = raw_text[:35] + "..." if len(raw_text) > 35 else raw_text
                self.lbl_status.configure(
                    text=progress_template.format(
                        engine=engine_display,
                        current=current,
                        total=total,
                        preview=preview,
                    )
                )

            self.window.after(0, _update)

        def worker() -> None:
            try:
                result = prepare_new_language(
                    target_code=lang_code,
                    target_name=lang_name,
                    base_code=self.base_code,
                    target_dir=target_dir,
                    default_dict=base_dict,
                    base_file=base_file_param,
                    engine=selected_engine,
                    overwrite=overwrite_val,
                    progress_callback=progress_update_ui,
                    status_callback=status_update_ui,
                )
                self.window.after(0, lambda: self._on_finish_success(result["file_path"]))
            except Exception as e:
                self.window.after(0, lambda: self._on_finish_error(e))

        threading.Thread(target=worker, daemon=True).start()

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita los controles del diálogo."""
        state = "normal" if enabled else "disabled"
        self.btn_accept.configure(state=state)
        self.btn_cancel.configure(state=state)
        self.cmb_target_lang.configure(state=state)
        self.entry_target_dir.configure(state=state)
        self.btn_browse_target.configure(state=state)
        self.cmb_engine.configure(state=state)
        self.chk_online.configure(state=state)
        self.chk_overwrite.configure(state=state)
        if enabled:
            self.rb_file.configure(state="normal")
            self.rb_mem.configure(state="normal" if self.has_memory_dict else "disabled")
            self._on_source_mode_changed(self.source_var.get())
        else:
            self.rb_mem.configure(state="disabled")
            self.rb_file.configure(state="disabled")
            self.entry_base_file.configure(state="disabled")
            self.btn_browse_file.configure(state="disabled")

    def _on_finish_success(self, file_path: str) -> None:
        """Maneja la culminación exitosa de la traducción."""
        self.progressbar.set(1.0)
        self.lbl_status.configure(text=t18n("i18n_ui.msg_status_completed", "Completado"))
        if self.on_success_callback:
            try:
                self.on_success_callback(file_path)
            except Exception as e:
                logger.error(f"Error en on_success_callback: {e}")

        messagebox.showinfo(
            t18n("i18n_ui.title_success", "Éxito"),
            t18n(
                "i18n_ui.msg_lang_created_success",
                "Archivo de idioma creado correctamente en:\n{file_path}\n\n¡Ya puedes seleccionarlo o integrarlo en tu aplicación!",
                file_path=os.path.normpath(file_path),
            ),
            parent=self.window,
        )
        self.close()

    def _on_finish_error(self, error: Exception) -> None:
        """Maneja errores durante el proceso de traducción."""
        self._set_controls_enabled(True)
        self.lbl_status.configure(text="")
        self.progressbar.set(0)
        if self.on_error_callback:
            try:
                self.on_error_callback(error)
            except Exception as e:
                logger.error(f"Error en on_error_callback: {e}")

        messagebox.showerror(
            t18n("i18n_ui.title_error", "Error"),
            t18n(
                "i18n_ui.msg_lang_created_fail",
                "No se pudo generar el archivo de idioma:\n{error}",
                error=error,
            ),
            parent=self.window,
        )

    def close(self) -> None:
        """Cierra la ventana del diálogo."""
        try:
            self.window.update_idletasks()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass



def launch_new_language_dialog(
    parent: Optional[Any] = None,
    target_dir: Optional[str] = None,
    base_code: Optional[str] = None,
    base_file: Optional[str] = None,
    default_dict: Optional[Dict[str, Any]] = None,
    icon_path: Optional[str] = None,
    theme: Optional[str] = None,
    appearance_mode: Optional[str] = None,
    font_family: Optional[str] = None,
    font_size: Optional[int] = None,
    fonts: Optional[Dict[str, Any]] = None,
    colors: Optional[Dict[str, Any]] = None,
    on_success: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> LanguageDialog:
    """
    Punto de entrada canónico para lanzar el diálogo de nuevo idioma de pkg-i18n.
    Si parent es None, ejecuta la aplicación como ventana raíz (mainloop).
    Si parent es provisto, ejecuta el diálogo como modal CTkToplevel.
    Permite a la aplicación anfitriona pasar fuentes y paleta de colores para mantener armonía visual total.
    """
    dialog = LanguageDialog(
        parent=parent,
        target_dir=target_dir,
        base_code=base_code,
        base_file=base_file,
        default_dict=default_dict,
        icon_path=icon_path,
        theme=theme,
        appearance_mode=appearance_mode,
        font_family=font_family,
        font_size=font_size,
        fonts=fonts,
        colors=colors,
        on_success=on_success,
        on_error=on_error,
    )
    if dialog.is_standalone:
        dialog.window.mainloop()
    return dialog
