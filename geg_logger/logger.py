"""
Модуль логирования для проекта AutoGenInstall2 с поддержрой .exe режима
Автоматическое использование имени логгера как module_name
"""

import json
import logging
import sys
import traceback

from datetime import datetime
from pathlib import Path
from typing import Any


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер для логирования с поддержкой module_name"""

    def format(self, record: logging.LogRecord) -> str:
        """
        Форматирование записи лога

        Args:
            record: Запись лога

        Returns:
            Отформатированная строка лога
        """
        # Используем module_name из extra, если он есть, иначе используем name
        module_name = getattr(record, "module_name", None) or record.name

        # Форматируем время
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y:%m:%d %H:%M:%S")

        # Форматируем уровень логирования
        level_name = record.levelname

        # Формируем строку лога: [YYYY:MM:DD HH:MM:SS] [module.name] [Log.Level] - [message]
        log_message = (
            f"[{timestamp}] [{module_name}] [{level_name}] - {record.getMessage()}"
        )

        # Добавляем stacktrace, если он есть в записи
        if hasattr(record, "stacktrace") and record.stacktrace:
            log_message += f"\nStacktrace:\n{record.stacktrace}"

        return log_message


def _get_appsettings_path() -> Path:
    """
    Получить правильный путь к appsettings.json
    Приоритет: текущая директория > директория .exe > домашняя директория
    """
    # 1. В текущей рабочей директории (самый важный приоритет)
    cwd_path = Path.cwd() / "appsettings.json"
    if cwd_path.exists():
        return cwd_path.resolve()
    
    # 2. Проверяем, запущены ли мы в .exe режиме
    if getattr(sys, "frozen", False):
        # Режим .exe - рядом с .exe файлом
        exe_dir = Path(sys.executable).parent
        exe_path = exe_dir / "appsettings.json"
        if exe_path.exists():
            return exe_path.resolve()
        
        # Временная папка PyInstaller
        if hasattr(sys, "_MEIPASS"):
            meipass_path = Path(sys._MEIPASS) / "appsettings.json"
            if meipass_path.exists():
                return meipass_path.resolve()
    
    # 3. В директории проекта (ищем pyproject.toml или .git как маркеры)
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        markers = ["pyproject.toml", ".git", "setup.py", "requirements.txt"]
        if any((parent / marker).exists() for marker in markers):
            project_path = parent / "appsettings.json"
            if project_path.exists():
                return project_path.resolve()
            break
    
    # 4. В домашней директории пользователя
    home_path = Path.home() / ".my_logger" / "appsettings.json"
    if home_path.exists():
        return home_path.resolve()
    
    # 5. Возвращаем путь в текущей директории (даже если файла нет - создадим)
    return Path.cwd() / "appsettings.json"


def _get_log_directory() -> Path:
    """
    Получить правильную директорию для логов
    """
    if getattr(sys, "frozen", False):
        # Режим .exe - логи рядом с .exe файлом
        exe_dir = Path(sys.executable).parent
        log_dir = exe_dir / "logs"
    else:
        # Режим разработки - логи в текущей рабочей директории
        log_dir = Path.cwd() / "logs"

    # Создаем директорию, если её нет
    log_dir.mkdir(exist_ok=True)
    return log_dir


class _Logger:
    """Базовый класс для логирования"""

    # Настройки логирования (загружаются из appsettings.json)
    _logging_config: dict[str, Any] | None = None
    _log_level: int = logging.INFO
    _can_file_write: bool = True
    _can_terminal_write: bool = True
    _include_stacktrace: bool = True

    @classmethod
    def _load_config(cls) -> dict[str, Any]:
        """Загрузка настроек логирования из appsettings.json"""
        if cls._logging_config is not None:
            return cls._logging_config

        config_path = _get_appsettings_path()

        default_config = {
            "level": "INFO",
            "canFileWrite": True,
            "canTerminalWrite": True,
            "includeStacktrace": True,
        }

        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config_data = json.load(f)
                    logging_config = config_data.get("logging", default_config)

                print(f"[LOGGER] Загружаем настройки из: {config_path}")
            else:
                logging_config = default_config
                print(
                    f"[LOGGER] Файл настроек не найден: {config_path}. Используем значения по умолчанию.",
                )

                try:
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {"logging": default_config},
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )
                    print(f"[LOGGER] Создан файл настроек по умолчанию: {config_path}")
                except Exception as e:
                    print(f"[LOGGER] Не удалось создать файл настроек: {e}")

            cls._logging_config = logging_config

            level_str = logging_config.get("level", "INFO").upper()
            level_mapping = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }
            cls._log_level = level_mapping.get(level_str, logging.INFO)
            cls._can_file_write = logging_config.get("canFileWrite", True)
            cls._can_terminal_write = logging_config.get("canTerminalWrite", True)
            cls._include_stacktrace = logging_config.get("includeStacktrace", True)

            print(f"[LOGGER] Уровень логирования: {level_str} ({cls._log_level})")
            print(f"[LOGGER] Логи в файл: {cls._can_file_write}")
            print(f"[LOGGER] Логи в консоль: {cls._can_terminal_write}")
            print(f"[LOGGER] Включить stacktrace для ошибок: {cls._include_stacktrace}")

        except json.JSONDecodeError as e:
            print(f"[LOGGER] ОШИБКА: Неверный формат JSON в {config_path}: {e}")
            cls._logging_config = default_config
            cls._log_level = logging.INFO
            cls._can_file_write = True
            cls._can_terminal_write = True
            cls._include_stacktrace = True
        except Exception as e:
            print(
                f"[LOGGER] Ошибка загрузки настроек логирования: {e}. Используем значения по умолчанию.",
            )
            cls._logging_config = default_config
            cls._log_level = logging.INFO
            cls._can_file_write = True
            cls._can_terminal_write = True
            cls._include_stacktrace = True

        return cls._logging_config

    def __init__(self, name: str, log_file_prefix: str):
        """
        Инициализация логгера

        Args:
            name: Имя логгера (будет использоваться как module_name в логах)
            log_file_prefix: Префикс для имени файла лога (app или gui)
        """
        # Загружаем настройки при первом использовании
        self._load_config()

        self.name = name
        self.log_file_prefix = log_file_prefix
        self.logger = logging.getLogger(name)

        # Устанавливаем уровень логирования из настроек
        self.logger.setLevel(self._log_level)

        # Запрещаем изменение уровня логирования

        def protected_set_level(level):
            pass  # Игнорируем попытки изменения уровня

        self.logger.setLevel = protected_set_level

        # Очищаем существующие обработчики
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Получаем правильную директорию для логов
        self.log_dir = _get_log_directory()

        # Настраиваем кастомный форматтер
        self.formatter = CustomFormatter()

        # Обработчик для консоли (если разрешено)
        if self._can_terminal_write:
            self._setup_console_handler()

        # Обработчик для файла (если разрешено)
        if self._can_file_write:
            self._setup_file_handler()

    def _setup_console_handler(self):
        """Настройка обработчика для вывода в консоль"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._log_level)
        console_handler.setFormatter(self.formatter)

        def protected_handler_set_level(level):
            pass

        console_handler.setLevel = protected_handler_set_level

        self.logger.addHandler(console_handler)

    def _setup_file_handler(self):
        """Настройка обработчика для вывода в файл"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_filename = f"{self.log_file_prefix}_{today}.log"
            log_file_path = self.log_dir / log_filename

            file_handler = logging.FileHandler(
                log_file_path,
                encoding="utf-8",
                mode="a",
            )
            file_handler.setLevel(self._log_level)
            file_handler.setFormatter(self.formatter)

            def protected_handler_set_level(level):
                pass

            file_handler.setLevel = protected_handler_set_level

            self.logger.addHandler(file_handler)

        except Exception as e:
            print(f"[LOGGER] ОШИБКА при создании файлового обработчика: {e}")
            try:
                backup_log_path = Path.cwd() / f"{self.log_file_prefix}_backup.log"
                file_handler = logging.FileHandler(
                    backup_log_path,
                    encoding="utf-8",
                    mode="a",
                )
                file_handler.setLevel(self._log_level)
                file_handler.setFormatter(self.formatter)
                self.logger.addHandler(file_handler)
            except Exception as e2:
                print(f"[LOGGER] Не удалось создать даже резервный лог: {e2}")

    def debug(self, message: str):
        """Логирование уровня DEBUG - автоматически использует имя логгера как module_name"""
        extra = {"module_name": self.name}
        self.logger.debug(message, extra=extra)

    def info(self, message: str):
        """Логирование уровня INFO - автоматически использует имя логгера как module_name"""
        extra = {"module_name": self.name}
        self.logger.info(message, extra=extra)

    def warning(self, message: str):
        """Логирование уровня WARNING - автоматически использует имя логгера как module_name"""
        extra = {"module_name": self.name}
        self.logger.warning(message, extra=extra)

    def error(self, message: str, exc_info: bool | Exception = None):
        """
        Логирование уровня ERROR - автоматически использует имя логгера как module_name
        Stacktrace добавляется автоматически, если он доступен.

        Args:
            message: Сообщение для логирования
            exc_info: Информация об исключении (опционально)
        """
        extra = {"module_name": self.name}

        # Если exc_info не указан, проверяем наличие активного исключения
        exc_info = bool(exc_info is None and sys.exc_info()[0] is not None)

        # Добавляем stacktrace для ошибок, если это разрешено в настройках
        if self._include_stacktrace and exc_info:
            if exc_info is True:
                stacktrace_str = traceback.format_exc()
                if stacktrace_str and stacktrace_str != "NoneType: None\n":
                    extra["stacktrace"] = stacktrace_str
                    self.logger.error(message, extra=extra)
                    return
            elif isinstance(exc_info, Exception):
                stacktrace_str = "".join(
                    traceback.format_exception(
                        type(exc_info),
                        exc_info,
                        exc_info.__traceback__,
                    ),
                )
                extra["stacktrace"] = stacktrace_str
                self.logger.error(message, extra=extra)
                return
            elif exc_info:
                self.logger.error(message, extra=extra, exc_info=True)
                return

        self.logger.error(message, extra=extra)

    def critical(self, message: str, exc_info: bool | Exception = None):
        """
        Логирование уровня CRITICAL - автоматически использует имя логгера как module_name
        Stacktrace добавляется автоматически, если он доступен.

        Args:
            message: Сообщение для логирования
            exc_info: Информация об исключении (опционально)
        """
        extra = {"module_name": self.name}

        # Если exc_info не указан, проверяем наличие активного исключения
        if exc_info is None:
            exc_info = sys.exc_info()[0] is not None

        # Добавляем stacktrace для ошибок, если это разрешено в настройках
        if self._include_stacktrace and exc_info:
            if exc_info is True:
                stacktrace_str = traceback.format_exc()
                if stacktrace_str and stacktrace_str != "NoneType: None\n":
                    extra["stacktrace"] = stacktrace_str
                    self.logger.critical(message, extra=extra)
                    return
            elif isinstance(exc_info, Exception):
                stacktrace_str = "".join(
                    traceback.format_exception(
                        type(exc_info),
                        exc_info,
                        exc_info.__traceback__,
                    ),
                )
                extra["stacktrace"] = stacktrace_str
                self.logger.critical(message, extra=extra)
                return
            elif exc_info:
                self.logger.critical(message, extra=extra, exc_info=True)
                return

        self.logger.critical(message, extra=extra)

    def exception(self, message: str):
        """
        Логирование исключения с уровнем ERROR - автоматически использует имя логгера как module_name
        Этот метод всегда добавляет полный stacktrace текущего исключения.

        Args:
            message: Сообщение для логирования
        """
        extra = {"module_name": self.name}
        self.logger.error(message, extra=extra, exc_info=True)


class Logger(_Logger):
    """Глобальный логгер"""

    def __init__(self, name: str):
        """
        Инициализация логгера

        Args:
            name: Имя модуля (будет отображаться в логах как module_name)
        """
        super().__init__(name, "app")