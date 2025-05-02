# dfs3 – Documentación de Funciones y Tests

Este documento resume las funciones, módulos y pruebas unitarias desarrolladas hasta la fecha en el sistema `dfs3`. Cada función incluye su descripción (docstring) y está organizada por módulo.

---

## utils/logger.py

- **`LOG(msg, level=Verbosity.MEDIUM)`**: Logs a general informational message if the given verbosity level is allowed.
- **`WRN(msg)`**: Logs a warning message, regardless of the global verbosity setting.
- **`ERR(msg)`**: Logs an error message, regardless of the global verbosity setting.

## core/db_init.py

- **`create_db()`**: Creates the SQLite database and all required tables if they do not already exist.

## core/event_handler.py

- **`validate_event_json(event: dict)`**: Validates the structure and content of a full dfs3 event.
- **`handle_node_status(event: dict)`**: Handles a node_status event.
- **`process_event(event: dict)`**: Processes a dfs3 event by validating and dispatching it to the appropriate handler.

## iota/listener.py

- **`validate_mqtt_event(data: dict)`**: Validates that the received MQTT message contains the required structure.
- **`fetch_and_process_event(block_id: str)`**: Simulates retrieval of an event from IOTA using the block_id, then processes it.
- **`on_connect(client, userdata, flags, rc)`**: Callback triggered when the MQTT client connects to the broker.
- **`on_message(client, userdata, msg)`**: Callback triggered when a message is received from the broker.
- **`start_mqtt_listener()`**: Initializes the MQTT client and starts the listener loop.

## main.py

- **`main()`**: Main entry point for the dfs3 system.

## tests/test_validation.py

- **`test_valid_mqtt_event()`**: Test that a fully valid MQTT message is accepted.
- **`test_invalid_mqtt_event_missing_field()`**: Test that an MQTT message missing required fields is rejected.
- **`test_invalid_mqtt_event_bad_format()`**: Test that an MQTT message with invalid SHA-256 or event type is rejected.
- **`test_valid_event_json()`**: Test that a fully valid dfs3 event JSON is accepted.
- **`test_invalid_event_json_missing_field()`**: Test that a dfs3 event JSON missing required fields is rejected.
- **`test_invalid_event_json_bad_origin()`**: Test that a dfs3 event JSON with invalid origin format is rejected.

