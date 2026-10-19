# 🌐 pkg-i18n

[🇪🇸 Español](README.md) | [🇺🇸 English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python Version](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://www.python.org/) [![Architecture: 7-Layer Cascade](https://img.shields.io/badge/architecture-7--layer%20cascade-orange.svg)](#-arquitectura-de-carga-en-cascada-7-capas--contingencia) [![Zero Runtime Dependencies](https://img.shields.io/badge/dependencies-zero%20mandatory-brightgreen.svg)](#-instalación)

Este paquete proporciona una solución de **internacionalización  (i18n), localización (l10n)** completa, centralizada, extensible, de alto rendimiento y sin dependencias obligatorias para cualquier proyecto Python (aplicaciones de escritorio como PyQt/CustomTkinter, herramientas CLI, scripts o servidores web).

**pkg-i18n** es la infraestructura integral de internacionalización (i18n), localización (l10n), utilizada por las aplicaciones de la suite **Asisnet**.

--------------------------------------------------------------------------------


--------------------------------------------------------------------------------

#### 📋 Tabla de Contenidos

1. [🎯 ¿Por qué pkg-i18n? (Propósito e Intención)](#-por-qué-pkg-i18n-propósito-e-intención)
2. [🚀 Capacidades y Características Clave](#-capacidades-y-características-clave)
3. [📦 Instalación](#-instalación)
4. [🏗️ Arquitectura de Carga en Cascada (7 Capas) + Contingencia](#️-arquitectura-de-carga-en-cascada-7-capas--contingencia)
5. [📁 Estructura del Proyecto y Formato de Archivos JSON](#-estructura-del-proyecto-y-formato-de-archivos-json)
6. [🛠️ Guía Rápida para Desarrolladores](#️-guía-rápida-para-desarrolladores)
   - [1. Inicialización y Consumo Básico (`t18n`)](#1-inicialización-y-consumo-básico-t18n)
   - [2. Verificación de Claves y Acceso Estilo Diccionario](#2-verificación-de-claves-y-acceso-estilo-diccionario)
   - [3. Personalización y Resolución de Rutas de Idiomas](#3-personalización-y-resolución-de-rutas-de-idiomas)
   - [4. Registro de Diccionario Base en Código (Capa 0)](#4-registro-de-diccionario-base-en-código-capa-0)
   - [5. Suscripción a Cambios en Tiempo Real (Patrón Observador)](#5-suscripción-a-cambios-en-tiempo-real-patrón-observador)
   - [6. Gestión y Listado de Idiomas Disponibles](#6-gestión-y-listado-de-idiomas-disponibles)
   - [7. Exportación del Diccionario Activo](#7-exportación-del-diccionario-activo-export_active_dictionary)
   - [8. Herramientas de Desarrollo y Traducción Automática](#8-herramientas-de-desarrollo-y-traducción-automática)
   - [9. Soporte para Empaquetado con PyInstaller](#9-soporte-para-empaquetado-con-pyinstaller)
7. [🌐 Interoperabilidad con Otros Lenguajes](#-interoperabilidad-con-otros-lenguajes)
8. [👥 Contacto y Soporte](#-contacto-y-soporte)
9. [📄 Licencia](#-licencia)

--------------------------------------------------------------------------------

#### 🎯 ¿Por qué pkg-i18n? (Propósito e Intención)
En el desarrollo de aplicaciones empresariales y de misión crítica, la gestión de textos multilingües suele convertirse en una  **tarea repetitiva, desorganizada y propensa a fallos** :
*   **Textos dispersos en código (hardcoded)** : Cadenas incrustadas directamente en la interfaz gráfica o lógica de negocio que dificultan auditorías, adaptaciones regionales y cambios de idioma.
*   **Dependencias pesadas y rígidas** : Herramientas tradicionales que requieren compilar catálogos binarios (.mo, .po) o atan los proyectos a dependencias complejas incompatibles con entornos ligeros o embebidos.
*   **Inconsistencias y caídas en tiempo de ejecución** : Ausencia de redes de contingencia deterministas ante claves ausentes en catálogos desactualizados, provocando errores no controlados frente al usuario.
*   **Corrupción al traducir automáticamente** : Pérdida de variables dinámicas ({user}), etiquetas HTML o URLs cuando se envían textos planos a motores de traducción externa.
*   **Aislamiento entre plataformas** : Dificultad para compartir un catálogo único de términos entre aplicaciones modernas en Python y sistemas empresariales consolidados en otros lenguajes (como .NET / VB.NET).
**pkg-i18n nace para erradicar definitivamente estos problemas** , proveyendo una solución  **llave en mano, modular, resiliente y de alto rendimiento** :
1.  **Resolución en 1 sola línea (t18n)** : Consulta inmediata con resolución por notación de puntos y red de contingencia transparente.
2.  **Carga en Cascada Multicapa (7 Capas + Contingencia)** : Permite sobreescribir desde diccionarios base en código hasta catálogos empaquetados y archivos editables externos por sucursal o usuario final, con una red de contingencia que garantiza cero interrupciones en producción.
3.  **Cero Dependencias Obligatorias en Runtime ($O(1)$)** : Consumo ultra liviano en memoria utilizando exclusivamente la biblioteca estándar de Python.
4.  **Traducción Asistida Inteligente con Enmascaramiento Seguro** : Automatización de catálogos protegiendo variables, saltos de línea y sintaxis HTML contra alucinaciones o alteraciones externas.
5.  **Ecosistema Abierto e Interoperable** : Formato JSON estándar listo para ser consumido tanto en Python como en soluciones corporativas .NET / VB.NET.

--------------------------------------------------------------------------------

#### 🚀 Capacidades y Características Clave
*   **Librería 100% Autónoma en Consumo** : Funciona exclusivamente sobre la biblioteca estándar de Python (json, re, logging, pathlib). No requiere dependencias de terceros para operar en producción.
*   **Resolución Ultrarrápida en Cascada Jerárquica (7 Capas)** : Resuelve diccionarios en memoria combinando valores registrados en código (Capa 0), archivos base empaquetados (es.json), variantes regionales (pt-BR.json) y capas externas personalizables.
*   **Red de Contingencia en Runtime** : Si una clave no se encuentra en ninguna capa del catálogo, t18n(clave, texto_defecto) formatea y entrega el texto por defecto proporcionado, garantizando continuidad operativa absoluta.
*   **Acceso Directo con Notación de Puntos y Sección _default** : Soporta claves directas (ej. t18n("btn_open") resuelve _default.btn_open) y rutas modulares anidadas (ej. t18n("modulo1.sec1.clave")).
*   **Formateo Seguro de Parámetros Dinámicos** : Inyección de variables con sintaxis estándar ("Bienvenido, {user}") con tolerancia y protección ante fallos de formato.
*   **Patrón Observador para Interfaces de Usuario** : Suscripción reactiva mediante i18n.subscribe(callback) para actualizar ventanas y vistas en tiempo real al conmutar el idioma sin reiniciar el aplicativo.
*   **Extractor Sintáctico AST + Regex (extract_base_language)** : Escanea el código fuente del proyecto para catalogar claves automáticamente y generar el diccionario base y auditoría de líneas (es_source.json).
*   **Traductor Automático con Enmascaramiento Antialucinación (prepare_new_language)** : Enmascara variables ({user}), etiquetas HTML y URLs con tokens numéricos seguros antes de invocar traductores externos (Google Translate / Argos Translate / Mock), restaurándolos íntegros en el destino.
*   **Soporte Nativo para Ejecutables PyInstaller** : Detección automática del entorno congelado (sys._MEIPASS) para localizar recursos empaquetados sin configuración adicional.
*   **Interoperabilidad con Ecosistemas .NET y VB.NET** : Arquitectura abierta para compartir catálogos y traducir software corporativo en múltiples lenguajes.

--------------------------------------------------------------------------------

#### 📦 Instalación
##### 1. Instalación Directa desde GitHub (Recomendado)
Instalación en el entorno virtual mediante pip:
```powershell
pip install git+https://github.com/borispinto/pkg-i18n.git

```
O declarándolo en tu archivo requirements.txt:
```text
pkg-i18n @ git+https://github.com/borispinto/pkg-i18n.git

```
O en tu archivo pyproject.toml:
```toml
[project]
dependencies = [
    "pkg-i18n>=1.0.0",
]

```

--------------------------------------------------------------------------------

##### 2. Instalación desde el Código Fuente Local
Clonación e instalación estándar:
```powershell
git clone https://github.com/borispinto/pkg-i18n.git
cd pkg-i18n
pip install .

```
O en modo editable para desarrollo:
```powershell
pip install -e .

```
>[!NOTE]  **Dependencias Opcionales** :
>*  Para ejecución en producción y consumo de traducciones (t18n),  **cero dependencias externas**  (solo Python 3.8+).
>*  Para herramientas de traducción automática externa (prepare_new_language con motores online/offline), se requiere instalar opcionalmente deep-translator (Google Translate) o argostranslate (Argos 100% offline):
>```powershell
>pip install deep-translator

>```

--------------------------------------------------------------------------------

#### 🏗️ Arquitectura de Carga en Cascada (7 Capas) + Contingencia
El gestor I18nManager resuelve las traducciones evaluando 7 capas en orden jerárquico ascendente (cada capa superior sobreescribe a las anteriores si define la misma clave):
| Capa | Origen | Descripción |
| ------ | ------ | ------ |
| **0** | Código Python | Diccionario base en código, cargado mediante register_defaults() |
| **1** | Interno es.json | Idioma base empaquetado por defecto en la aplicación |
| **2** | Externo es.json | Archivo base en directorio externo editable por el usuario |
| **3** | Interno {lang_base}.json | Idioma base solicitado (ej. pt.json) |
| **4** | Externo {lang_base}.json | Archivo base externo (ej. pt.json de usuario) |
| **5** | Interno {lang_regional}.json | Idioma regional solicitado (ej. pt-BR.json) |
| **6** | Externo {lang_regional}.json | Archivo regional externo (ej. pt-BR.json de usuario) |
| 🟡  **Contingencia** | En código t18n('clave', 'texto') | Red de seguridad final en tiempo de ejecución: detecta inconsistencias del catálogo y garantiza continuidad operativa |


--------------------------------------------------------------------------------

#### 📁 Estructura del Proyecto y Formato de Archivos JSON
##### Estructura recomendada en tu proyecto consumidor
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
>[!NOTE] El motor de i18n detecta automáticamente la carpeta resources/languages tanto en la raíz de tu proyecto, en el directorio de trabajo actual (CWD), o empaquetada dentro de ejecutables PyInstaller.

##### Formato de Archivo JSON de Idioma
De acuerdo con las especificaciones del motor, las  **claves reservadas con prefijo _ en la raíz**  son:
*  _language_name: Utilizada para mostrar el nombre legible del idioma en selectores de la UI.
*  _default: Sección reservada para todas las claves generales/globales.
El ordenamiento estándar ubica primero _language_name, luego _default, y a continuación los módulos o subsecciones del proyecto ordenados alfabéticamente:
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

#### 🛠️ Guía Rápida para Desarrolladores
##### 1. Inicialización y Consumo Básico (t18n)
Puedes utilizar el alias abreviado t18n() en cualquier módulo o función de tu proyecto:
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
# Por defecto, una clave inexistente retorna '<Texto Defecto>' para alertar al desarrollador.
# Para suprimir los marcadores '< >' y obtener el texto limpio:
texto_limpio = t18n("msg_welcome", "Bienvenida, {user}", user="Dayana", suppress_markers=True)

```

--------------------------------------------------------------------------------

##### 2. Verificación de Claves y Acceso Estilo Diccionario
```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# Verificación de existencia de claves:
if "btn_open" in i18n:
    print(i18n["btn_open"])

```

--------------------------------------------------------------------------------

##### 3. Personalización y Resolución de Rutas de Idiomas
`pkg-i18n` permite consultar y personalizar las rutas de directorios internos y externos:

```python
from i18n import get_i18n_instance, resolve_languages_directory

ruta = resolve_languages_directory()
i18n = get_i18n_instance()
i18n.set_internal_languages_dir("resources/languages")
i18n.set_external_languages_dir("external/languages")
```

##### 4. Registro de Diccionario Base en Código (Capa 0)
Para asegurar disponibilidad inmediata de textos sin depender de archivos en disco, se pueden registrar valores por defecto en código:
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

##### 5. Suscripción a Cambios en Tiempo Real (Patrón Observador)
Para aplicaciones con interfaz gráfica (CustomTkinter, PyQt, PySide, Tkinter, WxPython), puedes suscribir funciones para refrescar automáticamente la interfaz cuando el usuario cambie el idioma:
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

--------------------------------------------------------------------------------

##### 6. Gestión y Listado de Idiomas Disponibles
Para alimentar selectores o combos desplegables en la interfaz gráfica:
```python
from i18n import get_i18n_instance

i18n = get_i18n_instance()

# Obtener lista de dicts: [{'code': 'es', 'name': 'Español'}, ...]
idiomas_lista = i18n.get_available_languages()

# Obtener mapeo para combos por nombre: {'Español': 'es', 'Português (Brasil)': 'pt-BR'}
idiomas_dict = i18n.get_available_languages(by_name=True)

```

--------------------------------------------------------------------------------

##### 7. Exportación del Diccionario Activo (export_active_dictionary)
Permite volcar a un archivo JSON el diccionario consolidado en memoria (active_dictionary) tal cual está resuelto tras aplicar todas las capas:
```python
from i18n import export_active_dictionary, get_i18n_instance

# 1. Exportar con ruta por defecto ('dictionary.json' en el directorio de trabajo actual):
archivo_generado = export_active_dictionary()

# 2. Exportar especificando una carpeta de destino:
archivo_generado = export_active_dictionary("ruta/a/mi_carpeta/")

# 3. Exportar con ruta y nombre de archivo específico:
archivo_generado = export_active_dictionary("ruta/a/mi_carpeta/activo_en.json")

# O directamente desde la instancia de I18nManager:
i18n = get_i18n_instance()
i18n.export_active_dictionary("mi_diccionario.json")

```

--------------------------------------------------------------------------------

##### 8. Herramientas de Desarrollo y Traducción Automática
###### Extractor de Idioma Base (extract_base_language)
Escanea el código fuente de tu proyecto buscando llamadas a t18n() y genera o actualiza el archivo es.json conservando y ordenando las claves. Si no se especifica output_dir, se ubica automáticamente en resources/languages relativo a origin_dir:
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
[!TIP]  **Generación dual con show_source=True** :
1. es.json (Producción): Contiene las cadenas limpias para producción ("btn_open": "Abrir").
2. es_source.json (Auditoría / Desarrollo): Contiene el valor y el mapeo de fuentes por programa y números de línea:
```json
"btn_open": {
    "valor": "Abrir",
    "source": {
        "src/gui/main_window.py": [50, 520],
        "src/gui/second_window.py": [3, 8, 25]
    }
}

```
###### Sincronización y Traducción (prepare_new_language)
Crea o sincroniza plantillas para otros idiomas (ej. en.json, pt.json, fr.json) a partir del idioma base es.json. Si no se indica target_dir, se resuelve automáticamente mediante resolve_languages_directory():
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

--------------------------------------------------------------------------------

##### 9. Soporte para Empaquetado con PyInstaller
El módulo detecta automáticamente si la aplicación se ejecuta dentro de un ejecutable congelado con PyInstaller (sys._MEIPASS).
Al generar el ejecutable con PyInstaller, incluye la carpeta canónica de recursos de idioma con la opción --add-data:
```bash
pyinstaller --noconfirm --onedir --windowed --add-data "resources/languages;resources/languages" src/main.py

```

--------------------------------------------------------------------------------

#### 🌐 Interoperabilidad con Otros Lenguajes
Dado que **pkg-i18n** gestiona sus recursos lingüísticos en archivos de formato estándar JSON y expone herramientas modulares, es totalmente factible interoperar o compartir los catálogos de traducción con aplicaciones desarrolladas en otros lenguajes o plataformas (tales como .NET, VB.NET, C#, JavaScript o microservicios), ya sea consumiendo directamente los archivos `.json` generados o invocando los procesos de extracción y sincronización de forma desacoplada.

--------------------------------------------------------------------------------

#### 👥 Contacto y Soporte
Este proyecto es desarrollado y mantenido por  **Boris Pinto**, en colaboración con  **Asisnet Computación, CA** .
##### 🛠️ Autoría y Marca Personal
Si deseas colaborar en proyectos de código abierto o conectar profesionalmente:
*   **Desarrollador:**  Boris Pinto
*   **Correo Personal:**  [borispinto@gmail.com](mailto:borispinto@gmail.com)
*   **GitHub Profile:**  [@borispinto](https://github.com/borispinto)
##### 🏢 Soluciones Empresariales y Conectividad
¿Necesitas adaptar esta herramienta a tu negocio, requieres soporte técnico corporativo o buscas una infraestructura tecnológica a la medida? En  **Asisnet Computación, CA**  integramos software y hardware para optimizar tu operación.
*   **Nuestros Servicios:**
    *   **Software Administrativo:**  Sistemas a la medida para la gestión y control de tu negocio.
    *   **Redes y Comunicaciones:**  Diseño, instalación y soporte técnico para redes, infraestructura y conectividad.
    *   **Equipos Tecnológicos:**  Venta, soporte y mantenimiento de equipos.
*   **Contacto Comercial:**  ([proyectos@asisnet.net](mailto:proyectos@asisnet.net))

--------------------------------------------------------------------------------

#### 📄 Licencia
Este proyecto está bajo la Licencia [MIT](LICENSE). Es software libre y de código abierto, totalmente autorizado para su uso, modificación e integración en soluciones comerciales y empresariales.

Copyright (c) 2026 Boris Pinto. Todos los derechos reservados.