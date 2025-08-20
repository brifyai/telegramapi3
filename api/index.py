#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Entry point para Vercel
"""

import sys
import os

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la aplicación Flask
from web_interface import app

# Configurar para producción
app.debug = False
app.config['TESTING'] = False

# Para Vercel, necesitamos exportar la app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
