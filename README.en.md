# 🌐 pkg-i18n

[🇪🇸 Español](README.md) | [🇺🇸 English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python Version](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://www.python.org/) [![Architecture: 7-Layer Cascade](https://img.shields.io/badge/architecture-7--layer%20cascade-orange.svg)](#️-7-layer-cascade-loading-architecture--contingency) [![Zero Runtime Dependencies](https://img.shields.io/badge/dependencies-zero%20mandatory-brightgreen.svg)](#-installation)

This package provides a comprehensive, centralized, extensible, high-performance **internationalization (i18n) and localization (l10n)** solution with zero mandatory runtime dependencies for any Python project (desktop applications such as PyQt/CustomTkinter, CLI tools, scripts, or web servers).

**pkg-i18n** is the core internationalization (i18n) and localization (l10n) infrastructure utilized by applications across the **Asisnet** suite.

--------------------------------------------------------------------------------

#### 📋 Table of Contents

1. [🎯 Why pkg-i18n? (Purpose and Motivation)](#-why-pkg-i18n-purpose-and-motivation)
2. [🚀 Key Capabilities and Features](#-key-capabilities-and-features)
3. [📦 Installation](#-installation)
4. [🏗️ 7-Layer Cascade Loading Architecture + Contingency](#️-7-layer-cascade-loading-architecture--contingency)
5. [📁 Project Structure and JSON File Format](#-project-structure-and-json-file-format)
6. [🛠️ Quick Developer Guide](#️-quick-developer-guide)
   - [1. Initialization and Basic Consumption (`t18n`)](#1-initialization-and-basic-consumption-t18n)
   - [2. Key Verification and Dictionary-Style Access](#2-key-verification-and-dictionary-style-access)
   - [3. Language Directory Customization and Resolution](#3-language-directory-customization-and-resolution)
   - [4. In-Code Base Dictionary Registration (Layer 0)](#4-in-code-base-dictionary-registration-layer-0)
   - [5. Real-Time Change Subscription (Observer Pattern)](#5-real-time-change-subscription-observer-pattern)
   - [6. Available Languages Management and Listing](#6-available-languages-management-and-listing)
   - [7. Exporting Active Dictionary (`export_active_dictionary`)](#7-exporting-active-dictionary-export_active_dictionary)
   - [8. Development Tools and Automated Translation](#8-development-tools-and-automated-translation)
   - [9. PyInstaller Bundling Support](#9-pyinstaller-bundling-support)
7. [🌐 Interoperability with Other Languages](#-interoperability-with-other-languages)
8. [👥 Contact & Support](#-contact--support)
9. [📄 License](#-license)

--------------------------------------------------------------------------------

#### 🎯 Why pkg-i18n? (Purpose and Motivation)
In enterprise and mission-critical application development, managing multilingual texts often becomes a **repetitive, disorganized, and error-prone task**:
*   **Hardcoded strings in code**: Strings embedded directly inside the GUI or business logic, hindering audits, regional adaptations, and language switches.
*   **Heavy and rigid dependencies**: Traditional tools requiring compilation of binary catalogs (.mo, .po) or binding projects to complex dependencies incompatible with lightweight or embedded environments.
*   **Runtime inconsistencies and crashes**: Lack of deterministic fallback safety nets when keys are missing from outdated catalogs, causing unhandled errors in front of the user.
*   **Machine translation corruption**: Loss of dynamic variables (`{user}`), HTML tags, or URLs when raw plain text is sent to external translation engines.
*   **Platform isolation**: Difficulty sharing a single catalog of terms between modern Python applications and enterprise systems built in other languages (such as .NET / VB.NET).

**pkg-i18n was created to decisively eliminate these problems**, providing a **turnkey, modular, resilient, and high-performance** solution:
1.  **Single-line resolution (`t18n`)**: Instant lookup with dot-notation resolution and a transparent fallback net.
2.  **Multi-layer cascade loading (7 Layers + Contingency)**: Allows overriding from in-code base dictionaries to bundled catalogs and external editable files per branch or end-user, with a contingency net ensuring zero production downtime.
3.  **Zero mandatory runtime dependencies ($O(1)$)**: Ultra-lightweight memory footprint relying exclusively on Python's standard library.
4.  **Intelligent assisted translation with safe masking**: Catalog automation protecting variables, line breaks, and HTML syntax against external alterations or hallucinations.
5.  **Open and interoperable ecosystem**: Standard JSON format ready to be consumed both in Python and in corporate solutions across other platforms.

--------------------------------------------------------------------------------

#### 🚀 Key Capabilities and Features
*   **100% Autonomous Runtime Library**: Operates strictly on Python's standard library (`json`, `re`, `logging`, `pathlib`). No third-party dependencies required in production.
*   **Ultra-Fast Hierarchical Cascade Resolution (7 Layers)**: Resolves in-memory dictionaries combining in-code registered defaults (Layer 0), bundled base files (`es.json`), regional variants (`pt-BR.json`), and customizable external layers.
*   **Runtime Contingency Safety Net**: If a key is missing across all catalog layers, `t18n(key, default_text)` formats and returns the provided default text, ensuring complete operational continuity.
*   **Direct Access with Dot Notation and `_default` Section**: Supports direct keys (e.g., `t18n("btn_open")` resolves `_default.btn_open`) and nested modular paths (e.g., `t18n("modulo1.sec1.clave")`).
*   **Safe Dynamic Parameter Formatting**: Variable injection using standard syntax (`"Welcome, {user}"`) with tolerance and protection against formatting errors.
*   **Observer Pattern for User Interfaces**: Reactive subscription via `i18n.subscribe(callback)` to dynamically refresh windows and views in real-time when switching languages without restarting the application.
*   **AST + Regex Syntactic Extractor (`extract_base_language`)**: Scans project source code to automatically catalog keys and generate both the base dictionary and line-level audit logs (`es_source.json`).
*   **Automated Translator with Anti-Hallucination Masking (`prepare_new_language`)**: Masks variables (`{user}`), HTML tags, and URLs using safe numeric tokens before calling external translation engines (Google Translate / Argos Translate / Mock), restoring them intact at the destination.
*   **Native PyInstaller Executable Support**: Automatic detection of frozen environments (`sys._MEIPASS`) to locate bundled resources without extra configuration.
*   **Interoperability with Other Languages and Frameworks**: Open architecture to share catalogs and translate corporate software across diverse tech stacks.

--------------------------------------------------------------------------------

#### 📦 Installation
##### 1. Direct Installation from GitHub (Recommended)
Install in your virtual environment via pip:
```powershell
pip install git+https://github.com/borispinto/pkg-i18n.git
```
Or declare it in your `requirements.txt`:
```text
pkg-i18n @ git+https://github.com/borispinto/pkg-i18n.git
```
Or in your `pyproject.toml`:
```toml
[project]
dependencies = [
    "pkg-i18n>=1.0.0",
]
```

--------------------------------------------------------------------------------

##### 2. Installation from Local Source Code
Standard clone and installation:
```powershell
git clone https://github.com/borispinto/pkg-i18n.git
cd pkg-i18n
pip install .
```
Or in editable mode for development:
```powershell
pip install -e .
```

> [!NOTE]
> **Optional Dependencies**:
> * For production execution and translation consumption (`t18n`): **zero external dependencies** (Python 3.8+ only).
> * For automated external translation tooling (`prepare_new_language` with online/offline engines), optionally install `deep-translator` (Google Translate) or `argostranslate` (Argos 100% offline):
> ```powershell
> pip install deep-translator
> ```

--------------------------------------------------------------------------------

#### 🏗️ 7-Layer Cascade Loading Architecture + Contingency
The `I18nManager` resolves translations by evaluating 7 layers in ascending hierarchical order (higher layers override lower layers if they define the same key):

| Layer | Source | Description |
| :---: | :--- | :--- |
| **0** | Python Code | In-code base dictionary loaded via `register_defaults()` |
| **1** | Internal `es.json` | Bundled default base language packaged with the application |
| **2** | External `es.json` | Base file in an external user-editable directory |
| **3** | Internal `{lang_base}.json` | Requested base language (e.g., `pt.json`) |
| **4** | External `{lang_base}.json` | External user-defined base file (e.g., user `pt.json`) |
| **5** | Internal `{lang_regional}.json` | Requested regional language (e.g., `pt-BR.json`) |
| **6** | External `{lang_regional}.json` | External user-defined regional file (e.g., user `pt-BR.json`) |
| 🟡 **Contingency** | In-code `t18n('key', 'default')` | Final runtime safety net: catches catalog inconsistencies and guarantees operational continuity |

--------------------------------------------------------------------------------

#### 📁 Project Structure and JSON File Format
##### Recommended structure in your consumer project
```text
my_project/
├── pyproject.toml / requirements.txt   # Declares dependency on pkg-i18n
├── src/
│   ├── app.py                         # Application code
│   └── ...
└── resources/
    └── languages/                     # Canonical path for language files
        ├── es.json                    # Base language
        ├── en.json                    # English language
        ├── pt.json                    # Secondary language
        └── pt-BR.json                 # Regional variants
```

> [!NOTE]
> The i18n engine automatically discovers the `resources/languages` folder in your project root, current working directory (CWD), or bundled inside PyInstaller executables.

##### Language JSON File Format
According to engine specifications, **reserved root-level keys prefixed with `_`** are:
* `_language_name`: Used to display the human-readable language name in UI selectors.
* `_default`: Reserved section for all general / global keys.

Standard sorting places `_language_name` first, followed by `_default`, and then project modules or subsections in alphabetical order:
```json
{
    "_language_name": "Español",
    "_default": {
        "app_title": "Mi Aplicación Python",
        "btn_open": "Abrir",
        "btn_save": "Guardar",
        "msg_welcome": "Bienvenido, {user}"
    },
    "modulo1": {
        "sec1": {
            "campo_usuario": "Nombre de usuario",
            "valor_clave": "Valor en Sección 1"
        }
    }
}
```

--------------------------------------------------------------------------------

#### 🛠️ Quick Developer Guide
##### 1. Initialization and Basic Consumption (`t18n`)
You can use the shorthand alias `t18n()` in any module or function across your project:
```python
from i18n import t18n

# 1. Keys from the _default section (both syntaxes are equivalent):
button_text = t18n("btn_open", "Abrir")
save_text = t18n("_default.btn_save", "Guardar")

# 2. Nested or composite section keys:
section_title = t18n("modulo1.sec1.valor_clave", "Valor por Defecto")

# 3. Safe dynamic variable injection:
message = t18n("msg_welcome", "Bienvenida, {user}", user="Dayana")

# 4. Fallback markers control (<Default Text>) on non-existent keys:
# By default, a missing key returns '<Default Text>' to alert the developer.
# To suppress '< >' markers and obtain clean text:
clean_text = t18n("msg_welcome", "Bienvenida, {user}", user="Dayana", suppress_markers=True)
```

--------------------------------------------------------------------------------

##### 2. Key Verification and Dictionary-Style Access
```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# Check for key existence:
if "btn_open" in i18n:
    print(i18n["btn_open"])
```

--------------------------------------------------------------------------------

##### 3. Language Directory Customization and Resolution
`pkg-i18n` allows querying and customizing both internal and external directory paths:

```python
from i18n import get_i18n_instance, resolve_languages_directory

path = resolve_languages_directory()
i18n = get_i18n_instance()
i18n.set_internal_languages_dir("resources/languages")
i18n.set_external_languages_dir("external/languages")
```

##### 4. In-Code Base Dictionary Registration (Layer 0)
To ensure immediate text availability without relying on files on disk, default values can be registered directly in code:
```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

i18n.register_defaults({
    "_language_name": "Español",
    "_default": {
        "btn_accept": "Aceptar",
        "btn_close": "Cerrar",
        "btn_continue": "Continuar"
    },
    "modulo1": {
        "clave_1": "Texto de la clave 1 del modulo1.",
        "clave_2": "Texto de la clave 2 del modulo1.",
    }
})
```

--------------------------------------------------------------------------------

##### 5. Real-Time Change Subscription (Observer Pattern)
For GUI applications (CustomTkinter, PyQt, PySide, Tkinter, WxPython), you can register subscriber functions to automatically refresh the interface whenever the language changes:
```python
from i18n import get_i18n_instance, t18n

i18n = get_i18n_instance()

def on_language_change(new_language_code: str):
    print(f"Language changed to: {new_language_code}")
    # Update graphical interface strings
    lbl_title.configure(text=t18n("app_title", "Mi Aplicación"))
    btn_open.configure(text=t18n("btn_open", "Abrir"))

# Subscribe callback
i18n.subscribe(on_language_change)

# When switching languages, `on_language_change` is invoked automatically:
i18n.set_language("pt-BR")
```

--------------------------------------------------------------------------------

##### 6. Available Languages Management and Listing
To populate dropdowns or selectors in the GUI:
```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# Retrieve list of dicts: [{'code': 'es', 'name': 'Español'}, ...]
languages_list = i18n.get_available_languages()

# Retrieve mapping for combo boxes keyed by name: {'Español': 'es', 'Português (Brasil)': 'pt-BR'}
languages_dict = i18n.get_available_languages(by_name=True)
```

--------------------------------------------------------------------------------

##### 7. Exporting Active Dictionary (`export_active_dictionary`)
Allows dumping the consolidated in-memory dictionary (`active_dictionary`) into a JSON file, exactly as resolved after applying all layers:
```python
from i18n import export_active_dictionary, get_i18n_instance

# 1. Export with default path ('dictionary.json' in current working directory):
generated_file = export_active_dictionary()

# 2. Export specifying a target folder:
generated_file = export_active_dictionary("path/to/my_folder/")

# 3. Export with custom path and filename:
generated_file = export_active_dictionary("path/to/my_folder/active_en.json")

# Or directly through the I18nManager instance:
i18n = get_i18n_instance()
i18n.export_active_dictionary("my_dictionary.json")
```

--------------------------------------------------------------------------------

##### 8. Development Tools and Automated Translation
###### Base Language Extractor (`extract_base_language`)
Scans your project's source code searching for `t18n()` calls and generates or updates `es.json` while preserving and ordering keys. If `output_dir` is omitted, it defaults to `resources/languages` relative to `origin_dir`:
```python
from i18n import extract_base_language

result = extract_base_language(
    origin_dir="src",                      # Folder or source file to scan
    output_dir=None,                       # Optional (defaults to: src/resources/languages)
    file_extensions=[".py", ".html"],      # File extensions to scan
    recursive=True,                        # Recursively scan subdirectories
    function_names=["t18n"],               # Function names to detect
    language_name="Español",
    target_filename="es.json",
    show_source=True                       # Generates standard es.json AND additionally es_source.json
)

print(result)
# {
#   'status': 'success',
#   'target_file': '.../resources/languages/es.json',
#   'source_file': '.../resources/languages/es_source.json',
#   'total_extracted': 15,
#   ...
# }
```

> [!TIP]
> **Dual output with `show_source=True`**:
> 1. `es.json` (Production): Clean key-value pairs ready for production (`"btn_open": "Abrir"`).
> 2. `es_source.json` (Audit / Development): Contains values and precise source mapping per file and line numbers:
> ```json
> "btn_open": {
>     "valor": "Abrir",
>     "source": {
>         "src/gui/main_window.py": [50, 520],
>         "src/gui/second_window.py": [3, 8, 25]
>     }
> }
> ```

###### Synchronization and Translation (`prepare_new_language`)
Creates or synchronizes templates for other languages (e.g., `en.json`, `pt.json`, `fr.json`) based on the base `es.json` file. If `target_dir` is not specified, it is automatically resolved via `resolve_languages_directory()`:
```python
from i18n import prepare_new_language

# Example 1: Automated translation using Google Translate (requires deep-translator)
result = prepare_new_language(
    target_code="fr",
    target_name="Français",
    default_dict={},                      # Optional dict if no es.json exists
    base_code="es",
    target_dir=None,                      # Optional (defaults to resources/languages)
    auto_translate=True,                  # Automatically translate missing strings
    engine="auto"                         # Options: 'auto', 'google', 'argos', 'mock'
)

# Example 2: Generate base template without external translation (offline/local)
result_offline = prepare_new_language(
    target_code="en",
    target_name="English",
    auto_translate=False
)
```

--------------------------------------------------------------------------------

##### 9. PyInstaller Bundling Support
The module automatically detects whether the application is running inside a frozen PyInstaller bundle (`sys._MEIPASS`).
When packaging with PyInstaller, include the canonical language resources directory using the `--add-data` flag:
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "resources/languages;resources/languages" src/main.py
```

--------------------------------------------------------------------------------

#### 🌐 Interoperability with Other Languages
Since **pkg-i18n** manages linguistic resources in standard JSON format files and exposes modular tooling, it is completely feasible to interoperate or share translation catalogs with applications developed in other languages or platforms (such as .NET, VB.NET, C#, JavaScript, or microservices), either by consuming the generated `.json` files directly or invoking extraction and synchronization workflows in a decoupled manner.

--------------------------------------------------------------------------------

#### 👥 Contact & Support
This project is developed and maintained by **Boris Pinto**, in collaboration with **Asisnet Computación, CA**.

##### 🛠️ Authorship and Personal Brand
If you would like to collaborate on open-source projects or connect professionally:
*   **Developer:** Boris Pinto
*   **Personal Email:** [borispinto@gmail.com](mailto:borispinto@gmail.com)
*   **GitHub Profile:** [@borispinto](https://github.com/borispinto)

##### 🏢 Enterprise Solutions and Connectivity
Need to adapt this tool to your business, require corporate technical support, or look for tailored technological infrastructure? At **Asisnet Computación, CA** we integrate software and hardware to optimize your operations.
*   **Our Services:**
    *   **Administrative Software:** Custom systems for managing and controlling your business.
    *   **Networks and Communications:** Design, installation, and technical support for networks, infrastructure, and connectivity.
    *   **Tech Equipment:** Sales, support, and hardware maintenance.
*   **Commercial Inquiries:** ([proyectos@asisnet.net](mailto:proyectos@asisnet.net))

--------------------------------------------------------------------------------

#### 📄 License
This project is licensed under the [MIT License](LICENSE). It is free and open-source software, fully authorized for use, modification, and integration in commercial and enterprise solutions.

Copyright (c) 2026 Boris Pinto. All rights reserved.
