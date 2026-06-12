"""
ClickHouse 数据库连接与操作封装
"""
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from clickhouse_driver import Client
from clickhouse_connect import get_client
from clickhouse_connect.driver.exceptions import ClickHouseError

from .config import settings

logger = logging.getLogger(__name__)


class ClickHouseManager:
    _instance: Optional["ClickHouseManager"] = None
    _client: Optional[Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            self._client = get_client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                username=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=settings.clickhouse_database,
                settings={"insert_deduplicate": 0},
            )
            logger.info(f"ClickHouse connected: {settings.clickhouse_host}:{settings.clickhouse_port}")
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            raise

    @property
    def client(self):
        if self._client is None:
            self._connect()
        return self._client

    def reconnect(self):
        self.close()
        self._connect()

    def close(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        try:
            result = self.client.query(sql, parameters=params or {})
            columns = [col[0] for col in result.result_columns]
            return [dict(zip(columns, row)) for row in result.result_rows]
        except ClickHouseError as e:
            logger.error(f"ClickHouse query error: {e}, SQL: {sql}")
            self.reconnect()
            raise

    def query_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, table: str, data: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        if not data:
            return
        try:
            cols = columns or list(data[0].keys())
            rows = [[row[c] for c in cols] for row in data]
            self.client.insert(table, rows, column_names=cols)
            logger.debug(f"Inserted {len(data)} rows into {table}")
        except ClickHouseError as e:
            logger.error(f"ClickHouse insert error into {table}: {e}")
            raise

    def execute(self, sql: str, params: Optional[Dict] = None) -> int:
        try:
            return self.client.command(sql, parameters=params or {})
        except ClickHouseError as e:
            logger.error(f"ClickHouse execute error: {e}, SQL: {sql}")
            raise


class BatchWriter:
    def __init__(
        self,
        ch_manager: ClickHouseManager,
        batch_size: int = 500,
        flush_interval: float = 30.0,
    ):
        self._ch = ch_manager
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._timer_thread: Optional[threading.Thread] = None

    def add(self, table: str, rows: List[Dict[str, Any]], columns: Optional[List[str]] = None):
        if not rows:
            return
        with self._lock:
            if table not in self._buffer:
                self._buffer[table] = {"rows": [], "columns": columns}
            entry = self._buffer[table]
            entry["rows"].extend(rows)
            if columns and not entry["columns"]:
                entry["columns"] = columns
            if len(entry["rows"]) >= self._batch_size:
                self._flush_table(table)

    def _flush_table(self, table: str):
        entry = self._buffer.pop(table, None)
        if not entry or not entry["rows"]:
            return
        try:
            self._ch.insert(table, entry["rows"], entry.get("columns"))
            logger.info(f"BatchWriter flushed {len(entry['rows'])} rows to {table}")
        except Exception as e:
            logger.error(f"BatchWriter flush error for {table}: {e}")

    def flush_all(self):
        with self._lock:
            tables = list(self._buffer.keys())
        for table in tables:
            with self._lock:
                self._flush_table(table)

    def _timer_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(self._flush_interval)
            if self._stop_event.is_set():
                break
            self.flush_all()
        self.flush_all()

    def start(self):
        if self._timer_thread and self._timer_thread.is_alive():
            return
        self._timer_thread = threading.Thread(
            target=self._timer_loop, daemon=True, name="ch-batch-writer"
        )
        self._timer_thread.start()
        logger.info(f"BatchWriter started: batch_size={self._batch_size}, flush_interval={self._flush_interval}s")

    def stop(self):
        self._stop_event.set()
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=15)
        self.flush_all()
        logger.info("BatchWriter stopped")


def get_ch() -> ClickHouseManager:
    return ClickHouseManager()
