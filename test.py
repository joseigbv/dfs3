# dfs3.py

from api.server import start_api_server
import threading
import asyncio

async def main():
    # Aquí iría la lógica de inicialización del nodo, eventos, etc.
    # ...

    # Lanzar API REST en hilo separado
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # Simulación del loop principal
    while True:
        print("[dfs3] Nodo activo. Esperando eventos...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())

