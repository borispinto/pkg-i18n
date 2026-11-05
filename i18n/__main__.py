# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 ASISNET Computación, CA <proyectos@asisnet.net>
# SPDX-FileCopyrightText: 2026 Boris Pinto <borispinto@gmail.com>
# SPDX-License-Identifier: MIT
# Autor: Boris Pinto <borispinto@gmail.com>
# Contacto Institucional: ASISNET Computación, CA <proyectos@asisnet.net>
# File: i18n/__main__.py

"""Punto de entrada canónico para ejecución modular vía python -m i18n (PEP 338)."""

import os
import sys

# Asegurar que el directorio padre del paquete esté en sys.path al ejecutarse como directorio
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from i18n.cli import main

if __name__ == "__main__":
    sys.exit(main())
