def row_to_dict(cursor, row: tuple) -> dict:
    """
    Converts a database row and its cursor into a dictionary mapping column names to values.

    Args:
        cursor: The SQLite cursor after executing a query.
        row: A single row result as a tuple.

    Returns:
        A dictionary with column names as keys and row values as values.
    """
    if not row:
        return {}

    col_names = [desc[0] for desc in cursor.description]
    return dict(zip(col_names, row))


