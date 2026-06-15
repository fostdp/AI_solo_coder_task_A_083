import sys
import json
from typing import Any, Dict
from loguru import logger


class JsonFormatter:
    """JSON格式日志格式化器"""

    def __init__(self, service_name: str = "ancient-books-monitor"):
        self.service_name = service_name

    def format(self, record: Dict[str, Any]) -> str:
        log_record = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "service": self.service_name,
            "message": record["message"],
            "module": record.get("module", ""),
            "function": record.get("function", ""),
            "line": record.get("line", 0),
            "process": record.get("process", {}).get("id", 0),
            "thread": record.get("thread", {}).get("id", 0),
        }

        if record.get("extra"):
            for key, value in record["extra"].items():
                if key not in log_record:
                    log_record[key] = value

        if record.get("exception"):
            log_record["exception"] = str(record["exception"])

        return json.dumps(log_record, ensure_ascii=False) + "\n"


def setup_loguru_logging(config=None, service_name: str = "ancient-books-monitor",
                         log_level: str = "INFO", json_output: bool = None):
    """
    配置loguru日志系统

    Args:
        config: 配置对象
        service_name: 服务名称
        log_level: 日志级别
        json_output: 是否输出JSON格式，默认从环境变量LOG_JSON获取
    """
    if json_output is None:
        import os
        json_output = os.getenv("LOG_JSON", "true").lower() == "true"

    if config is not None:
        service_name = config.service.name
        log_level = config.service.log_level

    logger.remove()

    if json_output:
        formatter = JsonFormatter(service_name)
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format=formatter.format,
            serialize=False,
            enqueue=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=log_level.upper(),
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            enqueue=True,
        )

    logger.info(f"日志系统初始化完成 - 级别: {log_level}, JSON输出: {json_output}")

    return logger


def get_logger(name: str = None):
    """获取logger实例"""
    if name:
        return logger.bind(module=name)
    return logger
