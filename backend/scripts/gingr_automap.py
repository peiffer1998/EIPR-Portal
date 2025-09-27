"""Automap Gingr MySQL schema into a YAML mapping for the importer."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pymysql
import yaml

LOGGER = logging.getLogger("gingr_automap")

TARGETS: dict[str, list[str]] = {
    "owners": ["owner", "customer", "client", "parent"],
    "pets": ["pet", "animal", "dog", "cat"],
    "immunizations": ["immun", "vacc", "shot"],
    "reservations": ["reservation", "booking", "appt", "appointment", "lodging"],
    "invoices": ["invoice", "billing", "pos_transaction", "pos", "sale"],
    "payments": ["payment", "transaction"],
    "packages": ["package", "pass", "membership"],
    "credits": ["credit", "gift", "certificate", "store"],
}

FIELD_HINTS: dict[str, dict[str, list[str]]] = {
    "owners": {
        "id": ["id", "customer"],
        "first_name": ["first", "fname"],
        "last_name": ["last", "lname", "surname"],
        "email": ["email"],
        "phone": ["phone", "mobile", "cell"],
        "created_at": ["created", "joined", "added", "date"],
        "updated_at": ["updated", "modified", "changed"],
    },
    "pets": {
        "id": ["id", "pet", "animal"],
        "owner_id": ["owner", "customer", "client"],
        "name": ["name"],
        "species": ["species", "type", "animal"],
        "breed": ["breed"],
        "color": ["color"],
        "dob": ["dob", "birth", "born"],
        "updated_at": ["updated", "modified"],
    },
    "immunizations": {
        "id": ["id"],
        "pet_id": ["pet", "animal"],
        "vaccine": ["vacc", "immun"],
        "issued_on": ["issue", "admin", "given"],
        "expires_on": ["expire", "due"],
        "status": ["status", "state"],
    },
    "reservations": {
        "id": ["id", "reservation", "booking"],
        "pet_id": ["pet", "animal"],
        "start_at": ["start", "check_in", "begin"],
        "end_at": ["end", "check_out", "finish"],
        "status": ["status", "state"],
        "type": ["type", "service"],
        "location_id": ["location", "facility", "site"],
        "notes": ["note", "comment"],
        "updated_at": ["updated", "modified"],
    },
    "invoices": {
        "id": ["id", "invoice"],
        "reservation_id": ["reservation", "booking"],
        "total": ["total", "amount", "due"],
        "balance": ["balance", "due"],
        "status": ["status", "state"],
        "created_at": ["created", "date"],
        "updated_at": ["updated", "modified"],
    },
    "payments": {
        "id": ["id", "payment", "transaction"],
        "invoice_id": ["invoice", "reservation"],
        "amount": ["amount", "total", "paid"],
        "status": ["status", "state", "result"],
        "method": ["method", "type", "source"],
        "processed_at": ["processed", "posted", "date"],
    },
    "packages": {
        "id": ["id", "package", "membership"],
        "owner_id": ["owner", "customer"],
        "credits": ["credit", "remaining", "balance"],
        "name": ["name", "package"],
        "updated_at": ["updated", "modified"],
    },
    "credits": {
        "id": ["id", "gift", "credit"],
        "owner_id": ["owner", "customer"],
        "code": ["code", "number"],
        "value": ["value", "amount", "total"],
        "balance": ["remain", "balance"],
        "created_at": ["created", "issued"],
    },
}


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOGGER.addHandler(console)


def get_connection() -> pymysql.connections.Connection:
    host = os.environ.get("GINGR_MYSQL_HOST", "127.0.0.1")
    port = int(os.environ.get("GINGR_MYSQL_PORT", "3307"))
    db = os.environ.get("GINGR_MYSQL_DB", "gingr")
    user = os.environ.get("GINGR_MYSQL_USER", "root")
    password = os.environ.get("GINGR_MYSQL_PASSWORD", "rootpass")
    LOGGER.info("Connecting to MySQL %s:%s/%s", host, port, db)
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
    )


def fetch_tables(cur: pymysql.cursors.Cursor, database: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT TABLE_NAME as table_name, TABLE_ROWS as table_rows
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
        """,
        (database,),
    )
    return list(cur.fetchall())


def fetch_columns(
    cur: pymysql.cursors.Cursor, database: str, table: str
) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT COLUMN_NAME as column_name, DATA_TYPE as data_type, COLUMN_KEY as column_key
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """,
        (database, table),
    )
    return list(cur.fetchall())


def score_table(table_name: str, tokens: Iterable[str]) -> float:
    """Return a relative score for how well a table name matches a target token list."""

    lowered = table_name.lower()
    score: float = 0.0
    for token in tokens:
        token = token.lower()
        if lowered == token or lowered == f"{token}s":
            score += 200.0
        elif lowered.startswith(f"{token}_") or lowered.endswith(f"_{token}"):
            score += 25.0
        elif token in lowered:
            score += 5.0

    # Prefer shorter names when scores tie (e.g., ``owners`` over ``owner_files``).
    score -= len(lowered) * 0.01
    return score


def best_table(tables: list[dict[str, Any]], target: str) -> Optional[dict[str, Any]]:
    candidates = TARGETS.get(target, [])
    best: Optional[dict[str, Any]] = None
    best_score = -1.0
    for table in tables:
        score = score_table(table["table_name"], candidates)
        # add heuristic weight for row count
        rows = table["table_rows"] or 0
        score += min(rows, 1_000_000) / 1_000_000  # small fractional weight
        if score > best_score:
            best_score = score
            best = table
    return best


def guess_column(columns: list[dict[str, Any]], hints: list[str]) -> Optional[str]:
    """Choose the best-fitting column for a logical field."""

    lowered_hints = [h.lower() for h in hints]
    best_name: Optional[str] = None
    best_score = -1.0
    for column in columns:
        name = column["column_name"]
        lname = name.lower()
        column_key = (column.get("column_key") or "").lower()

        score = 0.0
        for hint in lowered_hints:
            if lname == hint or lname == f"{hint}_id" or lname == f"{hint}s":
                score += 200.0
            elif lname.startswith(f"{hint}_") or lname.endswith(f"_{hint}"):
                score += 25.0
            elif hint in lname:
                score += len(hint)

        if column_key == "pri" and any(
            h == "id" or h.endswith("_id") for h in lowered_hints
        ):
            score += 100.0

        if score > best_score:
            best_score = score
            best_name = name

    return best_name


def build_mapping(
    conn: pymysql.connections.Connection,
    database: str,
) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    with conn.cursor() as cur:
        tables = fetch_tables(cur, database)
        table_lookup: Dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            table_name = table["table_name"]
            table_lookup[table_name] = fetch_columns(cur, database, table_name)

        for target in TARGETS:
            choice = best_table(tables, target)
            if not choice:
                LOGGER.warning("No table candidate found for %s", target)
                continue
            table_name = choice["table_name"]
            columns = table_lookup.get(table_name, [])
            field_hints = FIELD_HINTS.get(target, {})
            selected_columns: Dict[str, Optional[str]] = {}
            for field, hints in field_hints.items():
                hint_list = list(hints)
                lowered_existing = [h.lower() for h in hint_list]
                if field.lower() not in lowered_existing:
                    hint_list = [field] + hint_list
                selected_columns[field] = guess_column(columns, hint_list)

            mapping[target] = {
                "table": table_name,
                "row_count": choice.get("table_rows", 0) or 0,
                "columns": selected_columns,
            }
            LOGGER.info(
                "Target %s -> table %s (rows=%s)",
                target,
                table_name,
                choice.get("table_rows", 0),
            )
            LOGGER.debug("Column mapping: %s", selected_columns)
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Automap Gingr schema to YAML")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("backend/scripts/gingr_mapping.yaml"),
        help="Path to write the mapping YAML file.",
    )
    args = parser.parse_args()

    log_path = Path("imports/automap.log")
    configure_logging(log_path)

    database = os.environ.get("GINGR_MYSQL_DB", "gingr")
    try:
        conn = get_connection()
    except Exception as exc:  # pragma: no cover - connection errors
        LOGGER.error("Failed to connect to MySQL: %s", exc)
        raise SystemExit(2) from exc

    try:
        mapping = build_mapping(conn, database)
    finally:
        conn.close()

    args.mapping.parent.mkdir(parents=True, exist_ok=True)
    with args.mapping.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(mapping, fh, sort_keys=True)
    LOGGER.info("Wrote mapping to %s", args.mapping)


if __name__ == "__main__":
    main()
