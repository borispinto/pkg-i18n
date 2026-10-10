# Guía de Integración e Instructivo: Sistema i18n para Python

<p align="left">
  <strong>Language / Idioma:</strong>
  <a href="README.md">🇪🇸 Español</a> |
  <a href="README.en.md">🇺🇸 English</a>
</p>

Este paquete proporciona una solución de **internacionalización (i18n)** completa, centralizada, extensible, de alto rendimiento y sin dependencias obligatorias para cualquier proyecto Python (aplicaciones de escritorio como PyQt/CustomTkinter, herramientas CLI, scripts o servidores web).

> **Nota de Interoperabilidad**: Aunque el paquete está desarrollado nativamente en Python, su arquitectura modular basada en catálogos JSON estándar y herramientas de extracción/traducción permite su **instalación e integración en sistemas de otros lenguajes**, como **VB.NET y C# (.NET)**. Consulta la sección [Integración con Otros Lenguajes (VB.NET y Ecosistema .NET)](#-integración-con-otros-lenguajes-vbnet-y-ecosistema-net) al final de este documento.

---

## 📋 Tabla de Contenidos
1. [Características Principales](#-características-principales)
2. [Instalación del Paquete](#-instalación-del-paquete)
3. [Estructura del Proyecto y Formato de Archivos JSON](#-estructura-del-proyecto-y-formato-de-archivos-json)
4. [Arquitectura de Carga en Cascada (7 Capas) + Contingencia](#-arquitectura-de-carga-en-cascada-7-capas)
5. [Uso del Motor en Python (`t18n`)](#-uso-del-motor-en-python-t18n)
6. [Instructivo de Integración e Importación en Python](#-instructivo-de-integración-e-importación-en-python)
7. [Suscripción a Cambios en Tiempo Real (Patrón Observador)](#-suscripción-a-cambios-en-tiempo-real-patrón-observador)
8. [Gestión y Listado de Idiomas Disponibles](#-gestión-y-listado-de-idiomas-disponibles)
9. [Exportar Diccionario Activo (`export_active_dictionary`)](#-exportar-diccionario-activo-export_active_dictionary)
10. [Herramientas de Desarrollo y Traducción Automática](#-herramientas-de-desarrollo-y-traducción-automática)
   - [Extractor de Idioma Base (`extract_base_language`)](#extractor-de-idioma-base-extract_base_language)
   - [Sincronización y Traducción (`prepare_new_language`)](#sincronización-y-traducción-prepare_new_language)
11. [Soporte para Empaquetado con PyInstaller](#-soporte-para-empaquetado-con-pyinstaller)
12. [Integración con Otros Lenguajes (VB.NET y Ecosistema .NET)](#-integración-con-otros-lenguajes-vbnet-y-ecosistema-net)
    - [Método 1: Catálogos JSON Compartidos y Herramientas CLI (Recomendado)](#método-1-catálogos-json-compartidos-y-herramientas-cli-recomendado)
    - [Método 2: Interoperabilidad en Tiempo de Ejecución con Python.NET (`pythonnet`)](#método-2-interoperabilidad-en-tiempo-de-ejecución-con-pythonnet-pythonnet)
    - [Método 3: Invocación por Subproceso / CLI o Microservicio Local](#método-3-invocación-por-subproceso--cli-o-microservicio-local)

---

## 🚀 Características Principales

- **Librería 100% Autónoma en Python**: No es necesario copiar carpetas de código dentro de cada proyecto; se instala e importa directamente como paquete estándar de Python.
- **Carga en Cascada Multicapa (7 Capas)**: Permite sobreescribir claves por defecto registradas en código, archivos base empaquetados (`es.json`), archivos regionalizados (`pt-BR.json`) y archivos externos editables por el usuario final.
- **Soporte para Notación de Puntos y Sección `_default`**: Las claves generales residen bajo la sección `"_default"` y se pueden invocar directamente (ej. `t18n("btn_open")` o `t18n("_default.btn_open")`). Las secciones anidadas soportan multinivel (ej. `t18n("modulo1.sec1.clave")`).
- **Respuesta Segura contra Fallos**: Si una clave no existe, formatea el texto base proporcionado y no interrumpe la ejecución del sistema.
- **Formateo Dinámico de Plantillas**: Inyección de variables con sintaxis estándar (ej. `"Bienvenido, {user}"`) con captura segura de errores de formato.
- **Patrón Observador Integrado**: Notificación automática e instantánea a la interfaz de usuario cuando el idioma cambia.
- **Extractor Sintáctico AST + Regex**: Analiza el código fuente del proyecto para extraer cadenas traducibles y actualizar el archivo base `es.json`.
- **Traductor Automático Inteligente**: Motores integrados (`GoogleTranslate`, `ArgosTranslate` 100% offline o `Mock`) con **enmascarado inteligente (`PlaceholderMasker`)** que protege variables (`{user}`), etiquetas HTML y URLs para evitar su corrupción durante la traducción.
- **Interoperabilidad Multilenguaje**: Capacidad para alimentar proyectos en VB.NET, C# y otros lenguajes a través de formatos estándar y puentes de interoperabilidad.

---

## 📦 Instalación del Paquete

**No es necesario copiar la carpeta del código fuente**. Instala `pkg-i18n` directamente en el entorno virtual de tu proyecto:

### 1. Instalación en modo desarrollo/editable (local)
```bash
pip install -e "/path/to/pkg-i18n"
```

### 2. En `requirements.txt` de tu proyecto
```text
# Enlace editable local durante desarrollo:
-e /path/to/pkg-i18n

# O enlace directo por repositorio GitHub:
# pkg-i18n @ git+https://github.com/borispinto/pkg-i18n.git
```

### 3. En `pyproject.toml` de tu proyecto
```toml
[project]
dependencies = [
    "pkg-i18n>=1.0.0",
]
```

---

## 📁 Estructura del Proyecto y Formato de Archivos JSON

### Estructura recomendada en tu proyecto consumidor
```text
mi_proyecto/
├── pyproject.toml / requirements.txt   # Declara dependencia a pkg-i18n
├── src/
│   ├── app.py                         # Código de tu aplicación
│   └── ...
└── resources/
    └── languages/                     # Ruta canónica para archivos de idioma
        ├── es.json                    # Idioma base
        ├── en.json                    # Idioma inglés
        ├── pt.json                    # Idioma secundario
        └── pt-BR.json                 # Variantes regionales
```

> **Nota**: El motor de `i18n` detecta automáticamente la carpeta `resources/languages` tanto en la raíz de tu proyecto, en el directorio de trabajo actual (`CWD`), o empaquetada dentro de ejecutables PyInstaller.

### Formato de Archivo JSON de Idioma
De acuerdo con las especificaciones del motor, las **claves reservadas con prefijo `_` en la raíz** son:
- `_language_name`: Utilizada para mostrar el nombre legible del idioma en selectores de la UI.
- `_default`: Sección reservada para todas las claves generales/globales.

El ordenamiento estándar ubica primero `_language_name`, luego `_default`, y a continuación los módulos o subsecciones del proyecto ordenados alfabéticamente:

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

---

## 🏗️ Arquitectura de Carga en Cascada (7 Capas) + Contingencia

El gestor `I18nManager` resuelve las traducciones evaluando 7 capas en orden jerárquico ascendente (cada capa superior sobreescribe a las anteriores):

| Capa | Origen | Descripción |
| :--- | :--- | :--- |
| **0** | Código Python | Diccionario base en código, se carga con `register_defaults()` |
| **1** | Interno `es.json` | Idioma base empaquetado por defecto en la aplicación |
| **2** | Externo `es.json` | Archivo base en directorio externo editable por el usuario |
| **3** | Interno `{lang_base}.json` | Idioma base solicitado (ej. `pt.json`) |
| **4** | Externo `{lang_base}.json` | Archivo base externo (ej. `pt.json` de usuario) |
| **5** | Interno `{lang_regional}.json` | Idioma regional solicitado (ej. `pt-BR.json`) |
| **6** | Externo `{lang_regional}.json` | Archivo regional externo (ej. `pt-BR.json` de usuario) |
| 🟡 **Contingencia** | Interno `t18n('clave', 'texto')` | Aplica para detectar inconsistencia del diccionario definido (red de seguridad final en tiempo de ejecución) |

---

## 💬 Uso del Motor en Python (`t18n`)

Puedes utilizar el alias abreviado `t18n()` en cualquier módulo o función de tu proyecto:

```python
from i18n import t18n

# 1. Claves de la sección _default (ambas sintaxis son equivalentes):
texto_boton = t18n("btn_open", "Abrir")
texto_guardar = t18n("_default.btn_save", "Guardar")

# 2. Claves de secciones anidadas o compuestas:
titulo_sec = t18n("modulo1.sec1.valor_clave", "Valor por Defecto")

# 3. Inyección segura de variables dinámicas:
mensaje = t18n("msg_welcome", "Bienvenida, {user}", user="Dayana")

# 4. Control de marcadores de fallback (<Texto Defecto>) en claves inexistentes:
# Por defecto, una clave inexistente retorna '<Texto Defecto>' (o '<Bienvenido, Carlos>') para alertar al desarrollador.
# Para suprimir los marcadores '< >' y obtener el texto limpio:
texto_limpio = t18n("msg_welcome", "Bienvenida, {user}", user="Dayana", suppress_markers=True)

# 5. Verificación de existencia de claves o acceso estilo diccionario:
from i18n import get_i18n_instance
i18n = get_i18n_instance()
if "btn_open" in i18n:
    print(i18n["btn_open"])
```

---

## 🛠️ Instructivo de Integración e Importación en Python

Una vez instalado el paquete, no necesitas configurar rutas de `sys.path`. Importa los símbolos directamente desde `i18n`:

```python
from i18n import get_i18n_instance, t18n, I18nManager, resolve_languages_directory

# 1. Obtener la instancia singleton de i18n (detecta resources/languages por defecto).

i18n = get_i18n_instance(default_lang={"es": "Español"})

# 2. (Opcional) Resolver la ruta canónica o personalizar carpetas de idiomas:
# ruta_idiomas = resolve_languages_directory()  # Retorna Path a resources/languages
# Se puede especificar una carpeta alternativa con set_external_languages_dir().
# i18n.set_internal_languages_dir("ruta/personalizada/resources/languages")
# i18n.set_external_languages_dir("ruta/usuario/resources/languages")

# 3. (Opcional) Registrar Diccionario base en código (Capa 0) estapa de desarrollo se puede alimentar con el resultado de la herramienta extract_base_language():
```
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
ó 
```
i18n_inst.register_defaults(get_default_translations_dict())

def get_default_translations_dict():
    """Retorna un diccionario completo con todas las claves e idioma base (es) de la aplicación."""
    data = {
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
    }
    return data
```

---

## 🔔 Suscripción a Cambios en Tiempo Real (Patrón Observador)

Para aplicaciones con interfaz gráfica (PyQt, PySide, Tkinter, CustomTkinter, WxPython), puedes suscribir funciones para refrescar automáticamente la interfaz cuando el usuario cambie el idioma:

```python
from i18n import get_i18n_instance, t18n

i18n = get_i18n_instance()

def al_cambiar_idioma(nuevo_codigo_idioma: str):
    print(f"El idioma cambió a: {nuevo_codigo_idioma}")
    # Actualizar textos de la interfaz gráfica
    lbl_titulo.configure(text=t18n("app_title", "Mi Aplicación"))
    btn_abrir.configure(text=t18n("btn_open", "Abrir"))

# Suscribir callback
i18n.subscribe(al_cambiar_idioma)

# Al cambiar de idioma, `al_cambiar_idioma` se ejecutará automáticamente:
i18n.set_language("pt-BR")
```

---

## 🌐 Gestión y Listado de Idiomas Disponibles

Para llenar combox/desplegables de selección de idioma en la interfaz:

```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# Obtener lista de dicts: [{'code': 'es', 'name': 'Español'}, ...]
idiomas_lista = i18n.get_available_languages()

# Obtener mapeo para combos por nombre: {'Español': 'es', 'Português (Brasil)': 'pt-BR'}
idiomas_dict = i18n.get_available_languages(by_name=True)
```

---

## 💾 Exportar Diccionario Activo (`export_active_dictionary`)

Permite volcar a un archivo JSON el diccionario activo en memoria (`active_dictionary`) tal cual está consolidado (con todas las capas resueltas y aplanadas):

```python
from i18n import export_active_dictionary, get_i18n_instance

# 1. Exportar con ruta por defecto ('dictionary.json' en el directorio actual de ejecución):
archivo_generado = export_active_dictionary()

# 2. Exportar especificando una carpeta de destino (se guardará como 'dictionary.json' en esa carpeta):
archivo_generado = export_active_dictionary("ruta/a/mi_carpeta/")

# 3. Exportar con ruta y nombre de archivo específico:
archivo_generado = export_active_dictionary("ruta/a/mi_carpeta/activo_en.json")

# O directamente desde la instancia de I18nManager:
i18n = get_i18n_instance()
i18n.export_active_dictionary("mi_diccionario.json")
```

---

## 🛠️ Herramientas de Desarrollo y Traducción Automática

### Extractor de Idioma Base (`extract_base_language`)

Escanea el código fuente de tu proyecto buscando invocaciones a `t18n()` y genera/actualiza el archivo `es.json` conservando y ordenando las claves. Si no se especifica `output_dir`, se ubica automáticamente en `resources/languages` relativo a `origin_dir`:

```python
from i18n import extract_base_language

resultado = extract_base_language(
    origin_dir="src",                      # Carpeta o archivo fuente a escanear
    output_dir=None,                       # Opcional (por defecto: src/resources/languages)
    file_extensions=[".py", ".html"],      # Extensiones a escanear
    recursive=True,                        # Escanear subdirectorios
    function_names=["t18n"],               # Nombres de funciones a detectar
    language_name="Español",
    target_filename="es.json",
    show_source=True                       # Genera es.json estándar Y adicionalmente es_source.json
)

print(resultado)
# {
#   'status': 'success',
#   'target_file': '.../resources/languages/es.json',
#   'source_file': '.../resources/languages/es_source.json',
#   'total_extracted': 15,
#   ...
# }
```

> **Generación dual con `show_source=True`**:
> 1. `es.json` (Archivo estándar para ejecución): Contiene las cadenas limpias para producción (`"btn_open": "Abrir"`).
> 2. `es_source.json` (Archivo de auditoría/desarrollo): Contiene el valor y el mapeo de fuentes por programa y líneas:
> ```json
> "btn_open": {
>     "valor": "Abrir",
>     "source": {
>         "src/gui/main_window.py": [50, 520],
>         "src/gui/second_window.py": [3, 8, 25]
>     }
> }
> ```

### Sincronización y Traducción (`prepare_new_language`)

Crea o sincroniza plantillas para otros idiomas (ej. `en.json`, `pt.json`, `fr.json`) a partir del idioma base `es.json`. Si no se indica `target_dir`, se resuelve automáticamente mediante `resolve_languages_directory()`:

```python
from i18n import prepare_new_language

# Ejemplo 1: Traducción automática usando Google Translate (requiere deep-translator)
resultado = prepare_new_language(
    target_code="fr",
    target_name="Français",
    default_dict={},                      # Diccionario opcional si no hay es.json
    base_code="es",
    target_dir=None,                      # Opcional (por defecto resources/languages)
    auto_translate=True,                  # Traducir automáticamente textos ausentes
    engine="auto"                         # Opciones: 'auto', 'google', 'argos', 'mock'
)

# Ejemplo 2: Generar plantilla base sin traducción externa (offline/local)
resultado_offline = prepare_new_language(
    target_code="en",
    target_name="English",
    auto_translate=False
)
```

---

## 📦 Soporte para Empaquetado con PyInstaller

El módulo detecta automáticamente si la aplicación se ejecuta dentro de un ejecutable congelado con PyInstaller (`sys._MEIPASS`).

Al generar el ejecutable con PyInstaller, incluye la carpeta canónica de recursos de idioma con la opción `--add-data`:

```bash
pyinstaller --noconfirm --onedir --windowed --add-data "resources/languages;resources/languages" src/main.py
```

---

## 🔌 Integración con Otros Lenguajes (VB.NET y Ecosistema .NET)

Aunque `pkg-i18n` está implementado nativamente en Python, su arquitectura permite que sistemas construidos en otros lenguajes (como **VB.NET**, **C#**, o aplicaciones .NET en general) aprovechen su ecosistema. Existen **tres métodos principales de integración**:

### Método 1: Catálogos JSON Compartidos y Herramientas CLI (Recomendado)

En esta modalidad desacoplada, `pkg-i18n` actúa como la herramienta de extracción y traducción automática durante el ciclo de desarrollo, mientras que la aplicación VB.NET consume directamente los archivos `resources/languages/*.json`:

#### 1. Extracción y Traducción desde Código VB.NET
El extractor sintáctico `extract_base_language` permite escanear archivos `.vb` mediante expresiones regulares y generar el archivo base `es.json`:
```python
from i18n import extract_base_language, prepare_new_language

# 1. Escanear llamadas t18n("clave", "Texto") en archivos VB.NET (.vb)
extract_base_language(
    origin_dir="MiProyectoVB",
    output_dir="MiProyectoVB/resources/languages",
    file_extensions=[".vb"],
    function_names=["t18n", "Traducir"]
)

# 2. Traducir automáticamente a otros idiomas (ej. Inglés y Portugués)
prepare_new_language(target_code="en", target_name="English", auto_translate=True)
prepare_new_language(target_code="pt-BR", target_name="Português (Brasil)", auto_translate=True)
```

#### 2. Consumo y Resolución en VB.NET
En la aplicación VB.NET (Windows Forms / WPF / ASP.NET), crea un módulo o clase auxiliar para resolver las claves con soporte de notación de puntos (`seccion.clave` y `default`):

```vb
Imports System.IO
Imports Newtonsoft.Json.Linq

Public Module I18nHelper
    Private _traducciones As JObject
    Private _idiomaActual As String = "es"
    Private _rutaIdiomas As String = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "resources", "languages")

    Public Sub CargarIdioma(codigoIdioma As String)
        _idiomaActual = codigoIdioma
        Dim archivoJson As String = Path.Combine(_rutaIdiomas, $"{codigoIdioma}.json")
        
        If File.Exists(archivoJson) Then
            Dim contenido As String = File.ReadAllText(archivoJson)
            _traducciones = JObject.Parse(contenido)
        Else
            _traducciones = New JObject()
        End If
    End Sub

    Public Function t18n(clave As String, Optional textoPorDefecto As String = "") As String
        If _traducciones Is Nothing Then Return If(String.IsNullOrEmpty(textoPorDefecto), clave, textoPorDefecto)

        ' 1. Búsqueda por ruta anidada (ej. modulo1.sec1.clave)
        Dim token As JToken = _traducciones.SelectToken(clave)

        ' 2. Si no se encuentra y no contiene punto, buscar en la sección 'default'
        If token Is Nothing AndAlso Not clave.Contains(".") Then
            token = _traducciones.SelectToken($"default.{clave}")
        End If

        If token IsNot Nothing Then
            Return token.ToString()
        End If

        Return If(String.IsNullOrEmpty(textoPorDefecto), clave, textoPorDefecto)
    End Function
End Module
```

**Uso en formularios o clases de VB.NET**:
```vb
Private Sub FormPrincipal_Load(sender As Object, e As EventArgs) Handles MyBase.Load
    I18nHelper.CargarIdioma("es")
    
    Me.Text = I18nHelper.t18n("app_title", "Mi Aplicación")
    btnAbrir.Text = I18nHelper.t18n("btn_open", "Abrir")
End Sub
```

---

### Método 2: Interoperabilidad en Tiempo de Ejecución con Python.NET (`pythonnet`)

Si la aplicación VB.NET requiere ejecutar el motor Python directamente en memoria para aprovechar las 7 capas de cascada completas y observadores:

1. Instala el paquete NuGet [pythonnet](https://www.nuget.org/packages/pythonnet/) en tu solución .NET.
2. Invoca el módulo `i18n` directamente desde VB.NET:

```vb
Imports Python.Runtime

Public Class I18nService
    Private Shared _i18nInstance As Object

    Public Shared Sub Inicializar()
        Runtime.PythonDLL = "python311.dll" ' Ajustar según la versión instalada de Python
        PythonEngine.Initialize()

        Using Py.GIL()
            Dim i18nModule As Object = Py.Import("i18n")
            _i18nInstance = i18nModule.get_i18n_instance()
        End Using
    End Sub

    Public Shared Function Traducir(clave As String, Optional textoDefecto As String = "") As String
        Using Py.GIL()
            Return _i18nInstance.t18n(clave, textoDefecto).ToString()
        End Using
    End Function

    Public Shared Sub CambiarIdioma(codigoIdioma As String)
        Using Py.GIL()
            _i18nInstance.set_language(codigoIdioma)
        End Using
    End Sub
End Class
```

---

### Método 3: Invocación por Subproceso / CLI o Microservicio Local

Para flujos de sincronización automatizada o arquitecturas de microservicios:
- **Subproceso desde VB.NET**: Ejecuta comandos o scripts Python mediante `System.Diagnostics.Process`:
  ```vb
  Dim startInfo As New ProcessStartInfo() With {
      .FileName = "python.exe",
      .Arguments = "-m i18n.cli_sync --target fr --auto-translate",
      .UseShellExecute = False,
      .RedirectStandardOutput = True
  }
  Using proc = Process.Start(startInfo)
      Dim salida As String = proc.StandardOutput.ReadToEnd()
      proc.WaitForExit()
  End Using
  ```
- **Microservicio Local**: Exponer `pkg-i18n` a través de un servicio REST ligero (FastAPI / Flask) y consumirlo vía `HttpClient` desde VB.NET.

---

## 👥 Autoría y Créditos

* **Arquitectura y Desarrollo:** [Boris Pinto](https://github.com/borispinto) (`borispinto@asisnet.net`)
* **Organización Colaboradora / Mantenedor:** [Asisnet Computacion, CA](https://www.asisnet.net) (`proyectos@asisnet.net`)
* **Repositorio Oficial:** [github.com/borispinto/pkg-i18n](https://github.com/borispinto/pkg-i18n)

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.  
Copyright © 2026 Boris Pinto.
