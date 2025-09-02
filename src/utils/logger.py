"""日志工具模块"""

import os
import sys
from loguru import logger
from ..config.settings import settings

# 确保日志目录存在
log_dir = os.path.dirname(settings.logging.log_file)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

# 移除默认处理器
logger.remove()

# 添加控制台处理器
logger.add(
    sys.stdout,
    format=settings.logging.log_format,
    level=settings.logging.log_level,
    colorize=True
)

# 添加文件处理器
logger.add(
    settings.logging.log_file,
    format=settings.logging.log_format,
    level=settings.logging.log_level,
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8"
)


def get_logger(name: str = None):
    """获取logger实例"""
    if name:
        return logger.bind(name=name)
    return logger