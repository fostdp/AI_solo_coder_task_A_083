from typing import Dict, Any
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


class MetricsManager:
    """Prometheus指标管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        """初始化所有指标"""

        self.ingest_messages_total = Counter(
            'ingest_messages_total',
            'Total number of messages ingested from MQTT',
            ['sensor_type', 'status']
        )

        self.ingest_errors_total = Counter(
            'ingest_errors_total',
            'Total number of ingestion errors',
            ['error_type']
        )

        self.queue_length = Gauge(
            'queue_length',
            'Current queue length',
            ['queue_name']
        )

        self.queue_dropped_total = Counter(
            'queue_dropped_total',
            'Total number of dropped messages from queues',
            ['queue_name']
        )

        self.batch_writer_batch_size = Histogram(
            'batch_writer_batch_size',
            'Batch size of ClickHouse writes',
            ['table_name'],
            buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000]
        )

        self.batch_writer_flushes_total = Counter(
            'batch_writer_flushes_total',
            'Total number of batch flushes',
            ['table_name', 'reason']
        )

        self.batch_writer_write_duration = Histogram(
            'batch_writer_write_duration_seconds',
            'Duration of ClickHouse write operations',
            ['table_name'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )

        self.aging_engine_predictions_total = Counter(
            'aging_engine_predictions_total',
            'Total number of aging predictions',
            ['status']
        )

        self.aging_engine_duration = Histogram(
            'aging_engine_duration_seconds',
            'Duration of aging prediction calculations',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )

        self.mold_engine_calculations_total = Counter(
            'mold_engine_calculations_total',
            'Total number of mold risk calculations',
            ['status']
        )

        self.alerts_total = Counter(
            'alerts_total',
            'Total number of alerts generated',
            ['level', 'type']
        )

        self.alerts_deduped_total = Counter(
            'alerts_deduped_total',
            'Total number of deduplicated alerts',
            ['level']
        )

        self.websocket_connections = Gauge(
            'websocket_connections',
            'Current number of WebSocket connections'
        )

        self.api_requests_total = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code']
        )

        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'Duration of API requests',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )

        self.clickhouse_connected = Gauge(
            'clickhouse_connected',
            'ClickHouse connection status (1=connected, 0=disconnected)'
        )

        self.mqtt_connected = Gauge(
            'mqtt_connected',
            'MQTT connection status (1=connected, 0=disconnected)'
        )

        self.system_running = Gauge(
            'system_running',
            'System running status (1=running, 0=stopped)'
        )

    def record_ingest_message(self, sensor_type: str, status: str = "success"):
        """记录摄取消息计数"""
        self.ingest_messages_total.labels(sensor_type=sensor_type, status=status).inc()

    def record_ingest_error(self, error_type: str):
        """记录摄取错误"""
        self.ingest_errors_total.labels(error_type=error_type).inc()

    def set_queue_length(self, queue_name: str, length: int):
        """设置队列长度"""
        self.queue_length.labels(queue_name=queue_name).set(length)

    def record_queue_dropped(self, queue_name: str, count: int = 1):
        """记录队列丢弃消息"""
        self.queue_dropped_total.labels(queue_name=queue_name).inc(count)

    def observe_batch_size(self, table_name: str, size: int):
        """观察批大小"""
        self.batch_writer_batch_size.labels(table_name=table_name).observe(size)

    def record_batch_flush(self, table_name: str, reason: str = "size"):
        """记录批次刷新"""
        self.batch_writer_flushes_total.labels(table_name=table_name, reason=reason).inc()

    def observe_write_duration(self, table_name: str, duration: float):
        """观察写入持续时间"""
        self.batch_writer_write_duration.labels(table_name=table_name).observe(duration)

    def record_aging_prediction(self, status: str = "success"):
        """记录老化预测"""
        self.aging_engine_predictions_total.labels(status=status).inc()

    def observe_aging_duration(self, duration: float):
        """观察老化计算持续时间"""
        self.aging_engine_duration.observe(duration)

    def record_mold_calculation(self, status: str = "success"):
        """记录霉菌计算"""
        self.mold_engine_calculations_total.labels(status=status).inc()

    def record_alert(self, level: str, alert_type: str):
        """记录告警"""
        self.alerts_total.labels(level=level, type=alert_type).inc()

    def record_alert_deduped(self, level: str):
        """记录去重告警"""
        self.alerts_deduped_total.labels(level=level).inc()

    def set_websocket_connections(self, count: int):
        """设置WebSocket连接数"""
        self.websocket_connections.set(count)

    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录API请求"""
        self.api_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
        self.api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    def set_clickhouse_connected(self, connected: bool):
        """设置ClickHouse连接状态"""
        self.clickhouse_connected.set(1 if connected else 0)

    def set_mqtt_connected(self, connected: bool):
        """设置MQTT连接状态"""
        self.mqtt_connected.set(1 if connected else 0)

    def set_system_running(self, running: bool):
        """设置系统运行状态"""
        self.system_running.set(1 if running else 0)

    def get_latest_metrics(self) -> bytes:
        """获取最新的指标数据"""
        return generate_latest()

    def get_content_type(self) -> str:
        """获取指标内容类型"""
        return CONTENT_TYPE_LATEST


metrics = MetricsManager()
