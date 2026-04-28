# geg_logger/__init__.py
from .logger import Logger, _Logger

__version__ = "1.0.0"
__all__ = ["Logger", "_Logger"]


# Удобная функция для быстрого создания логгера
def get_logger(name: str) -> Logger:
    """Быстрое создание логгера"""
    return Logger(name)
