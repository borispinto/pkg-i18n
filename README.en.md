# Integration Guide & Reference Manual: i18n System for Python

<p align="left">
  <strong>Language / Idioma:</strong>
  <a href="README.md">🇪🇸 Español</a> |
  <a href="README.en.md">🇺🇸 English</a>
</p>

This package delivers a comprehensive, centralized, extensible, high-performance, and zero-mandatory-dependency **internationalization (i18n)** solution for any Python project (desktop apps like PyQt/CustomTkinter, CLI tools, automation scripts, or web backends).

> **Interoperability Notice**: While natively built in Python, its modular architecture based on standard JSON catalogs and AST/Regex extraction tools enables **cross-platform integration with other language ecosystems**, such as **VB.NET and C# (.NET)**. See the [Cross-Language Integration (VB.NET & .NET Ecosystem)](#-cross-language-integration-vbnet--net-ecosystem) section at the end of this document.

---

## 📋 Table of Contents
1. [Key Features](#-key-features)
2. [Installation](#-installation)
3. [Project Structure & JSON Catalog Format](#-project-structure--json-catalog-format)
4. [7-Layer Cascade Loading Architecture](#-7-layer-cascade-loading-architecture)
5. [Python Integration & Import Guide](#-python-integration--import-guide)
6. [Using the Engine in Python (`t18n`)](#-using-the-engine-in-python-t18n)
7. [Real-time Language Subscription (Observer Pattern)](#-real-time-language-subscription-observer-pattern)
8. [Available Languages Discovery & Management](#-available-languages-discovery--management)
9. [Export Active Dictionary (`export_active_dictionary`)](#-export-active-dictionary-export_active_dictionary)
10. [Development & Automated Translation Tools](#-development--automated-translation-tools)
    - [Base Language Extractor (`extract_base_language`)](#base-language-extractor-extract_base_language)
    - [Catalog Sync & Translation (`prepare_new_language`)](#catalog-sync--translation-prepare_new_language)
11. [PyInstaller Packaging Support](#-pyinstaller-packaging-support)
12. [Cross-Language Integration (VB.NET & .NET Ecosystem)](#-cross-language-integration-vbnet--net-ecosystem)
    - [Method 1: Shared JSON Catalogs & CLI Tools (Recommended)](#method-1-shared-json-catalogs--cli-tools-recommended)
    - [Method 2: In-Process Runtime Interop via Python.NET (`pythonnet`)](#method-2-in-process-runtime-interop-via-pythonnet-pythonnet)
    - [Method 3: Subprocess / CLI or Local Microservice](#method-3-subprocess--cli-or-local-microservice)
13. [Authorship & Credits](#-authorship--credits)
14. [License](#-license)

---

## 🚀 Key Features

- **100% Autonomous Python Library**: No need to vendor code inside downstream repositories; installs cleanly as a standard package.
- **7-Layer Cascade Resolution**: Dynamically resolves keys through in-memory fallbacks, bundled baseline catalogs (`es.json`), regional files (`pt-BR.json`), and user-customizable external directories.
- **Dot-Notation & `_default` Namespace Support**: General keys in `"_default"` can be accessed directly (e.g., `t18n("btn_open")` or `t18n("_default.btn_open")`). Multi-level nesting is fully supported (`t18n("module1.sec1.key")`).
- **Fail-Safe Robustness**: If a key does not exist, the engine returns the formatted fallback text without throwing unhandled exceptions.
- **Dynamic Template Formatting**: Inject variables safely with standard Python brace syntax (e.g., `"Welcome, {user}"`) with graceful fallback on format mismatches.
- **Built-in Observer Pattern**: Real-time notifications and automatic UI redraw callbacks whenever the active locale changes.
- **AST + Regex Extraction Engine**: Statically analyzes project source files to discover translatable strings and generate baseline `es.json` files.
- **Smart Automated Translation**: Seamless integration with translation backends (`GoogleTranslate`, offline `ArgosTranslate`, or `Mock`) accompanied by **intelligent variable masking (`PlaceholderMasker`)** protecting variables (`{user}`), HTML tags, and URLs from corruption.
- **Cross-Language Interoperability**: Capable of powering VB.NET, C#, and external tools through standard JSON contracts.

---

## 📦 Installation

Install `pkg-i18n` into your project virtual environment:

### 1. Local Editable Mode (Development)
```bash
pip install -e "/path/to/pkg-i18n"
```

### 2. In `requirements.txt`
```text
# Local editable development link:
-e /path/to/pkg-i18n

# Direct Git repository:
# pkg-i18n @ git+https://github.com/borispinto/pkg-i18n.git
```

### 3. In `pyproject.toml`
```toml
[project]
dependencies = [
    "pkg-i18n>=1.0.0",
]
```

---

## 📁 Project Structure & JSON Catalog Format

### Recommended consumer project layout
```text
my_project/
├── pyproject.toml / requirements.txt   # Declares dependency on pkg-i18n
├── src/
│   ├── app.py                         # Application source code
│   └── ...
└── resources/
    └── languages/                     # Canonical directory for translation catalogs
        ├── es.json                    # Baseline language
        ├── en.json                    # English translations
        ├── pt.json                    # Portuguese baseline
        └── pt-BR.json                 # Regional variants
```

> **Note**: The engine automatically discovers `resources/languages` in the project root, current working directory (`CWD`), or bundled within PyInstaller executables.

### JSON Catalog Format
Reserved root keys prefixed with `_`:
- `_language_name`: Display name of the locale for UI dropdowns.
- `_default`: Reserved namespace for global/general application strings.

```json
{
    "_language_name": "English",
    "_default": {
        "app_title": "My Python Application",
        "btn_open": "Open",
        "btn_save": "Save",
        "msg_welcome": "Welcome, {user}"
    },
    "module1": {
        "sec1": {
            "user_field": "Username",
            "key_value": "Section 1 Value"
        }
    }
}
```

---

## 🏗️ 7-Layer Cascade Loading Architecture

`I18nManager` resolves translations by evaluating 7 hierarchical layers in ascending priority order (higher layers override lower layers):

| Layer | Source | Description |
| :--- | :--- | :--- |
| **Layer 0** | Python Code | Dynamic in-memory defaults registered via `register_defaults()` |
| **Layer 1** | Bundled `es.json` | Default baseline locale packaged inside the application |
| **Layer 2** | External `es.json` | Baseline catalog in user-editable external directory |
| **Layer 3** | Bundled `{lang_base}.json` | Requested base language catalog (e.g., `pt.json`) |
| **Layer 4** | External `{lang_base}.json` | External base language catalog (e.g., user-provided `pt.json`) |
| **Layer 5** | Bundled `{lang_regional}.json` | Requested regional variant catalog (e.g., `pt-BR.json`) |
| **Layer 6** | External `{lang_regional}.json` | External regional variant catalog (e.g., user-provided `pt-BR.json`) |

---

## 🛠️ Python Integration & Import Guide

```python
from i18n import get_i18n_instance, t18n, I18nManager, resolve_languages_directory

# 1. Obtain singleton instance (auto-discovers resources/languages by default)
i18n = get_i18n_instance(default_lang={"es": "Español"})

# 2. (Optional) Customizing internal or external directory paths:
# i18n.set_internal_languages_dir("custom/path/resources/languages")
# i18n.set_external_languages_dir("user/override/resources/languages")

# 3. (Optional) Register code-level fallback defaults (Layer 0):
i18n.register_defaults({
    "btn_open": "Open File",
    "module1": {
        "sec1": {"key_value": "Internal Fallback"}
    }
})
```

---

## 💬 Using the Engine in Python (`t18n`)

```python
from i18n import t18n

# 1. Global / _default section keys:
open_text = t18n("btn_open", "Open")
save_text = t18n("_default.btn_save", "Save")

# 2. Nested section keys:
sec_title = t18n("module1.sec1.key_value", "Default Title")

# 3. Dynamic template variable injection:
welcome_msg = t18n("msg_welcome", "Welcome, {user}", user="Boris")

# 4. Suppress fallback markers (<Fallback Text>) for clean production output:
clean_text = t18n("missing_key", "Fallback Value", suppress_markers=True)

# 5. Dictionary-style lookup or existence checks:
from i18n import get_i18n_instance
i18n = get_i18n_instance()
if "btn_open" in i18n:
    print(i18n["btn_open"])
```

---

## 🔔 Real-time Language Subscription (Observer Pattern)

For desktop GUI frameworks (PyQt, PySide, Tkinter, CustomTkinter, WxPython):

```python
from i18n import get_i18n_instance, t18n

i18n = get_i18n_instance()

def on_language_changed(new_locale_code: str):
    print(f"Language switched to: {new_locale_code}")
    # Refresh GUI widgets
    lbl_title.configure(text=t18n("app_title", "My Application"))
    btn_open.configure(text=t18n("btn_open", "Open"))

# Subscribe callback
i18n.subscribe(on_language_changed)

# Changing language triggers the callback automatically:
i18n.set_language("en")
```

---

## 🌐 Available Languages Discovery & Management

Populate UI language selectors and combo boxes:

```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# List of dicts: [{'code': 'es', 'name': 'Español'}, {'code': 'en', 'name': 'English'}, ...]
lang_list = i18n.get_available_languages()

# Key-value mapping for combo boxes: {'English': 'en', 'Español': 'es'}
lang_map = i18n.get_available_languages(by_name=True)
```

---

## 💾 Export Active Dictionary (`export_active_dictionary`)

Dump the consolidated, flattened active dictionary from memory to a single JSON snapshot:

```python
from i18n import export_active_dictionary, get_i18n_instance

# 1. Export with default path ('dictionary.json' in current working directory):
generated_file = export_active_dictionary()

# 2. Export into a target folder:
generated_file = export_active_dictionary("path/to/export/folder/")

# 3. Export with explicit path and filename:
generated_file = export_active_dictionary("path/to/export/active_en.json")
```

---

## 🛠️ Development & Automated Translation Tools

### Base Language Extractor (`extract_base_language`)

Scans Python source files for `t18n()` invocations and generates/updates `es.json`:

```python
from i18n import extract_base_language

result = extract_base_language(
    origin_dir="src",                      # Folder or file to scan
    output_dir=None,                       # Optional (defaults to src/resources/languages)
    file_extensions=[".py", ".html"],      # File extensions
    recursive=True,                        # Scan subdirectories
    function_names=["t18n"],               # Function names to detect
    language_name="Español",
    target_filename="es.json",
    show_source=True                       # Generates es.json AND audit file es_source.json
)

print(result)
```

### Catalog Sync & Translation (`prepare_new_language`)

Synchronizes target locale catalogs (e.g., `en.json`, `fr.json`) against baseline `es.json`:

```python
from i18n import prepare_new_language

# Example 1: Automated translation using Google Translate
result = prepare_new_language(
    target_code="en",
    target_name="English",
    base_code="es",
    auto_translate=True,                  # Translate missing strings automatically
    engine="auto"                         # Options: 'auto', 'google', 'argos', 'mock'
)

# Example 2: Scaffold new language catalog without network translation
result_offline = prepare_new_language(
    target_code="de",
    target_name="Deutsch",
    auto_translate=False
)
```

---

## 📦 PyInstaller Packaging Support

The package automatically detects frozen binaries via `sys._MEIPASS`.

Include your language catalogs using `--add-data`:

```bash
pyinstaller --noconfirm --onedir --windowed --add-data "resources/languages;resources/languages" src/main.py
```

---

## 🔌 Cross-Language Integration (VB.NET & .NET Ecosystem)

### Method 1: Shared JSON Catalogs & CLI Tools (Recommended)

1. **Extraction**: Use `extract_base_language` to scan `.vb` files and populate `es.json`.
2. **Consumption in VB.NET**:

```vb
Imports System.IO
Imports Newtonsoft.Json.Linq

Public Module I18nHelper
    Private _translations As JObject
    Private _currentLang As String = "en"
    Private _langDir As String = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "resources", "languages")

    Public Sub LoadLanguage(langCode As String)
        _currentLang = langCode
        Dim jsonPath As String = Path.Combine(_langDir, $"{langCode}.json")
        
        If File.Exists(jsonPath) Then
            _translations = JObject.Parse(File.ReadAllText(jsonPath))
        Else
            _translations = New JObject()
        End If
    End Sub

    Public Function t18n(key As String, Optional defaultText As String = "") As String
        If _translations Is Nothing Then Return If(String.IsNullOrEmpty(defaultText), key, defaultText)

        Dim token As JToken = _translations.SelectToken(key)
        If token Is Nothing AndAlso Not key.Contains(".") Then
            token = _translations.SelectToken($"_default.{key}")
        End If

        If token IsNot Nothing Then Return token.ToString()
        Return If(String.IsNullOrEmpty(defaultText), key, defaultText)
    End Function
End Module
```

### Method 2: In-Process Runtime Interop via Python.NET (`pythonnet`)

Run the Python engine directly inside the .NET process memory:

```vb
Imports Python.Runtime

Public Class I18nService
    Private Shared _i18nInstance As Object

    Public Shared Sub Initialize()
        Runtime.PythonDLL = "python311.dll"
        PythonEngine.Initialize()

        Using Py.GIL()
            Dim i18nModule As Object = Py.Import("i18n")
            _i18nInstance = i18nModule.get_i18n_instance()
        End Using
    End Sub

    Public Shared Function Translate(key As String, Optional fallback As String = "") As String
        Using Py.GIL()
            Return _i18nInstance.t18n(key, fallback).ToString()
        End Using
    End Function
End Class
```

---

## 👥 Authorship & Credits

* **Architecture & Development:** [Boris Pinto](https://github.com/borispinto) (`borispinto@asisnet.net`)
* **Contributing Organization / Maintainer:** [Asisnet Computacion, CA](https://www.asisnet.net) (`proyectos@asisnet.net`)
* **Official Repository:** [github.com/borispinto/pkg-i18n](https://github.com/borispinto/pkg-i18n)

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.  
Copyright © 2026 Boris Pinto.
