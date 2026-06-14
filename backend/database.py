import logging
import requests
from typing import List, Dict, Any, Optional
from .config import settings

logger = logging.getLogger(__name__)

class ClickHouseClient:
    def __init__(self):
        self._base_url = f"http://{settings.clickhouse_host}:{settings.clickhouse_port}"
        self._db = settings.clickhouse_database
        self._params = {
            "user": settings.clickhouse_user,
            "password": settings.clickhouse_password,
            "database": self._db,
        }

    def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        formatted_sql = self._format_query(sql, params)
        formatted_sql += " FORMAT JSON"
        try:
            resp = requests.post(
                self._base_url, data=formatted_sql.encode("utf-8"), params=self._params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"ClickHouse query error: {e}")
            return []

    def query_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Optional[Dict] = None) -> bool:
        formatted_sql = self._format_query(sql, params)
        try:
            resp = requests.post(
                self._base_url, data=formatted_sql.encode("utf-8"), params=self._params, timeout=15
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"ClickHouse execute error: {e}")
            return False

    def batch_insert(self, table: str, columns: List[str], rows: List[List[Any]]) -> bool:
        if not rows:
            return True
        col_def = ", ".join(columns)
        csv_lines = "\n".join(",".join(str(v) for v in row) for row in rows)
        sql = f"INSERT INTO {table} ({col_def}) FORMAT CSV"
        try:
            resp = requests.post(
                self._base_url, data=csv_lines.encode("utf-8"), params=self._params, timeout=30
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"ClickHouse batch insert error: {e}")
            return False

    def _format_query(self, sql: str, params: Optional[Dict] = None) -> str:
        if not params:
            return sql
        result = sql
        for k, v in params.items():
            placeholder = "{" + k + ":String}"
            if placeholder in result:
                result = result.replace(placeholder, f"'{v}'")
            placeholder_int = "{" + k + ":Int64}"
            if placeholder_int in result:
                result = result.replace(placeholder_int, str(v))
            placeholder_dt = "{" + k + ":DateTime64(3)}"
            if placeholder_dt in result:
                result = result.replace(placeholder_dt, f"'{v}'")
        return result

_ch_client: Optional[ClickHouseClient] = None

def get_ch() -> ClickHouseClient:
    global _ch_client
    if _ch_client is None:
        _ch_client = ClickHouseClient()
    return _ch_client
