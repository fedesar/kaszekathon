"""Helpers to connect to the Leanmote MySQL database using IAM authentication."""

from __future__ import annotations

import os
import time
from typing import Any, Optional, Sequence

import boto3
import pymysql

from .logging_utils import log_json

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

_CONNECTION = None
_TOKEN_CREATION_TIME = 0.0
_MAX_TOKEN_LIFETIME_SECONDS = 14 * 60


def get_connection():
    global _CONNECTION, _TOKEN_CREATION_TIME

    now = time.time()
    if _CONNECTION is not None and (now - _TOKEN_CREATION_TIME) < _MAX_TOKEN_LIFETIME_SECONDS:
        try:
            with _CONNECTION.cursor() as cursor:
                cursor.execute("SELECT 1")
            return _CONNECTION
        except Exception:
            try:
                _CONNECTION.close()
            except Exception:
                pass
            _CONNECTION = None

    db_host = os.environ["LEANMOTE_DB_HOST"]
    db_user = os.environ["LEANMOTE_DB_USER"]
    db_name = os.environ["LEANMOTE_DB_NAME"]
    db_port = int(os.environ.get("LEANMOTE_DB_PORT", "3306"))
    region = os.environ.get("LEANMOTE_AWS_REGION", "us-east-1")

    log_json(
        "info",
        "database",
        "Opening MySQL connection",
        status="success",
        extra={"database": db_name},
    )

    password = os.environ.get("LEANMOTE_DB_PASSWORD")
    if password is None:
        session = boto3.Session(region_name=region)
        rds_client = session.client("rds", region_name=region)
        password = rds_client.generate_db_auth_token(DBHostname=db_host, Port=db_port, DBUsername=db_user)

    _TOKEN_CREATION_TIME = now
    _CONNECTION = pymysql.connect(
        host=db_host,
        user=db_user,
        password=password,
        database=db_name,
        port=db_port,
        connect_timeout=5,
        ssl={"ssl": {}},
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    return _CONNECTION


def db_fetch(sql: str, params: Optional[Sequence[Any]] = None):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def db_get(sql: str, params: Optional[Sequence[Any]] = None):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone()


def db_execute(sql: str, params: Optional[Sequence[Any]] = None):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.lastrowid


__all__ = ["db_fetch", "db_get", "db_execute", "get_connection"]
