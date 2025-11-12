"""
Модуль конфигурации для утилиты сравнения логов сборки.

Предоставляет структуры данных и функции для загрузки и валидации конфигурации.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import yaml
import re
import os


class ConfigValidationError(Exception):
    """Исключение для ошибок валидации конфигурации."""

    pass


@dataclass
class TargetStep:
    """Целевой этап сборки для анализа."""

    pattern: str
    name: str


@dataclass
class Config:
    """
    Конфигурация для парсинга и сравнения логов сборки.

    Содержит настройки по умолчанию для проекта OrionPro.
    """

    # Этапы для анализа
    target_steps: List[TargetStep] = field(
        default_factory=lambda: [
            TargetStep(pattern="Step 4/21: BuildOrionPRO", name="BuildOrionPRO")
        ]
    )

    # Маркеры вложенных этапов
    stage_markers: List[str] = field(
        default_factory=lambda: ["<build>", "<brcc>", "<dcc>"]
    )

    # Паттерны предупреждений
    warning_patterns: List[str] = field(
        default_factory=lambda: [" Warning: ", " Hint: "]
    )

    # Игнорируемые паттерны (для фильтрации временных меток и путей)
    ignore_patterns: Dict[str, str] = field(
        default_factory=lambda: {
            "timestamp": r"^\[\d{2}:\d{2}:\d{2}\]",
            "path_prefix": r"N:\\BuildArea\\[^\\]+\\",
        }
    )

    # Настройки вывода
    output: Dict[str, bool] = field(
        default_factory=lambda: {
            "use_colors": True,
            "show_unchanged_count": True,
            "group_by_stage": True,
        }
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Загружает конфигурацию из YAML файла или использует значения по умолчанию.

    Args:
        config_path: Путь к файлу конфигурации (опционально)

    Returns:
        Config: Объект конфигурации

    Raises:
        FileNotFoundError: Если указанный файл конфигурации не существует
        ConfigValidationError: Если конфигурация некорректна
    """
    # Если путь не указан, используем значения по умолчанию
    if config_path is None:
        return Config()

    # Проверяем существование файла
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")

    try:
        # Читаем YAML файл
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Если файл пустой, используем значения по умолчанию
        if data is None:
            return Config()

        # Парсим target_steps
        target_steps = []
        if "target_steps" in data:
            for step_data in data["target_steps"]:
                target_steps.append(
                    TargetStep(
                        pattern=step_data.get("pattern", ""),
                        name=step_data.get("name", ""),
                    )
                )

        # Создаем конфигурацию с переопределенными значениями
        config = Config()

        if target_steps:
            config.target_steps = target_steps

        if "stage_markers" in data:
            config.stage_markers = data["stage_markers"]

        if "warning_patterns" in data:
            config.warning_patterns = data["warning_patterns"]

        if "ignore_patterns" in data:
            config.ignore_patterns = data["ignore_patterns"]

        if "output" in data:
            config.output.update(data["output"])

        return config

    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Ошибка парсинга YAML: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Ошибка загрузки конфигурации: {e}")


def validate_config(config: Config) -> bool:
    """
    Проверяет корректность конфигурации.

    Args:
        config: Объект конфигурации для проверки

    Returns:
        bool: True если конфигурация корректна

    Raises:
        ConfigValidationError: Если конфигурация некорректна
    """
    # Проверка наличия целевых этапов
    if not config.target_steps:
        raise ConfigValidationError("Не указаны целевые этапы (target_steps)")

    # Проверка каждого целевого этапа
    for i, step in enumerate(config.target_steps):
        if not step.pattern:
            raise ConfigValidationError(
                f"Целевой этап #{i+1}: отсутствует паттерн (pattern)"
            )
        if not step.name:
            raise ConfigValidationError(f"Целевой этап #{i+1}: отсутствует имя (name)")

    # Проверка наличия маркеров этапов
    if not config.stage_markers:
        raise ConfigValidationError("Не указаны маркеры этапов (stage_markers)")

    # Проверка наличия паттернов предупреждений
    if not config.warning_patterns:
        raise ConfigValidationError(
            "Не указаны паттерны предупреждений (warning_patterns)"
        )

    # Проверка корректности регулярных выражений в ignore_patterns
    if config.ignore_patterns:
        for key, pattern in config.ignore_patterns.items():
            try:
                re.compile(pattern)
            except re.error as e:
                raise ConfigValidationError(
                    f"Некорректное регулярное выражение в ignore_patterns['{key}']: {e}"
                )

    # Проверка настроек вывода
    if not isinstance(config.output, dict):
        raise ConfigValidationError("Настройки вывода (output) должны быть словарем")

    # Проверка типов значений в output
    for key, value in config.output.items():
        if not isinstance(value, bool):
            raise ConfigValidationError(
                f"Значение output['{key}'] должно быть булевым (true/false)"
            )

    return True
