"""
Модуль извлечения предупреждений из логов сборки.

Предоставляет функции для извлечения, нормализации и парсинга
предупреждений компилятора (Warning и Hint) из этапов сборки.
"""

from dataclasses import dataclass
from typing import List, Tuple
import re
from src.config import Config
from src.parser import BuildStep


@dataclass
class Warning:
    """
    Представление предупреждения компилятора.

    Содержит как оригинальный, так и нормализованный текст для
    корректного сравнения между логами.
    """

    text: str  # Нормализованный текст (для сравнения)
    original: str  # Оригинальный текст (для отчёта)
    type: str  # Тип: "Warning" или "Hint"
    stage: str  # Имя этапа сборки (например, "<Abd.dpr>")
    file_path: str  # Путь к файлу (если есть)
    line_number: int  # Номер строки в файле (если есть, иначе 0)


def parse_warning_details(text: str) -> Tuple[str, int]:
    """
    Извлекает путь к файлу и номер строки из текста предупреждения.

    Обрабатывает различные форматы предупреждений компилятора Delphi:
    - N:\\BuildArea\\...\\file.pas(123) Warning: ...
    - file.pas(456) Hint: ...
    - Относительные и абсолютные пути

    Args:
        text: Текст предупреждения

    Returns:
        Tuple[str, int]: Кортеж (путь_к_файлу, номер_строки)
                        Если информация не найдена, возвращает ("", 0)

    Examples:
        >>> parse_warning_details("N:\\\\Path\\\\file.pas(123) Warning: test")
        ("N:\\\\Path\\\\file.pas", 123)
        >>> parse_warning_details("file.pas(456) Hint: test")
        ("file.pas", 456)
        >>> parse_warning_details("Some text without file info")
        ("", 0)
    """
    # Паттерн для извлечения пути к файлу и номера строки
    # Формат: путь/к/файлу.pas(номер_строки)
    # Путь может содержать буквы диска, обратные слэши, точки и т.д.
    # Поддерживаем как абсолютные (N:\...), так и относительные пути
    pattern = (
        r"([A-Za-z]:[^\s()]+\.(?:pas|dpr|inc|PAS|DPR|INC)|"
        r"[^\s():]+\.(?:pas|dpr|inc|PAS|DPR|INC))\((\d+)\)"
    )

    match = re.search(pattern, text)
    if match:
        file_path = match.group(1)
        line_number = int(match.group(2))
        return (file_path, line_number)

    return ("", 0)


def normalize_warning(text: str, config: Config) -> str:
    """
    Нормализует текст предупреждения для корректного сравнения.

    Выполняет следующие операции:
    1. Удаляет временные метки в начале строки (формат [HH:MM:SS])
    2. Удаляет номера строк из путей к файлам (file.pas(123) -> file.pas)
    3. Нормализует пути к файлам (убирает абсолютные префиксы)
    4. Применяет паттерны игнорирования из конфигурации
    5. Убирает лишние пробелы

    Args:
        text: Оригинальный текст предупреждения
        config: Объект конфигурации с паттернами игнорирования

    Returns:
        str: Нормализованный текст

    Examples:
        >>> config = Config()
        >>> normalize_warning("[14:13:30] : [<dcc>] file.pas(123) Warning: test", config)
        "file.pas Warning: test"
    """
    normalized = text.strip()

    # Удаляем префикс типа [Hint] или [Warning] перед временной меткой, если он есть
    # Например: "[Hint] [14:14:17] ..." -> "[14:14:17] ..."
    normalized = re.sub(r"^\[(Hint|Warning)\]\s*", "", normalized, flags=re.IGNORECASE)

    # Удаляем временную метку в начале строки
    if "timestamp" in config.ignore_patterns:
        timestamp_pattern = config.ignore_patterns["timestamp"]
        normalized = re.sub(timestamp_pattern, "", normalized)

    # Удаляем флаги после временной метки (например, " :", "i:", "W:")
    # Формат: [HH:MM:SS]X: где X - один символ. Требуем пробел после двоеточия,
    # чтобы не удалять буквы дисков в путях (например, N:\)
    normalized = re.sub(r"^\s*[A-Za-z ]?\s*:\s+", "", normalized)

    # Удаляем префиксы в квадратных скобках (например, "[Step 4/21]", "[<dcc>]")
    normalized = re.sub(r"^\s*\[([^\]]+)\]\s*", "", normalized)

    # Нормализуем пути к файлам - убираем абсолютные префиксы
    if "path_prefix" in config.ignore_patterns:
        path_prefix_pattern = config.ignore_patterns["path_prefix"]
        normalized = re.sub(path_prefix_pattern, "", normalized)

    # Удаляем номера строк из путей к файлам
    # Формат: file.ext(123) -> file.ext
    # Ищем любой путь (содержит точку или слэш) с номером строки в скобках
    normalized = re.sub(
        r"([^\s()]*[\\./][^\s()]+)\(\d+\)",
        r"\1",
        normalized
    )

    # Удаляем пути к файлам перед ключевыми словами Warning/Hint
    # Некоторые предупреждения включают путь (например, "file.pas Hint: ..."),
    # другие - нет (просто "Hint: ..."). Удаляем путь для единообразия.
    normalized = re.sub(
        r"\s*\S+\.(pas|dpr|inc|PAS|DPR|INC|txt|TXT)\s+(Hint|Warning):",
        r"\2:",
        normalized,
        flags=re.IGNORECASE
    )

    # Убираем множественные пробелы и табы
    normalized = re.sub(r"\s+", " ", normalized)

    # Убираем пробелы в начале и конце
    normalized = normalized.strip()

    # Приводим к нижнему регистру, если включена опция ignore_case
    if config.comparison.get("ignore_case", False):
        normalized = normalized.lower()

    return normalized


def extract_warnings(step: BuildStep, config: Config) -> List[Warning]:
    """
    Извлекает все предупреждения из этапа сборки и его подэтапов.

    Рекурсивно обрабатывает иерархию этапов, ищет строки содержащие
    паттерны предупреждений из конфигурации (Warning, Hint).

    Args:
        step: Этап сборки для анализа
        config: Объект конфигурации с паттернами предупреждений

    Returns:
        List[Warning]: Список найденных предупреждений

    Examples:
        >>> config = Config()
        >>> step = BuildStep(name="<test>", level=0, start_line=1, end_line=3,
        ...                  lines=["line 1", "file.pas(10) Warning: test"])
        >>> warnings = extract_warnings(step, config)
        >>> len(warnings)
        1
    """
    warnings: List[Warning] = []

    # Обрабатываем строки текущего этапа
    for line in step.lines:
        # Проверяем каждый паттерн предупреждения
        for warning_pattern in config.warning_patterns:
            if warning_pattern.pattern in line:
                # Используем тип из паттерна
                warning_type = warning_pattern.type

                # Извлекаем детали (путь к файлу и номер строки)
                file_path, line_number = parse_warning_details(line)

                # Нормализуем текст для сравнения
                normalized_text = normalize_warning(line, config)

                # Создаем объект предупреждения
                warning = Warning(
                    text=normalized_text,
                    original=line.strip(),
                    type=warning_type,
                    stage=step.name,
                    file_path=file_path,
                    line_number=line_number,
                )

                warnings.append(warning)
                break  # Не проверяем остальные паттерны для этой строки

    # Рекурсивно обрабатываем дочерние этапы
    for child in step.children:
        child_warnings = extract_warnings(child, config)
        warnings.extend(child_warnings)

    return warnings
