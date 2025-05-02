# dfs3 — Distributed File System 3.0

![License](https://img.shields.io/badge/license-MIT-blue.svg)

`dfs3` is a distributed and decentralized file storage system designed as an academic Final Degree Project (TFG). It leverages low-power IoT devices like Raspberry Pi, encrypted storage, and events published on the IOTA Tangle to achieve redundancy, availability, and secure control with no central servers.

## Key Features

- **End-to-end encryption**: Files are encrypted on the client before upload.
- **Web 3.0 architecture**: Fully decentralized with no single points of failure.
- **Event propagation via IOTA + MQTT**: Efficient, auditable, and fault-tolerant communication.
- **Virtual file system**: Based on file paths, symbolic entries, and JSON metadata.
- **Replication across nodes**: Automatic management of redundant storage.
- **User and permission management**: Secure file sharing via encrypted keys.

## Architecture

- **Nodes**: Raspberry Pi devices that store encrypted files and listen to events.
- **Users**: Interact through nodes to upload, share, and download files.
- **REST Microservices**: Lightweight interfaces for file and user operations.
- **IOTA + MQTT**: IOTA stores persistent events, MQTT acts as the control channel.

## Repository Structure

```
dfs3/
├── api/               # REST API for users and files
├── core/              # Key logic, events, configuration
├── storage/           # Encrypted local storage and metadata
├── mqtt/              # MQTT client for network events
├── iota/              # Tangle publishing and querying
├── tests/             # Automated tests
├── node.json          # Encrypted node configuration
└── README.md          # This file
```

## Installation

Requires Python 3.10+ and pip:

```bash
git clone https://github.com/joseigbv/dfs3.git
cd dfs3
pip install -r requirements.txt
```

## Usage

### Initialize node

```bash
python main.py
```

If this is the first run, you will be asked for a passphrase to protect your private key. A `node.json` configuration file will be generated.

### Upload a file (REST client, TODO)

```bash
curl -X POST http://localhost:8000/files \
  -F "file=@document.pdf" \
  -F "filename=document.pdf"
```

## System Events

- `node_registered`: New node joined the network
- `file_created`: New file made available
- `file_shared`: File shared with another user
- `node_status`: Periodic heartbeat from the node

Events are published to IOTA and notified via MQTT.

---

## Motivación académica

Este proyecto se desarrolla como parte del Trabajo de Fin de Grado en Ingeniería Informática, con el objetivo de aplicar principios de la Web 3.0 al diseño de un sistema de almacenamiento distribuido orientado a IoT, bajo un enfoque seguro, abierto y trazable.

---

## Referencias

- [IPFS Whitepaper](https://ipfs.io/ipfs/Qm.../whitepaper.pdf)
- [Filecoin Spec](https://spec.filecoin.io)
- [Cardano Research](https://iohk.io/en/research/)
- [Erasure Coding IEEE Paper](https://doi.org/10.1109/TIT.2010.2054295)

---

## Licencia

Este proyecto está bajo licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.

---

## Contacto

Desarrollado por **José Ignacio Bravo Vicente**  
Contacto: [nacho.bravo@gmail.com]
