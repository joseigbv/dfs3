"""
Module: api/server.py
Description: FastAPI-based REST server for the dfs3 distributed file system node.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
"""

# MIT License
# Copyright (c) 2025 José Ignacio Bravo <nacho.bravo@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Change history:
#   2025-04-30 - José Ignacio Bravo - Initial creation

import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from config.settings import API_PORT, SSL_KEYFILE, SSL_CERTFILE


# Creamos una instancia de la aplicación
app = FastAPI()

# Permitir origen cruzado desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://node.dfs3.net"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-DFS3-File-ID",
        "X-DFS3-Owner",
        "X-DFS3-Size",
        "X-DFS3-IV",
        "X-DFS3-SHA256",
        "X-DFS3-Mimetype",
        "X-DFS3-Encrypted-Key",
        "X-DFS3-IV-Key",
        "X-DFS3-Public-Key",
    ]
)

# Configuracón de rutas
app.include_router(router, prefix="/api/v1")

# Permitimos la descarga de contenido estático
app.mount("/", StaticFiles(directory="webclient", html=True), name="static")


def start_api():
    """
    Starts the dfs3 HTTP API server.
    """
    uvicorn.run("api.server:app", 
        host="0.0.0.0", 
        port=API_PORT, 
        ssl_keyfile=SSL_KEYFILE,
        ssl_certfile=SSL_CERTFILE,
        log_level="info"
    )

