"""
核心模块
包含配置加载、消息协议、队列管理、日志、指标
"""
from .config import Config, ServiceConfig, config, setup_logging
from .messages import (
    Message,
    SensorData,
    EnvSensorData,
    PhSensorData,
    AgingPredictionRequest,
    AgingPredictionResult,
    MoldPredictionRequest,
    MoldPredictionResult,
    AlertMessage,
    ClickHouseRecord,
    ControlMessage,
    deserialize_message,
    serialize_message,
)
from .queue_manager import (
    QueueManager,
    AsyncQueueWrapper,
    ProcessQueueWrapper,
    QueueStats,
    queue_manager,
)
from .logging_setup import setup_loguru_logging, get_logger, JsonFormatter
from .metrics import MetricsManager, metrics

__all__ = [
    "Config",
    "ServiceConfig",
    "config",
    "setup_logging",
    "Message",
    "SensorData",
    "EnvSensorData",
    "PhSensorData",
    "AgingPredictionRequest",
    "AgingPredictionResult",
    "MoldPredictionRequest",
    "MoldPredictionResult",
    "AlertMessage",
    "ClickHouseRecord",
    "ControlMessage",
    "deserialize_message",
    "serialize_message",
    "QueueManager",
    "AsyncQueueWrapper",
    "ProcessQueueWrapper",
    "QueueStats",
    "queue_manager",
    "setup_loguru_logging",
    "get_logger",
    "JsonFormatter",
    "MetricsManager",
    "metrics",
]
