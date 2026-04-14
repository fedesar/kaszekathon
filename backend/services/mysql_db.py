"""Helpers to connect to the Leanmote MySQL database using IAM authentication."""

from __future__ import annotations

import os
import time
from typing import Any, Optional, Sequence

import threading

import boto3
import pymysql

from .logging_utils import log_json

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

_local = threading.local()
_MAX_TOKEN_LIFETIME_SECONDS = 14 * 60


def get_connection():
    now = time.time()
    conn = getattr(_local, "connection", None)
    token_time = getattr(_local, "token_creation_time", 0.0)

    if conn is not None and (now - token_time) < _MAX_TOKEN_LIFETIME_SECONDS:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            _local.connection = None

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

    _local.token_creation_time = now
    _local.connection = pymysql.connect(
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
    return _local.connection


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
